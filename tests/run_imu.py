import serial
import struct
import time

from payload.constants import PACKET_BYTE_SIZE, ARDUINO_SERIAL_TIMEOUT, PACKET_START_MARKER
from payload.data_handling.packets.imu_data_packet import IMUDataPacket

# Define the expected marker value (must match what is used on the Arduino)
# PACKET_START_MARKER = -1e30  # Use the same value
MOVE_CURSOR_UP = "\033[F"  # Move cursor up one line

# Open the serial port (adjust as needed)
ser = serial.Serial('/dev/ttyUSB1', 115200, timeout=ARDUINO_SERIAL_TIMEOUT)

def fetch_data(ser):
    # Wait until there's enough data: marker + packet data
    if ser.in_waiting >= 4 + PACKET_BYTE_SIZE:
        # Read marker bytes and convert to float
        marker_bytes = ser.read(4)
        # print(marker_bytes)
        (marker,) = struct.unpack("<f", marker_bytes)
        # print(marker)
        if marker_bytes == PACKET_START_MARKER:
            # print("found start marker")
            binary_packet = ser.read(PACKET_BYTE_SIZE)
            if len(binary_packet) == PACKET_BYTE_SIZE:
                return process_packet_data(binary_packet)
    return None

def process_packet_data(binary_packet):
    num_floats = PACKET_BYTE_SIZE // 4
    unpacked_data = struct.unpack("<" + "f" * num_floats, binary_packet)
    # Assuming IMUDataPacket is defined appropriately to accept these values.
    return IMUDataPacket(*unpacked_data)

# Example main loop:
try:
    while True:
        packet = fetch_data(ser)
        if packet is not None:
            print(packet.timestamp, packet.ambientPressure, packet.estCompensatedAccelX)
            print(MOVE_CURSOR_UP, end="", flush=True)
        else:
            time.sleep(0.01)
except KeyboardInterrupt:
    print("Exiting...")
finally:
    ser.close()
