"""Module for simulating interacting with the IMU (Inertial measurement unit) on the rocket."""

import time
from pathlib import Path

import pandas as pd

from payload.constants import IMU_APPROXIMATE_FREQUENCY
from payload.data_handling.packets.imu_data_packet import IMUDataPacket
from payload.interfaces.base_imu import BaseIMU


class MockIMU(BaseIMU):
    """
    A mock implementation of the IMU for testing purposes. It reads data from a CSV file
    and returns one row at a time as an IMUDataPacket at a fixed rate of 50Hz.
    """

    __slots__ = (
        "_current_index",
        "_df",
        "_log_file_path",
        "_valid_columns",
        "real_time_replay",
    )

    def __init__(self, log_file_path: Path | None = None, real_time_replay: bool = True) -> None:
        """
        Initializes the MockIMU by loading data from the given CSV file.
        :param log_file_path: Path to the CSV file containing mock IMU data.
        """
        super().__init__()

        self._log_file_path = log_file_path
        if log_file_path is None:
            # Just use the first file in the `launch_data` directory:
            # Note: We do this convoluted way because we want to make it work with the one liner
            # `uvx --from git+... mock` on any machine from any state. Otherwise a Path().cwd()
            # would be enough.
            path = Path(__file__)
            payload_index = path.parts.index("Payload-2024-2025")  # Find the Payload directory
            root_dir = Path(*path.parts[: payload_index + 1])  # Make a new path to that dir
            self._log_file_path = next(iter(Path(root_dir / "launch_data").glob("*.csv")))

        # We iterate through the CSV file using pandas, making one row into a data packet at a time
        self.real_time_replay = real_time_replay
        self._current_index: int = 0

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

    def fetch_data(self) -> IMUDataPacket | None:
        """
        Returns the next row of the CSV as an IMUDataPacket at a rate of 50Hz.
        If called too soon, it returns None.
        :return: IMUDataPacket or None if not enough time has passed.
        """
        # We simulate the delay the real imu has in sending data by checking the time that has
        # passed since the last fetch.
        if self.real_time_replay:
            time.sleep(1 / IMU_APPROXIMATE_FREQUENCY)  # 50Hz = 20ms

        # If we have reached the end of the data, stop the IMU
        if self._current_index >= len(self._df):
            self.stop()
            return None

        row = self._df.iloc[self._current_index]
        row_dict = {k: v for k, v in row.items() if pd.notna(v)}
        self._current_index += 1
        # Converts a row in the CSV to an IMUDataPacket
        return IMUDataPacket(**row_dict)
