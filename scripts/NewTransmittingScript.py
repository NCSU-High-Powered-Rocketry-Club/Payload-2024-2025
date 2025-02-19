import time
import socket

# Direwolf KISS TCP connection details
KISS_HOST = "127.0.0.1"  # Localhost where Direwolf is running
KISS_PORT = 8001  # KISS TCP port

def send_kiss_packet(payload):
    """Send an APRS packet using the KISS TCP interface to Direwolf."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((KISS_HOST, KISS_PORT))
            # KISS frame: 0xC0 (Start), 0x00 (Data Frame), payload, 0xC0 (End)
            kiss_frame = b"\xc0\x00" + payload.encode() + b"\xc0"
            sock.sendall(kiss_frame)
        print("✅ APRS packet sent successfully via KISS mode.")
    except Exception as e:
        print(f"❌ Failed to send APRS packet: {e}")

def main():
    # Construct an APRS packet
    aprs_message = (
        "YOURCALL-1>APRS,TCPIP*:="
        "3749.00N/12224.00W-This is a test message"
    )  # Replace with actual callsign & lat/lon

    send_kiss_packet(aprs_message)  # Send packet via KISS
    time.sleep(2)  # Short delay to ensure transmission completes

if __name__ == "__main__":
    main()
