"""Module for simulating interacting with the IMU (Inertial measurement unit) on the rocket."""

import ast
import contextlib
import multiprocessing
import time
from functools import partial
from pathlib import Path

import pandas as pd

from payload.constants import (
    LOG_BUFFER_SIZE,
    MAX_FETCHED_PACKETS,
    MAX_QUEUE_SIZE,
    RAW_DATA_PACKET_SAMPLING_RATE,
    STOP_SIGNAL,
)
from payload.utils import get_all_from_queue


class MockIMU:
    """
    A mock implementation of the IMU for testing purposes. It doesn't interact with any hardware
    and returns data read from a previous log file.
    """

    __slots__ = ("_log_file_path",)

    def __init__(
        self,
        real_time_replay: bool,
        log_file_path: Path | None = None,
    ):
        """
        Initializes the object that pretends to be an IMU for testing purposes by reading from a
        log file.

        We don't call the parent constructor as the IMU class has different parameters, so we
        manually start the process that fetches data from the log file
        :param log_file_path: The path of the log file to read data from.
        :param real_time_replay: Whether to mimmick a real flight by sleeping for a set
        period, or run at full speed, e.g. for using it in the CI.
        """
        self._log_file_path = log_file_path
        # Check if the launch data file exists:
        if log_file_path is None:
            # Just use the first file in the `launch_data` directory:
            # Note: We do this convoluted way because we want to make it work with the one liner
            # `uvx --from git+... mock` on any machine from any state.
            root_dir = Path(__file__).parent.parent.parent
            self._log_file_path = next(iter(Path(root_dir / "launch_data").glob("*.csv")))

    def _read_file(
        self, log_file_path: Path, real_time_replay: bool
    ) -> None:
        """
        Reads the data from the log file and puts it into the shared queue.
        :param log_file_path: the name of the log file to read data from located in scripts/imu_data
        :param real_time_replay: Whether to mimic a real flight by sleeping for a set period,
        or run at full speed, e.g. for using it in the CI.
        """

        # Using pandas and itertuples to read the file:
        df_header = pd.read_csv(log_file_path, nrows=0)
        # Get the columns that are common between the data packet and the log file, since we only
        # care about those
        valid_columns = list(
            (set(EstimatedDataPacket.__struct_fields__) | set(RawDataPacket.__struct_fields__))
            & set(df_header.columns)
        )

        # Read the csv, starting from the row after the log buffer, and using only the valid columns
        df = pd.read_csv(
            log_file_path,
            skiprows=list(range(1, start_index + 1)),
            engine="c",
            usecols=valid_columns,
            converters={"invalid_fields": MockIMU._convert_invalid_fields},
        )

        # Iterate over the rows of the dataframe and put the data packets in the queue
        for row in df.itertuples(index=False):
            start_time = time.time()
            # Convert the named tuple to a dictionary and remove any NaN values:
            row_dict = {k: v for k, v in row._asdict().items() if pd.notna(v)}

            # Check if the process should stop:
            if not self.is_running:
                break

            # If the row has the scaledAccelX field, it is a raw data packet, otherwise it is an
            # estimated data packet
            if row_dict.get("scaledAccelX"):
                imu_data_packet = RawDataPacket(**row_dict)
            else:
                imu_data_packet = EstimatedDataPacket(**row_dict)

            # Put the packet in the queue
            self._data_queue.put(imu_data_packet)

            # sleep only if we are running a real-time replay
            # Our IMU sends raw data at 1000 Hz, so we sleep for 1 ms between each packet to
            # pretend to be real-time
            if real_time_replay and isinstance(imu_data_packet, RawDataPacket):
                # Mimmick polling interval
                end_time = time.time()
                time.sleep(max(0.0, RAW_DATA_PACKET_SAMPLING_RATE - (end_time - start_time)))

