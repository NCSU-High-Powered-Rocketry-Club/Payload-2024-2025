import time
from pathlib import Path
import pandas as pd

from payload.constants import FREQUENCY
from payload.data_handling.data_packets.imu_data_packet import IMUDataPacket
from payload.hardware.imu import BaseIMU

class MockIMU(BaseIMU):
    """
    A mock implementation of the IMU for testing purposes. It reads data from a CSV file
    and returns one row at a time as an IMUDataPacket at a fixed rate of 50Hz.
    """

    __slots__ = ("_log_file_path", "_last_fetch_time", "_current_index")

    def __init__(self, log_file_path: Path | None = None) -> None:
        """
        Initializes the MockIMU by loading data from the given CSV file.
        :param log_file_path: Path to the CSV file containing mock IMU data.
        """
        self._log_file_path = log_file_path
        if log_file_path is None:
            root_dir = Path(__file__).parent.parent.parent
            self._log_file_path = next(iter(Path(root_dir / "launch_data").glob("*.csv")))
        self._data = pd.read_csv(self._log_file_path)
        self._current_index = 0
        self._last_fetch_time = 0  # Initialize last fetch time

    def stop(self) -> None:
        """Stops the IMU."""
        pass

    def fetch_data(self) -> IMUDataPacket | None:
        """
        Returns the next row of the CSV as an IMUDataPacket at a rate of 50Hz.
        If called too soon, it returns None.
        :return: IMUDataPacket or None if not enough time has passed.
        """
        current_time = time.time()
        # We simulate the delay the real imu has in sending data by checking the time that has
        # passed since the last fetch.
        if current_time - self._last_fetch_time < 1 / FREQUENCY:  # 50Hz = 20ms
            return None  # Skip this call if 20ms hasn't passed

        if self._current_index >= len(self._data):
            raise StopIteration("No more data available in the CSV file.")

        row = self._data.iloc[self._current_index]
        self._current_index += 1

        self._last_fetch_time = current_time
        # Converts a row in the CSV to an IMUDataPacket
        return IMUDataPacket(**row.to_dict())
