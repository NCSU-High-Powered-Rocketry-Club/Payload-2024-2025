# For Command line arguments
import argparse

# Payload system
import payload


# Program description
msg = "Main HPRC Payload Program for 2024-2025."

# Initialize parser
parser = argparse.ArgumentParser(description=msg)

# TODO: Add any arguments we might need
# parser.add_argument("-f", "--Frequency", help="APRS Frequency in MHz")

args = parser.parse_args()


def main(args):

    payload = payload.PayloadSystem()

    try:
        while not payload.ready_to_shutdown:
            payload.update()

    except KeyboardInterrupt:
        pass

    payload.shutdown()

    print("Program complete. Waiting for recovery.")


if __name__ == "__main__":
    main(args)
