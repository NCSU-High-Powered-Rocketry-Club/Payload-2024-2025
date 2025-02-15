import serial
from payload.constants import RECEIVER_SERIAL_TIMEOUT, RECEIVER_SERIAL_PORT, RECEIVER_BAUD_RATE


def read_serial():
    """Simulates core read behavior of Receiver class without threading."""
    latest_message = "NO_MESSAGE"

    try:
        with serial.Serial(
                port=RECEIVER_SERIAL_PORT,
                baudrate=RECEIVER_BAUD_RATE,
                timeout=RECEIVER_SERIAL_TIMEOUT
        ) as ser:
            print(f"Listening on {RECEIVER_SERIAL_PORT} at {RECEIVER_BAUD_RATE} baud...")

            while True:
                # Check for data before reading (non-blocking check)
                if ser.in_waiting > 0:
                    line = ser.readline().decode("utf-8", errors="ignore").strip()
                    if line:
                        latest_message = line
                        print(f"Received: {latest_message}")

    except serial.SerialException as e:
        print(f"Serial error: {e}")
    except KeyboardInterrupt:
        print("\nStopped listening. Final message:", latest_message)


if __name__ == "__main__":
    read_serial()
