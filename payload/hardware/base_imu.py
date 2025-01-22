"""Module defining the base class (BaseIMU) for interacting with
the IMU (Inertial measurement unit) on the rocket."""

from abc import ABC, abstractmethod

from payload.data_handling.packets.imu_data_packet import IMUDataPacket


class BaseIMU(ABC):
    """
    Represents the IMU on the rocket. This class will read data and package it into an
    IMUDataPacket that can be fetched with the fetch_data method.
    """

    @abstractmethod
    def stop(self) -> None:
        """
        Stops the IMU.
        """

    @abstractmethod
    def fetch_data(self) -> IMUDataPacket | None:
        """
        Makes a request to the IMU for the next data packet and returns it.
        """
