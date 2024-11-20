# For Command line arguments
import argparse
import RPi.GPIO as GPIO
import time

XBEE_SHUTDOWN_PIN = 18
# GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(XBEE_SHUTDOWN_PIN, GPIO.OUT)
GPIO.output(XBEE_SHUTDOWN_PIN, GPIO.HIGH)

time.sleep(2)
if True:
    # Payload module
    import spaceducks


# Program description
msg = "Main HPRC Payload Program for 2024-2025."

# Initialize parser
parser = argparse.ArgumentParser(description=msg)

# Callsign argument
parser.add_argument(
    "callsign", help="Callsign to use for transmission. NOTRANSMIT to disable."
)

# Port arguments
parser.add_argument("xbee_port", help="Port to use for XBee communication")

parser.add_argument("feather_port", help="Port to use for feather sensor reading")

args = parser.parse_args()


def main(args):

    payload = spaceducks.PayloadSystem(args.callsign, args.xbee_port, args.feather_port)

    try:
        while payload.running:
            payload.update()

    except KeyboardInterrupt:
        # Early shutdown if interrupted
        payload.shutdown()

    print("Program complete. Waiting for recovery.")


if __name__ == "__main__":
    main(args)
