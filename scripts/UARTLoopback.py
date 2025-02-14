import serial

ser = serial.Serial(port="/dev/ttyAMA0", baudrate=9600, timeout=1)

try:
    test_message = "Hello, UART!\n"
    ser.write(test_message.encode())  # Send data
    print("Sent:", test_message.strip())

    received_data = ser.readline().decode().strip()  # Read response
    print("Received:", received_data)

    if received_data == test_message.strip():
        print("RX Pin is working correctly!")
    else:
        print("No data received. Check wiring and UART settings.")

except Exception as e:
    print("Error:", e)

finally:
    ser.close()
