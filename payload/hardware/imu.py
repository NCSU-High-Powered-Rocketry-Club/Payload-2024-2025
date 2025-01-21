"""Module for interacting with the IMU (Inertial measurement unit) on the rocket."""
import struct
import time

import serial

from payload.constants import PACKET_BYTE_SIZE
from payload.data_handling.packets.imu_data_packet import IMUDataPacket


class IMU:
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
    def _process_packet_data(binary_packet) -> None:
        """
        Process the data points in the unpacked packet and puts into an IMUDataPacket.
        :param unpacked_packet: The serialized data packet containing multiple data points.
        """
        # Iterate through each data point in the packet.
        unpacked_data = struct.unpack("<"+"f"*(PACKET_BYTE_SIZE//4), binary_packet)
        return IMUDataPacket(*unpacked_data)

    def fetch_data(self) -> None:
        """
        Continuously fetch data packets from the IMU and process them.
        """
        while self._serial.in_waiting < PACKET_BYTE_SIZE:
            # print(self._serial.in_waiting)
            time.sleep(0.001)
        # print(self._serial.in_waiting)
        serialized_data_packet = self._serial.read(PACKET_BYTE_SIZE)
        print(serialized_data_packet)
        return IMU._process_packet_data(serialized_data_packet)

