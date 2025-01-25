"""Module for simulating interacting with the IMU (Inertial measurement unit) on the rocket."""

import time
from pathlib import Path

import pandas as pd

from payload.constants import FREQUENCY
from payload.data_handling.packets.imu_data_packet import IMUDataPacket
from payload.interfaces.base_imu import BaseIMU


class MockIMU(BaseIMU):
    """
    A mock implementation of the IMU for testing purposes. It reads data from a CSV file
    and returns one row at a time as an IMUDataPacket at a fixed rate of 50Hz.
    """

    __slots__ = ("_current_index", "_df", "_last_fetch_time", "_log_file_path", "is_running")

    def __init__(self, log_file_path: Path | None = None) -> None:
        """
        Initializes the MockIMU by loading data from the given CSV file.
        :param log_file_path: Path to the CSV file containing mock IMU data.
        """
        self._log_file_path = log_file_path
        if log_file_path is None:
            # If no log file path is provided, use the default log file path
            root_dir = Path(__file__).parent.parent.parent
            self._log_file_path = next(iter(Path(root_dir / "launch_data").glob("*.csv")))
        # We iterate through the CSV file using pandas, making one row into a data packet at a time
        self._data = pd.read_csv(self._log_file_path)
        self._current_index = 0
        self._last_fetch_time = 0
        self.is_running = True

        # Using pandas and itertuples to read the header:
        df_header = pd.read_csv(self._log_file_path, nrows=0)
        # Get the columns that are common between the data packet and the log file, since we only
        # care about those
        self._valid_columns = list((set(IMUDataPacket.__struct_fields__)) & set(df_header.columns))
        self._df = pd.read_csv(
            self._log_file_path,
            engine="c",
            usecols=self._valid_columns,
        )

    def start(self) -> None:
        """Starts the IMU."""
        self.is_running = True

    def stop(self) -> None:
        """Stops the IMU."""
        self.is_running = False

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

        # If we have reached the end of the data, stop the IMU
        if self._current_index >= len(self._data):
            self.stop()
            return None

        row = self._df.iloc[self._current_index]
        row_dict = {k: v for k, v in row.items() if pd.notna(v)}
        self._current_index += 1
        self._last_fetch_time = current_time
        # Converts a row in the CSV to an IMUDataPacket
        return IMUDataPacket(**row_dict)
