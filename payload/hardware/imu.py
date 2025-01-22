"""Module for interacting with the IMU (Inertial measurement unit) on the rocket."""

import struct
import time
from abc import ABC

import serial

from payload.constants import PACKET_BYTE_SIZE
from payload.data_handling.data_packets.imu_data_packet import IMUDataPacket
from payload.hardware.base_imu import BaseIMU


class IMU(BaseIMU):
    """
    Represents the IMU on the rocket. This is used to interact with the data collected by the
    Arduino.
    """

    def __init__(self, port: str, baud_rate: int) -> None:
        """
        Initializes the object that interacts with the Arduino connected to the pi.
        :param port: the port that the Arduino is connected to
        :param baud_rate: the baud rate of the channel
        """
        self._serial = serial.Serial(port, baud_rate, timeout=10)

    @staticmethod
    def _process_packet_data(binary_packet) -> IMUDataPacket:
        """
        Process the data points in the unpacked packet and puts into an IMUDataPacket.
        :param binary_packet: The serialized data packet containing multiple data points.
        """
        # Iterate through each data point in the packet.
        unpacked_data = struct.unpack("<" + "f" * (PACKET_BYTE_SIZE // 4), binary_packet)
        return IMUDataPacket(*unpacked_data)

    def fetch_data(self) -> IMUDataPacket | None:
        """
        Continuously fetch data packets from the IMU and process them.
        """
        if self._serial.in_waiting >= PACKET_BYTE_SIZE:
            serialized_data_packet = self._serial.read(PACKET_BYTE_SIZE)
            return IMU._process_packet_data(serialized_data_packet)
        return None
