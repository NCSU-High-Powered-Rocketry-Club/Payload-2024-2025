import time
import socket
from gpiozero import OutputDevice

# GPIO pin setup
GPIO_PIN = 8
ptt = OutputDevice(GPIO_PIN, initial_value=True)  # Default to high (inactive)

# Direwolf KISS TCP connection details
KISS_HOST = "127.0.0.1"  # Localhost where Direwolf is running
KISS_PORT = 8001  # KISS TCP port


def pull_pin_low():
    """Activate PTT (Push-To-Talk) by pulling the pin LOW."""
    ptt.off()


def pull_pin_high():
    """Deactivate PTT by pulling the pin HIGH."""
    ptt.on()


def send_kiss_packet(payload):
    """Send an APRS packet using the KISS TCP interface to Direwolf."""
    try:
        # Open a socket connection to Direwolf's KISS interface
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((KISS_HOST, KISS_PORT))

            # KISS frame: 0xC0 (Start), 0x00 (Data Frame), payload, 0xC0 (End)
            kiss_frame = b"\xc0\x00" + payload.encode() + b"\xc0"
            sock.sendall(kiss_frame)

        print("APRS packet sent successfully via KISS mode.")
    except Exception as e:
        print(f"Failed to send APRS packet: {e}")


def main():
    pull_pin_low()  # Activate PTT
    time.sleep(0.5)  # Small delay to ensure PTT is engaged

    # Construct an APRS packet
    aprs_message = (
        "YOURCALL-1>APRS,TCPIP*:="
        "3749.00N/12224.00W-This is a test message"
    )  # Replace with actual lat/lon

    send_kiss_packet(aprs_message)  # Send packet via KISS

    time.sleep(2)  # Hold PTT for a short duration after sending
    pull_pin_high()  # Release PTT
    print("Transmission complete. Pin reset.")


if __name__ == "__main__":
    main()
