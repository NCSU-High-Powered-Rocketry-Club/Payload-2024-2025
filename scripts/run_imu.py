import serial
import json
import struct

# Configure your serial port and baud rate
SERIAL_PORT = "/dev/ttyS7"
BAUD_RATE = 11522

ser = serial.Serial(SERIAL_PORT, BAUD_RATE)

while True:
    data = ser.read(92)
    unpacked_data = struct.unpack('<f' * 18, data)
    print(unpacked_data)
