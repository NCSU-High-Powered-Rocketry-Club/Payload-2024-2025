"""Module defining the base class (BaseIMU) for interacting with
the IMU (Inertial measurement unit) on the rocket."""

import collections
import contextlib
import sys

from payload.constants import IMU_TIMEOUT_SECONDS
from payload.data_handling.data_packets.imu_data_packet import IMUDataPacket


class BaseIMU:
    """
    Base class for the IMU and MockIMU classes.
    """

    __slots__ = (
        "_running",
    )

    def __init__(self) -> None:
        """
        Initialises object using arguments passed by the constructors of the subclasses.
        """
        self._running = False

    @property
    def is_running(self) -> bool:
        """
        Returns whether the process fetching data from the IMU is running.
        :return: True if the process is running, False otherwise
        """
        return self._running

    def stop(self) -> None:
        """
        Stops fetching data from the IMU.
        """
        self._running = False

    def start(self) -> None:
        """
        Starts the process separate from the main process for fetching data from the IMU.
        """
        self._running = True
        self._data_fetch_process.start()

    def get_imu_data_packet(self) -> IMUDataPacket | None:
        """
        Gets the last available data packet from the IMU.
        :return: an IMUDataPacket object containing the latest data from the IMU. If a value is not
        available, it will be None.
        """
        return self._data_queue.get(timeout=IMU_TIMEOUT_SECONDS)