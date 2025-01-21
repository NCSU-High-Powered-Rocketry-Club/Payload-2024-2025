"""Module for simulating interacting with the IMU (Inertial measurement unit) on the rocket."""
import pandas as pd
from payload.data_handling.packets.imu_data_packet import IMUDataPacket
from payload.hardware.imu import BaseIMU


class MockIMU(BaseIMU):
    """
    A mock implementation of the IMU for testing purposes. It reads data from a CSV file
    and returns one row at a time as an IMUDataPacket.
    """
    def __init__(self, log_file_path: str) -> None:
        """
        Initializes the MockIMU by loading data from the given CSV file.
        :param log_file_path: Path to the CSV file containing mock IMU data.
        """
        self._data = pd.read_csv(log_file_path)
        self._current_index = 0

    def stop(self) -> None:
        """
        Stops the IMU.
        """
        pass

    def fetch_data(self) -> IMUDataPacket:
        """
        Returns the next row of the CSV as an IMUDataPacket. Raises an exception if no more data is
        available.
        :return: IMUDataPacket representing the next row of data.
        """
        if self._current_index >= len(self._data):
            raise StopIteration("No more data available in the CSV file.")

        row = self._data.iloc[self._current_index]
        self._current_index += 1

        # Convert the row to an IMUDataPacket.
        # Assuming the column names in the CSV match the attributes of IMUDataPacket.
        return IMUDataPacket(**row.to_dict())
