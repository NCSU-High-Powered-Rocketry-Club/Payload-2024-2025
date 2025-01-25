"""Module for interacting with the IMU (Inertial measurement unit) on the rocket."""

import struct
import time

import serial

from payload.constants import PACKET_BYTE_SIZE, PACKET_START_MARKER
from payload.data_handling.packets.imu_data_packet import IMUDataPacket
from payload.interfaces.base_imu import BaseIMU


class IMU(BaseIMU):
    """
    Represents the IMU on the rocket. This is used to interact with the data collected by the
    Arduino.
    """

    __slots__ = ("_serial", "_port", "_baud_rate")

    def __init__(self, port: str, baud_rate: int) -> None:
        """
        Initializes the object that interacts with the Arduino connected to the pi.
        :param port: the port that the Arduino is connected to
        :param baud_rate: the baud rate of the channel
        """
        self._serial = None
        self._baud_rate = baud_rate
        self._port = port

    def start(self):
        self._serial = serial.Serial(self._port, self._baud_rate, timeout=10)

    def stop(self):
        """stops the IMU process."""
        # self._serial.reset_input_buffer()
        # self._serial.reset_output_buffer()
        self._serial.close()
        print("imu stopped")

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
        Fetches a data packet from the IMU in a non-blocking manner.
        It keeps reading until it finds a valid start marker, then returns a full packet.
        If there is not enough data, it returns None.
        """
        while self._serial.in_waiting >= PACKET_BYTE_SIZE + 1:  # The + 1 is for the start marker
            # Reads a single byte and checks if it is the start marker
            byte = self._serial.read(1)
            if byte == PACKET_START_MARKER:
                serialized_data_packet = self._serial.read(PACKET_BYTE_SIZE)
                return IMU._process_packet_data(serialized_data_packet)
        return None
