"""Module for interacting with the IMU (Inertial Measurement Unit) on the rocket."""

import struct

import serial

from payload.constants import ARDUINO_SERIAL_TIMEOUT, PACKET_BYTE_SIZE, PACKET_START_MARKER
from payload.data_handling.packets.imu_data_packet import IMUDataPacket
from payload.interfaces.base_imu import BaseIMU


class IMU(BaseIMU):
    """
    Represents the IMU on the rocket. This is used to interact with the data collected by the
    Arduino.
    """
    __slots__ = ("_baud_rate", "_buffer", "_port", "_serial")

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
    def _process_packet_data(binary_packet: bytes) -> IMUDataPacket:
        """
        Processes the data points in the unpacked packet into an IMUDataPacket.

        :param binary_packet: The serialized data packet (84 bytes) containing multiple data points.
        :return: An IMUDataPacket object with the unpacked data.
        """
        # Unpack 84 bytes into 21 floats (84 / 4 = 21), assuming little-endian format
        # TODO: Handle statusFlags appropriately if part of the packet structure
        unpacked_data = struct.unpack("<" + "f" * (PACKET_BYTE_SIZE // 4), binary_packet)
        return IMUDataPacket(*unpacked_data)

    def _read_data(self) -> None:
        """Function that reads data from the serial port and processes it."""
        while self.is_running:
            new_data = self._serial.read(self._serial.in_waiting)
            if new_data:
                self._buffer += new_data
                # Process buffer for packets
                marker_idx = self._buffer.find(PACKET_START_MARKER)
                if marker_idx == -1:  # No marker found
                    continue

                packet_start = marker_idx + len(PACKET_START_MARKER)
                if len(self._buffer) >= packet_start + PACKET_BYTE_SIZE:
                    # Extract and process packet
                    packet = self._buffer[packet_start:packet_start + PACKET_BYTE_SIZE]
                    self._buffer = self._buffer[packet_start + PACKET_BYTE_SIZE:]
                    data_packet = self._process_packet_data(packet)
                    self._queued_imu_packets.put(data_packet)
                else:
                    continue  # Not enough data for a full packet

    def start(self):
        """Opens the serial connection to the Arduino."""
        self._serial = serial.Serial(self._port, self._baud_rate, timeout=ARDUINO_SERIAL_TIMEOUT)
        super().start()

    def stop(self):
        """Closes the serial connection to the Arduino."""
        super().stop()
        if self._serial:
            self._serial.close()
