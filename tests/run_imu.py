import serial
import struct
import time

from payload.constants import ARDUINO_SERIAL_TIMEOUT, PACKET_BYTE_SIZE, PACKET_START_MARKER
from payload.data_handling.packets.imu_data_packet import IMUDataPacket


def process_packet_data(binary_packet: bytes) -> IMUDataPacket:
    """
    Unpacks the binary packet into an IMUDataPacket instance.
    The format string assumes little-endian floats.
    """
    # Calculate number of floats (each float is 4 bytes)
    num_floats = PACKET_BYTE_SIZE // 4
    # Unpack the binary data
    unpacked_data = struct.unpack("<" + "f" * num_floats, binary_packet)
    return IMUDataPacket(*unpacked_data)


def main():
    # Adjust the port (e.g., '/dev/ttyUSB0' for Linux or 'COM3' for Windows)
    port = '/dev/ttyUSB0'
    baud_rate = 115200

    # Open the serial port
    ser = serial.Serial(port, baud_rate, timeout=ARDUINO_SERIAL_TIMEOUT)
    print(f"Connected to Arduino on port {port}")

    try:
        while True:
            # Wait until there is enough data for a full packet (start marker + packet)
            if ser.in_waiting >= PACKET_BYTE_SIZE + 1:
                # Read one byte at a time until we find the start marker.
                marker = ser.read(1)
                if marker == PACKET_START_MARKER:
                    binary_packet = ser.read(PACKET_BYTE_SIZE)
                    # Check that we received a full packet
                    if len(binary_packet) == PACKET_BYTE_SIZE:
                        imu_packet = process_packet_data(binary_packet)
                        print(imu_packet.pressureAlt)
            else:
                time.sleep(0.01)
    except KeyboardInterrupt:
        print("Exiting...")
    finally:
        ser.close()


if __name__ == '__main__':
    main()
