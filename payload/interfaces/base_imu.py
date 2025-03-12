"""Module defining the base class (BaseIMU) for interacting with
the IMU (Inertial measurement unit) on the rocket."""

import threading
from abc import ABC, abstractmethod
from queue import Queue

from payload.data_handling.packets.imu_data_packet import IMUDataPacket


class BaseIMU(ABC):
    """
    Represents the IMU on the rocket. This class will read data and package it into an
    IMUDataPacket that can be fetched with the fetch_data method.
    """

    __slots__ = ("_is_running", "_lock", "_queued_imu_packets", "_thread")

    def __init__(self):
        self._is_running: threading.Event = threading.Event()
        self._queued_imu_packets = Queue()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()

    @abstractmethod
    def _read_data(self) -> IMUDataPacket | None:
        """
        Makes a request to the IMU for the next data packet and returns it.
        """

    @property
    def is_running(self) -> bool:
        """
        Returns whether the IMU is running.
        """
        return self._is_running.is_set()

    def start(self) -> None:
        """
        Starts the IMU.
        """
        self._is_running.set()
        self._thread = threading.Thread(target=self._read_data, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """
        Stops the IMU.
        """
        self._is_running.clear()
        if self._thread:
            self._thread.join()

    def get_data_packet(self) -> IMUDataPacket:
        """
        Returns the most recent IMU data packet that has been received.

        :return: The most recent IMU data packet.
        """
        return self._queued_imu_packets.get()
