"""Module for logging data to a CSV file in real time."""

import csv
import multiprocessing
import signal
from pathlib import Path
from typing import Any, Literal

from msgspec import to_builtins

from payload.constants import (
    MAX_GET_TIMEOUT_SECONDS,
    STOP_SIGNAL,
)
from payload.data_handling.packets.context_data_packet import ContextDataPacket
from payload.data_handling.packets.imu_data_packet import IMUDataPacket
from payload.data_handling.packets.logger_data_packet import LoggerDataPacket
from payload.data_handling.packets.processor_data_packet import ProcessorDataPacket
from payload.utils import modify_multiprocessing_queue_windows


class Logger:
    """
    A class that logs data to a CSV file. Similar to the IMU class, it runs in a separate process.
    This is because the logging process is I/O-bound, meaning that it spends most of its time
    waiting for the file to be written to. By running it in a separate process, we can continue to
    log data while the main loop is running.

    It uses Python's csv module to append the payload's current state and IMU data to
    our logs in real time.
    """

    LOG_BUFFER_STATES = ("StandbyState", "LandedState")

    __slots__ = (
        "_log_counter",
        "_log_process",
        "_log_queue",
        "log_path",
    )

    def __init__(self, log_dir: Path) -> None:
        """
        Initializes the logger object. It creates a new log file in the specified directory. Like
        the IMU class, it creates a queue to store log messages, and starts a separate process to
        handle the logging. We are logging a lot of data, and logging is I/O-bound, so running it
        in a separate process allows the main loop to continue running without waiting for the log
        file to be written to.
        :param log_dir: The directory where the log files will be.
        """
        # Create the log directory if it doesn't exist
        log_dir.mkdir(parents=True, exist_ok=True)

        # Get all existing log files and find the highest suffix number
        existing_logs = list(log_dir.glob("log_*.csv"))
        max_suffix = (
            max(int(log.stem.split("_")[-1]) for log in existing_logs) if existing_logs else 0
        )

        # Buffer for StandbyState and LandedState
        self._log_counter = 0

        # Create a new log file with the next number in sequence
        self.log_path = log_dir / f"log_{max_suffix + 1}.csv"
        with self.log_path.open(mode="w", newline="") as file_writer:
            writer = csv.DictWriter(file_writer, fieldnames=list(LoggerDataPacket.__annotations__))
            writer.writeheader()

        # Makes a queue to store log messages, basically it's a process-safe list that you add to
        # the back and pop from front, meaning that things will be logged in the order they were
        # added.
        # Signals (like stop) are sent as strings, but data is sent as dictionaries
        self._log_queue: multiprocessing.Queue[LoggerDataPacket | Literal["STOP"]] = (
            multiprocessing.Queue()
        )
        modify_multiprocessing_queue_windows(self._log_queue)

        # Start the logging process
        self._log_process = multiprocessing.Process(
            target=self._logging_loop, name="Logger Process"
        )

    @property
    def is_running(self) -> bool:
        """
        Returns whether the logging process is running.
        """
        return self._log_process.is_alive()

    @staticmethod
    def _convert_unknown_type(unknown_object: Any) -> str:
        """
        Truncates the decimal place of the object to 8 decimal places. Used by msgspec to
        convert numpy float64 to a string.
        :param unknown_object: The object to truncate.
        :return: The truncated object.
        """
        return f"{unknown_object:.8f}"

    @staticmethod
    def _prepare_log_dict(
        context_data_packet: ContextDataPacket,
        imu_data_packet: IMUDataPacket,
        processed_data_packet: ProcessorDataPacket,
    ) -> LoggerDataPacket:
        """
        Creates a data packet dictionary representing a row of data to be logged. To control what
        is logged, you can add or remove fields from LoggerDataPacket.
        :param context_data_packet: The context data packet to log.
        :param imu_data_packet: The IMU data packet to log.
        :param processed_data_packet: The processed data packet to log.
        :return: The dictionary representing what will be logged.
        """

        # Let's first add the state field (This might be expanded into a context data pack like in
        # airbrakes code):
        logged_data_packet: LoggerDataPacket = {}

        # Convert the context data packet to a dictionary and add it to the logged data packet
        context_data_packet_dict: dict[str, str] = to_builtins(context_data_packet)
        logged_data_packet.update(context_data_packet_dict)

        # Convert the imu data packet to a dictionary
        # Using to_builtins() is much faster than asdict() for some reason
        imu_data_packet_dict: dict[str, int | float] = to_builtins(imu_data_packet)
        logged_data_packet.update(imu_data_packet_dict)

        # Convert the processed data packet to a dictionary
        processed_data_packet_dict: dict[str, str] = to_builtins(
            processed_data_packet,
            enc_hook=Logger._convert_unknown_type,  # converts np float to str
        )

        # Let's drop the "time_since_last_data_packet" field:
        processed_data_packet_dict.pop("time_since_last_data_packet", None)

        logged_data_packet.update(processed_data_packet_dict)

        return logged_data_packet

    def start(self) -> None:
        """
        Starts the logging process. This is called before the main while loop starts.
        """
        self._log_process.start()

    def stop(self) -> None:
        """
        Stops the logging process. It will finish logging the current message and then stop.
        """
        self._log_queue.put(STOP_SIGNAL)  # Put the stop signal in the queue
        print("put logging stop signal in queue")
        # Waits for the process to finish before stopping it
        self._log_process.join(timeout=3)

    def log(
        self,
        context_data_packet: ContextDataPacket,
        imu_data_packet: IMUDataPacket,
        processed_data_packet: ProcessorDataPacket,
    ) -> None:
        """
        Logs the current state and IMU data to the CSV file.
        :param context_data_packet: The context data packet to log.
        :param imu_data_packet: The IMU data packet to log.
        :param processed_data_packet: The processed data packet to log.
        """
        # We are populating a dictionary with the fields of the logged data packet
        logged_data_packet = Logger._prepare_log_dict(
            context_data_packet,
            imu_data_packet,
            processed_data_packet,
        )

        self._log_queue.put(logged_data_packet)

    # ------------------------ ALL METHODS BELOW RUN IN A SEPARATE PROCESS -------------------------
    @staticmethod
    def _truncate_floats(data: LoggerDataPacket) -> dict[str, str | object]:
        """
        Truncates the decimal place of the floats in the dictionary to 8 decimal places.
        :param data: The dictionary to truncate.
        :return: The truncated dictionary.
        """
        return {
            key: f"{value:.8f}" if isinstance(value, float) else value
            for key, value in data.items()
        }

    def _logging_loop(self) -> None:
        """
        The loop that saves data to the logs. It runs in parallel with the main loop.
        """
        # Ignore the SIGINT (Ctrl+C) signal, because we only want the main process to handle it
        signal.signal(signal.SIGINT, signal.SIG_IGN)  # Ignores the interrupt signal

        # Unfortunately, we need to modify the queue here again because the modifications made in
        # the __init__ are not copied to the new process.
        modify_multiprocessing_queue_windows(self._log_queue)

        # Set up the csv logging in the new process
        with self.log_path.open(mode="a", newline="") as file_writer:
            writer = csv.DictWriter(file_writer, fieldnames=list(LoggerDataPacket.__annotations__))
            while True:
                # Get a message from the queue (this will block until a message is available)
                # Because there's no timeout, it will wait indefinitely until it gets a message.
                message_fields: list[LoggerDataPacket | Literal["STOP"]] = self._log_queue.get_many(
                    timeout=MAX_GET_TIMEOUT_SECONDS
                )
                if STOP_SIGNAL in message_fields:
                    return
                # If the message is the stop signal, break out of the loop
                for message_field in message_fields:
                    writer.writerow(Logger._truncate_floats(message_field))
