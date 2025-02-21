import serial
import csv
import struct
import numpy

# Configure your serial port and baud rate
SERIAL_PORT = "/dev/ttyUSB0"
BAUD_RATE = 115200
BYTE_SIZE = 80
CSV_FILE = 'test_data.csv'

ser = serial.Serial(SERIAL_PORT, BAUD_RATE,timeout=100)

header = [
    'timestamp', 'voltage', 'temperature', 'pressure', 
    'comp_accel_x', 'comp_accel_y', 'comp_accel_z',
    'gyro_x', 'gyro_y', 'gyro_z',
    'magnetic_x', 'magnetic_y', 'magnetic_z',
    'quat_w', 'quat_x', 'quat_y', 'quat_z',
    'gps_lat', 'gps_long', 'gps_alt'
]
last_t = 1
tlist = []
# Open the CSV file in append mode, and create it if it doesn't exist
with open(CSV_FILE, mode='w', newline='') as file:
    writer = csv.writer(file)

    writer.writerow(header)

    while True:
        data = ser.read(BYTE_SIZE)
        #print(data)
        try:
            unpacked_data = struct.unpack('<'+'f'*(BYTE_SIZE//4), data)
            # Print the unpacked values
            writer.writerow(unpacked_data)
            t = unpacked_data[0]
            diff = t-last_t
            print(1000/(diff+0.0001))
            last_t = t

            

        except struct.error as e:
            print(f"Unpacking error: {e}")
            print(f"Raw data: {data}")
