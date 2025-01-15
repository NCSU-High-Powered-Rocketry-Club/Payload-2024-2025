import serial
import time

# Adjust the port name based on your setup (often /dev/ttyACM0 or /dev/ttyUSB0)
ser = serial.Serial('/dev/ttyACM0', 115200, timeout=1)
time.sleep(2)  # Give time for the serial connection to establish

while True:
    if ser.in_waiting > 0:
        line = ser.readline().decode('utf-8').strip()
        print(line)  # Print or process the data as needed
