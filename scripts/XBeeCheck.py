"""Module for the Receiver class."""

import threading
import time
import serial

from payload.constants import NO_MESSAGE, RECEIVER_SERIAL_TIMEOUT, RECEIVER_THREAD_TIMEOUT
from payload.interfaces.base_receiver import BaseReceiver


class Receiver(BaseReceiver):
    """
    This is the class that controls the Xbee Pro s3b. On a separate thread, it listens for incoming
    messages from the transmitter and then makes them available to the main thread.
    """

    __slots__ = ("_baud_rate", "_latest_message", "_lock", "_port", "_stop_event", "_thread")

    def __init__(self, port: str, baud_rate: int) -> None:
        self._port = port
        self._baud_rate = baud_rate
        self._latest_message: str = NO_MESSAGE
        self._serial_connection = None
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._listen, daemon=True)

    @property
    def latest_message(self) -> str:
        """Thread-safe access to the latest received message."""
        with self._lock:
            return self._latest_message

    def start(self) -> None:
        """Starts the listening thread."""
        if self._thread.is_alive():
            self._thread.close()

        time.sleep(0.5)

        if self._serial_connection:
            if self._serial_connection.is_open:
                try:
                    self._serial_connection.flush()
                    self._serial_connection.close()

                except Exception as e:
                    print("Exception when trying to close prev. receiver serial: ", e)

                finally:
                    self._serial_connection = None

        if not  self._thread.is_alive():
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._listen, daemon=True)
            self._thread.start()

    def stop(self) -> None:
        """Stops the listening thread safely."""
        self._stop_event.set()  # Signal thread to exit

        time.sleep(0.5)

        if self._thread.is_alive():
            self._thread.join(timeout=RECEIVER_THREAD_TIMEOUT)  # Wait for thread to stop

        # if self._serial_connection:
        #     try:
        #         if self._serial_connection.is_open:
        #             self._serial_connection.flush()
        #             self._serial_connection.close()

        #     except Exception as e:
        #         print("Exception when closing receiver serial port: ", e)

        #     finally:
        #         self._serial_connection = None
        


    def _listen(self) -> None:
        """
        Continuously listens for incoming messages from the ground station. It runs on a separate
        thread and reads the serial port for incoming messages. When a message is received, it is
        stored in the latest_message attribute.
        """
        try:
            self._serial_connection = serial.Serial(self._port, self._baud_rate, timeout = RECEIVER_SERIAL_TIMEOUT)

            while not self._stop_event.is_set():
                if self._serial_connection.in_waiting > 0:
                    # This reads the incoming message from the serial port and decodes it. If it has
                    # an error decoding, it will ignore the error it and just keep going. This could
                    # be a potential issue if we start getting junk data.
                    line = self._serial_connection.readline().decode("utf-8", "ignore").strip()
                    if line:
                        with self._lock:
                            self._latest_message = line.strip()

        except Exception as e:
            print("Error opening receiver serial port: ", e)

        finally:
            if self._serial_connection:
                try:
                    if self._serial_connection.is_open:
                        self._serial_connection.flush()
                        self._serial_connection.close()

                except OSError as e:
                    print("Exception when closing receiver serial port: ", e)

                finally:
                    self._serial_connection = None
