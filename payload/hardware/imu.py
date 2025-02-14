"""Module for interacting with the IMU (Inertial measurement unit) on the rocket."""

import struct

import serial

from payload.constants import PACKET_BYTE_SIZE, PACKET_START_MARKER
from payload.data_handling.packets.imu_data_packet import IMUDataPacket
from payload.interfaces.base_imu import BaseIMU


class IMU(BaseIMU):
    """
    Represents the IMU on the rocket. This is used to interact with the data collected by the
    Arduino.
    """

    __slots__ = ("_baud_rate", "_port", "_serial")

    def __init__(self, port: str, baud_rate: int) -> None:
        """
        Initializes the object that interacts with the Arduino connected to the pi.
        :param port: the port that the Arduino is connected to
        :param baud_rate: the baud rate of the channel
        """
        self._port = port
        self._baud_rate = baud_rate
        self._serial = None

    @staticmethod
    def _process_packet_data(binary_packet) -> IMUDataPacket:
        """
        Process the data points in the unpacked packet and puts into an IMUDataPacket.
        :param binary_packet: The serialized data packet containing multiple data points. On the
        arduino, we allocate 84 bytes for each packet. These bytes match up with the order of the
        fields in the IMUDataPacket struct.
        """
        # Iterate through each data point in the packet.
        unpacked_data = struct.unpack("<" + "f" * (PACKET_BYTE_SIZE // 4), binary_packet)
        return IMUDataPacket(*unpacked_data)

    def start(self):
        self._serial = serial.Serial(self._port, self._baud_rate, timeout=1)

    def stop(self):
        self._serial.close()

    def fetch_data(self) -> IMUDataPacket | None:
        """
        Fetches a data packet from the IMU in a non-blocking manner.
        It keeps reading until it finds a valid start marker, then returns a full packet.
        If there is not enough data, it returns None.
        """
        # Over serial, we are constantly sending packets of data. We need to read the data in a way
        # that we can properly sync with the start of a packet. This is why we read one byte at a
        # time until we find the start marker. Additionally, we alot exactly 84 bytes for each
        # packet, even if some of the fields are empty.
        while self._serial.in_waiting >= PACKET_BYTE_SIZE + 1:  # The + 1 is for the start marker
            # Reads a single byte and checks if it is the start marker. We do this to properly sync
            # our code with the start of a packet. This will read through any junk data until it
            # finds the start marker.
            byte = self._serial.read(1)
            if byte == PACKET_START_MARKER:
                serialized_data_packet = self._serial.read(PACKET_BYTE_SIZE)
                return IMU._process_packet_data(serialized_data_packet)
        return None
