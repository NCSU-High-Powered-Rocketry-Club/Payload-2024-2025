"""Module for interacting with the IMU (Inertial Measurement Unit) on the rocket."""

import struct
import serial
import time
from payload.constants import ARDUINO_SERIAL_TIMEOUT, PACKET_BYTE_SIZE, PACKET_START_MARKER
from payload.data_handling.packets.imu_data_packet import IMUDataPacket
from payload.interfaces.base_imu import BaseIMU

class IMU(BaseIMU):
    """
    Represents the IMU on the rocket. This is used to interact with the data collected by the
    Arduino.
    """
    __slots__ = ("_baud_rate", "_port", "_serial", "_buffer")

    def __init__(self, port: str, baud_rate: int) -> None:
        """
        Initializes the object that interacts with the Arduino connected to the Pi.

        :param port: The port that the Arduino is connected to (e.g., '/dev/ttyUSB0').
        :param baud_rate: The baud rate of the serial channel (e.g., 115200).
        """
        super().__init__()
        self._port = port
        self._baud_rate = baud_rate
        self._serial = None
        self._buffer = b""  # Initialize an empty buffer to store serial data

    @staticmethod
    def _process_packet_data(binary_packet) -> IMUDataPacket:
        """
        Processes the data points in the unpacked packet into an IMUDataPacket.

        :param binary_packet: The serialized data packet (84 bytes) containing multiple data points.
        :return: An IMUDataPacket object with the unpacked data.
        """
        # Unpack 84 bytes into 21 floats (84 / 4 = 21), assuming little-endian format
        # TODO: Handle statusFlags appropriately if part of the packet structure
        unpacked_data = struct.unpack("<" + "f" * (PACKET_BYTE_SIZE // 4), binary_packet)
        data_packet = IMUDataPacket(*unpacked_data)
        data_packet.timestamp = time.time()  # Add python timestamp to the data packet

    def start(self):
        """Opens the serial connection to the Arduino."""
        super().start()
        self._serial = serial.Serial(self._port, self._baud_rate, timeout=ARDUINO_SERIAL_TIMEOUT)

    def stop(self):
        """Closes the serial connection to the Arduino."""
        super().stop()
        self._serial.close()

    def fetch_data(self) -> IMUDataPacket | None:
        """
        Fetches a data packet from the IMU in a non-blocking manner.
        Accumulates serial data in a buffer, searches for the start marker, and returns a full packet
        if found. Returns None if no complete packet is available.

        :return: An IMUDataPacket if a valid packet is found, otherwise None.
        """
        # Read all available bytes from the serial port (non-blocking due to timeout)
        new_data = self._serial.read(self._serial.in_waiting)
        self._buffer += new_data  # Append new data to the buffer

        # Search for the start marker in the buffer
        marker_idx = self._buffer.find(PACKET_START_MARKER)
        if marker_idx != -1:  # Start marker found
            packet_start = marker_idx + len(PACKET_START_MARKER)
            # Check if there are enough bytes for a complete packet
            if len(self._buffer) >= packet_start + PACKET_BYTE_SIZE:
                # Extract the packet (84 bytes)
                packet = self._buffer[packet_start:packet_start + PACKET_BYTE_SIZE]
                # Remove the processed marker and packet from the buffer
                self._buffer = self._buffer[packet_start + PACKET_BYTE_SIZE:]
                # Process and return the packet
                return self._process_packet_data(packet)

        return None  # No complete packet available