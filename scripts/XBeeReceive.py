import serial

SERIAL_PORT = "/dev/ttyAMA0"
BAUD_RATE = 9600


def read_serial():
    try:
        with serial.Serial(SERIAL_PORT, BAUD_RATE) as ser:
            print(f"V3: Listening on {SERIAL_PORT} at {BAUD_RATE} baud rate...")
            while True:
                line = ser.readline().decode("utf-8", errors="ignore").strip()
                if line:
                    print(f"Received: {line}")
    except serial.SerialException as e:
        print(f"Error: {e}")
    except KeyboardInterrupt:
        print("Serial reading stopped.")


if __name__ == "__main__":
    read_serial()
