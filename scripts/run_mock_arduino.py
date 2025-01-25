import serial
import struct
import time
import random

# Configure your serial port and baud rate
SERIAL_PORT = "COM50"
BAUD_RATE = 115200

# Structure of the data packet
DATA_FORMAT = '<' + 'f' * 23  # Format for 23 float values
BYTE_SIZE = struct.calcsize(DATA_FORMAT)

# Example data packet structure
def generate_packet():
    return struct.pack(
        DATA_FORMAT,
        time.time(),  # timestamp
        random.uniform(3.3, 4.2),  # voltage
        random.uniform(20, 40),  # temperature
        random.uniform(950, 1050),  # pressure
        random.uniform(-2, 2),  # comp_accel_x
        random.uniform(-2, 2),  # comp_accel_y
        random.uniform(-2, 2),  # comp_accel_z
        random.uniform(-500, 500),  # gyro_x
        random.uniform(-500, 500),  # gyro_y
        random.uniform(-500, 500),  # gyro_z
        random.uniform(-100, 100),  # magnetic_x
        random.uniform(-100, 100),  # magnetic_y
        random.uniform(-100, 100),  # magnetic_z
        random.uniform(-1, 1),  # quat_w
        random.uniform(-1, 1),  # quat_x
        random.uniform(-1, 1),  # quat_y
        random.uniform(-1, 1),  # quat_z
        random.uniform(-2, 2),  # lin_accel_x
        random.uniform(-2, 2),  # lin_accel_y
        random.uniform(-2, 2),  # lin_accel_z
        random.uniform(-90, 90),  # gps_lat
        random.uniform(-180, 180),  # gps_long
        random.uniform(0, 10000)  # gps_alt
    )

# Open the serial port
with serial.Serial(SERIAL_PORT, BAUD_RATE) as ser:
    while True:
        packet = generate_packet()
        ser.write(packet)
        time.sleep(1)  # Send data every second
