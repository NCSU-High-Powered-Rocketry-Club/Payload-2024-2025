"""The main file which will be run on the Raspberry Pi. It will create the PayloadContext object
and run the main loop."""

import argparse
import time

from payload.constants import BAUD_RATE, SERIAL_PORT, LOGS_PATH
from payload.data_handling.data_processor import IMUDataProcessor
from payload.data_handling.logger import Logger
from payload.hardware.imu import IMU
from payload.mock.display import FlightDisplay
from payload.mock.mock_imu import MockIMU
from payload.mock.mock_logger import MockLogger
from payload.payload import PayloadContext
from payload.utils import arg_parser

def run_real_flight() -> None:
    """Entry point for the application to run the real flight. Entered when run with
    `uv run real` or `uvx --from git+... real`."""
    args = arg_parser()
    run_flight(args)


def run_mock_flight() -> None:
    """Entry point for the application to run the mock flight. Entered when run with
    `uvx --from git+... mock` or `uv run mock`."""
    args = arg_parser(mock_invocation=True)
    run_flight(args)


def run_flight(args: argparse.Namespace) -> None:
    mock_time_start = time.time()

    imu, logger, data_processor = create_components(args)
    # Initialize the airbrakes context and display
    payload = PayloadContext(imu, logger, data_processor)
    flight_display = FlightDisplay(payload, mock_time_start, args)

    # Run the main flight loop
    run_flight_loop(payload, flight_display)


def create_components(
    args: argparse.Namespace,
) -> tuple[IMU, Logger, IMUDataProcessor]:
    """
    Creates the system components needed for the payload system. Depending on its arguments, it
    will return either mock or real components.
    :param args: Command line arguments determining the configuration.
    :return: A tuple containing the IMU, Logger, and data processor objects
    """
    if args.mock:
        # Replace hardware with mock objects for mock replay
        imu = MockIMU(
            real_time_replay=not args.fast_replay,
            log_file_path=args.path,
        )
        logger = MockLogger(LOGS_PATH, delete_log_file=not args.keep_log_file)
    else:
        # Use real hardware components
        imu = IMU(SERIAL_PORT,BAUD_RATE)
        logger = Logger(LOGS_PATH)

    # Initialize data processing
    data_processor = IMUDataProcessor()
    return imu, logger, data_processor


def run_flight_loop(
    payload: PayloadContext, flight_display: FlightDisplay
) -> None:
    """
    Main flight control loop that runs until shutdown is requested or interrupted.
    :param payload: The payload context managing the state machine.
    :param flight_display: Display interface for flight data.
    :param is_mock: Whether running in mock replay mode.
    """
    try:
        while True:
            # Update the state machine
            payload.update()
            flight_display.update_display()
    except KeyboardInterrupt:
        flight_display.end_mock_interrupted.set()
        payload.logger.stop()


if __name__ == "__main__":
    args = arg_parser()
    run_flight(args)
