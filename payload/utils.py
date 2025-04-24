"""File which contains a few basic utility functions which can be reused in the project."""

import argparse
from pathlib import Path


def convert_milliseconds_to_seconds(timestamp: float) -> float | None:
    """Converts milliseconds to seconds"""
    return timestamp / 1e3


def deadband(input_value: float, threshold: float) -> float:
    """
    Returns 0 if the input_value is within the deadband threshold.
    Otherwise, returns the input_value adjusted by the threshold.
    :param input_value: The value to apply the deadband to.
    :param threshold: The deadband threshold.
    :return: Adjusted input_value or 0 if within the deadband.
    """
    if abs(input_value) < threshold:
        return 0.0
    return input_value


def arg_parser() -> argparse.Namespace:
    """Handles the command line arguments for the main payload script.

    :return: The parsed arguments as a class with attributes.
    """
    # We require ONE and only one of the 2 positional arguments to be passed:
    # - real: Run the real flight with all the real hardware.
    # - mock: Run in replay mode with mock data and mock servo.
    global_parser = argparse.ArgumentParser(add_help=False)

    # Global mutually exclusive group, for the `--debug` and `--verbose` options:
    global_group = global_parser.add_mutually_exclusive_group()

    # These are global options, available to `mock`, `real`, and `sim` modes:
    global_group.add_argument(
        "-d",
        "--debug",
        help="Run the flight without a display. This will not "
        "print the flight data and allow you to inspect the values of your print() statements.",
        action="store_true",
        default=False,
    )

    global_group.add_argument(
        "-v",
        "--verbose",
        help="Shows the display with much more data.",
        action="store_true",
        default=False,
    )

    global_parser.add_argument(
        "-k",
        "--callsign",
        help="Input callsign to use in post-landing transmission.",
        type=str,
        default=None
    )

    # Top-level mock_replay_parser.for the main script:
    main_parser = argparse.ArgumentParser(
        description="Main mock_replay_parser for the payload script.",
        parents=[global_parser],
    )

    # Subparsers for `real`, `mock`
    subparsers = main_parser.add_subparsers(
        title="modes", description="Valid modes of operation", dest="mode", required=True
    )

    # Real flight parser:
    subparsers.add_parser(
        "real",
        help="Run the real flight with all the real hardware.",
        description="Configuration for the real flight.",
        parents=[global_parser],  # Include the global options
        prog="real",  # Program name in help messages
    )
    # No extra arguments needed for the real flight mode.

    # Mock replay parser:
    mock_replay_parser = subparsers.add_parser(
        "mock",
        help="Run in replay mode with mock data (i.e. previous flight data)",
        description="Configuration for the mock replay payload script.",
        parents=[global_parser],  # Include the global options
        prog="mock",  # Program name in help messages
    )

    mock_replay_parser.add_argument(
        "-l",
        "--keep-log-file",
        help="Keep the log file after the mock stops",
        action="store_true",
        default=False,
    )

    mock_replay_parser.add_argument(
        "-f",
        "--fast-replay",
        help="Run the mock at full speed instead of in real time.",
        action="store_true",
        default=False,
    )

    mock_replay_parser.add_argument(
        "-c",
        "--real-camera",
        help="Run the mock with the real camera.",
        action="store_true",
        default=False,
    )

    mock_replay_parser.add_argument(
        "-r",
        "--real-receiver",
        help="Run the mock replay with the real receiver.",
        action="store_true",
        default=False,
    )

    mock_replay_parser.add_argument(
        "-t",
        "--real-transmitter",
        help="Run the mock replay with the real transmitter.",
        action="store_true",
        default=False,
    )

    mock_replay_parser.add_argument(
        "-i",
        "--real-imu",
        help="Run the mock replay with the real imu.",
        action="store_true",
        default=False,
    )
    mock_replay_parser.add_argument(
        "-p",
        "--path",
        help="Define the pathname of flight data to use in mock replay. By default, the"
        " first file found in the launch_data directory will be used if not specified.",
        type=Path,
        default=None,
    )

    return main_parser.parse_args()
