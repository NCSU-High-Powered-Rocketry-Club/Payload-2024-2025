"""The main file which will be run on the Raspberry Pi. It will create the PayloadContext object
and run the main loop."""

import argparse
import sys
import time

from payload.constants import (
    ARDUINO_BAUD_RATE,
    ARDUINO_SERIAL_PORT,
    DIREWOLF_CONFIG_PATH,
    LOGS_PATH,
    MOCK_MESSAGE_PATH,
    MOCK_RECEIVER_INITIAL_DELAY,
    MOCK_RECEIVER_RECEIVE_DELAY,
    RECEIVER_BAUD_RATE,
    RECEIVER_SERIAL_PORT,
    TRANSMIT_MESSAGE,
    TRANSMITTER_PIN,
)
from payload.data_handling.data_processor import DataProcessor
from payload.data_handling.logger import Logger
from payload.hardware.camera import Camera
from payload.hardware.imu import IMU
from payload.hardware.receiver import Receiver
from payload.hardware.transmitter import Transmitter
from payload.interfaces.base_imu import BaseIMU
from payload.interfaces.base_receiver import BaseReceiver
from payload.mock.display import FlightDisplay
from payload.mock.mock_camera import MockCamera
from payload.mock.mock_imu import MockIMU
from payload.mock.mock_logger import MockLogger
from payload.mock.mock_receiver import MockReceiver
from payload.mock.mock_transmitter import MockTransmitter
from payload.payload import PayloadContext
from payload.utils import arg_parser


def run_real_flight() -> None:
    """Entry point for the application to run the real flight. Entered when run with
    `uv run real` or `uvx --from git+... real`."""
    # Modify sys.argv to include `real` as the first argument:
    sys.argv.insert(1, "real")
    args = arg_parser()
    run_flight(args)


def run_mock_flight() -> None:
    """Entry point for the application to run the mock flight. Entered when run with
    `uvx --from git+... mock` or `uv run mock`."""
    # Modify sys.argv to include `mock` as the first argument:
    sys.argv.insert(1, "mock")
    args = arg_parser()
    run_flight(args)


def run_flight(args: argparse.Namespace) -> None:
    mock_time_start = time.time()

    imu, logger, data_processor, transmitter, receiver, camera = create_components(args)
    # Initialize the payload context and display
    payload = PayloadContext(imu, logger, data_processor, transmitter, receiver, camera)
    flight_display = FlightDisplay(payload, mock_time_start, args)

    # Run the main flight loop
    run_flight_loop(payload, flight_display, args)


def create_components(
    args: argparse.Namespace,
) -> tuple[BaseIMU, Logger, DataProcessor, Transmitter, BaseReceiver, Camera]:
    """
    Creates the system components needed for the payload system. Depending on its arguments, it
    will return either mock or real components.
    :param args: Command line arguments determining the configuration.
    :return: A tuple containing the objects needed to initialize `PayloadContext`.
    """
    if args.mode == "mock":
        # Replace hardware with mock objects for mock replay
        imu = (
            IMU(ARDUINO_SERIAL_PORT, ARDUINO_BAUD_RATE)
            if args.real_imu
            else MockIMU(
                log_file_path=args.path,
                real_time_replay=not args.fast_replay,
            )
        )
        logger = MockLogger(LOGS_PATH, delete_log_file=not args.keep_log_file)
        transmitter = (
            Transmitter(TRANSMITTER_PIN, DIREWOLF_CONFIG_PATH)
            if args.real_transmitter
            else MockTransmitter(MOCK_MESSAGE_PATH)
        )
        receiver = (
            Receiver(RECEIVER_SERIAL_PORT, RECEIVER_BAUD_RATE)
            if args.real_receiver
            else MockReceiver(
                MOCK_RECEIVER_INITIAL_DELAY, MOCK_RECEIVER_RECEIVE_DELAY, TRANSMIT_MESSAGE
            )
        )
        camera = Camera() if args.real_camera else MockCamera()
    else:
        # Use real hardware components
        imu = IMU(ARDUINO_SERIAL_PORT, ARDUINO_BAUD_RATE)
        logger = Logger(LOGS_PATH)
        transmitter = Transmitter(TRANSMITTER_PIN, DIREWOLF_CONFIG_PATH)
        receiver = Receiver(RECEIVER_SERIAL_PORT, RECEIVER_BAUD_RATE)
        camera = Camera()

    # Initialize data processing
    data_processor = DataProcessor()
    return imu, logger, data_processor, transmitter, receiver, camera


def run_flight_loop(
    payload: PayloadContext, flight_display: FlightDisplay, args: argparse.Namespace
) -> None:
    """
    Main flight control loop that runs until shutdown is requested or interrupted.
    :param payload: The payload context managing the state machine.
    :param flight_display: Display interface for flight data.
    :param args: Command line arguments determining the configuration.
    """
    payload.start()
    flight_display.start()

    try:
        while True:
            # Update the state machine
            payload.update()

            # For some reason if you put the below as a loop condition, Ctrl+C doesn't work!!
            if payload.shutdown_requested:
                break
            # Stop the replay when the data is exhausted
            if args.mode == "mock" and (not args.real_imu and not payload.imu.is_running):
                break

    # handle user interrupt gracefully
    except KeyboardInterrupt:
        if args.mode == "mock":
            flight_display.end_mock_interrupted.set()
    except Exception as e:
        # This is run if we have landed and the program is not interrupted (see state.py)
        raise e
        if args.mode == "mock":
            # Stop the mock replay naturally if not interrupted
            flight_display.end_mock_natural.set()
    finally:
        # Stop the display and payload
        flight_display.stop()
        payload.stop()


if __name__ == "__main__":
    args = arg_parser()
    run_flight(args)
