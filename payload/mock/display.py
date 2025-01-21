"""File to handle the display of real-time flight data in the terminal."""

import argparse
import multiprocessing
import threading
import time
from typing import TYPE_CHECKING

import psutil
from colorama import Fore, Style, init

from payload.constants import DisplayEndingType

if TYPE_CHECKING:
    from payload.payload import PayloadContext


# Shorten colorama names, I (jackson) don't love abbreviations but this is a lot of typing and
# ruff doesn't like when the lines are too long and they are ugly when long (harshil)
G = Fore.GREEN
R = Fore.RED
Y = Fore.YELLOW
C = Fore.CYAN
RESET = Style.RESET_ALL


class FlightDisplay:
    """Class related to displaying real-time flight data in the terminal with pretty colors
    and spacing.
    """

    # Initialize Colorama
    MOVE_CURSOR_UP = "\033[F"  # Move cursor up one line

    __slots__ = (
        "_args",
        "_coast_time",
        "_launch_file",
        "_launch_time",
        "_mock",
        "_payload",
        "_processes",
        "_start_time",
        "_thread_target",
        "_verbose",
        "end_mock_interrupted",
        "end_mock_natural",
    )

    def __init__(
        self, payload: "PayloadContext", start_time: float, args: argparse.Namespace
    ) -> None:
        """
        :param payload: The PayloadContext object.
        :param start_time: The time (in seconds) the replay started.
        """
        init(autoreset=True)  # Automatically reset colors after each print
        self._payload = payload
        self._start_time = start_time
        self._args = args
        self._launch_time: int = 0  # Launch time from MotorBurnState
        self._coast_time: int = 0  # Coast time from CoastState
        # daemon threads are killed when the main thread exits.
        self._thread_target = threading.Thread(
            target=self.update_display, daemon=True, name="Real Time Display Thread"
        )
        # Create events to signal the end of the replay.
        self.end_mock_natural = threading.Event()
        self.end_mock_interrupted = threading.Event()

        try:
            # Try to get the launch file name (only available in MockIMU)
            self._launch_file = self._payload.imu._log_file_path.name
        except AttributeError:  # If it failed, that means we are running a real flight!
            self._launch_file = "N/A"

    def update_display(self) -> None:
        """
        Updates the display with real-time data. Runs in another thread. Automatically stops when
        the replay ends.
        """
        # Don't print the flight data if we are in debug mode
        if self._args.debug:
            return
        self._update_display()
        # The program has ended, so we print the final display, depending on how it ended:
        if self.end_mock_natural.is_set():
            self._update_display(DisplayEndingType.NATURAL)
        if self.end_mock_interrupted.is_set():
            self._update_display(DisplayEndingType.INTERRUPTED)

    def _update_display(self, end_type: DisplayEndingType | None = None) -> None:
        """
        Updates the display with real-time data.
        :param end_type: Whether the replay ended or was interrupted.
        """

        fetched_packets = len(self._payload.imu_data_packet)

        data_processor = self._payload.data_processor


        # Set the launch time if it hasn't been set yet:
        if not self._launch_time and self._payload.state.name == "MotorBurnState":
            self._launch_time = self._payload.state.start_time_ns

        elif not self._coast_time and self._payload.state.name == "CoastState":
            self._coast_time = self._payload.state.start_time_ns

        if self._launch_time:
            time_since_launch = (
                self._payload.data_processor.current_timestamp - self._launch_time
            ) * 1e-4
        else:
            time_since_launch = 0

        # Prepare output
        output = [
            f"{Y}{'=' * 15} {"REPLAY" if self._args.mock else "STANDBY"} INFO {'=' * 15}{RESET}",
            f"Replay file:                  {C}{self._launch_file}{RESET}",
            f"Time since replay start:      {C}{time.time() - self._start_time:<10.2f}{RESET} {R}s{RESET}",  # noqa: E501
            f"{Y}{'=' * 12} REAL TIME FLIGHT DATA {'=' * 12}{RESET}",
            # Format time as MM:SS:
            f"Launch time:               {G}T+{time.strftime('%M:%S', time.gmtime(time_since_launch))}{RESET}",  # noqa: E501
            f"State:                     {G}{self._payload.state.name:<15}{RESET}",
            f"Current velocity:          {G}{data_processor.vertical_velocity:<10.2f}{RESET} {R}m/s{RESET}",  # noqa: E501
            f"Max velocity so far:       {G}{data_processor.max_vertical_velocity:<10.2f}{RESET} {R}m/s{RESET}",  # noqa: E501
            f"Current height:            {G}{data_processor.current_altitude:<10.2f}{RESET} {R}m{RESET}",  # noqa: E501
            f"Max height so far:         {G}{data_processor.max_altitude:<10.2f}{RESET} {R}m{RESET}",  # noqa: E501
        ]

        # Adds additional info to the display if -v was specified
        if self._args.verbose:
            output.extend(
                [
                    f"{Y}{'=' * 18} DEBUG INFO {'=' * 17}{RESET}",
                    f"Fetched packets:                 {G}{fetched_packets:<10}{RESET} {R}packets{RESET}",  # noqa: E501
                    f"Log buffer size:                 {G}{len(self._payload.logger._log_buffer):<10}{RESET} {R}packets{RESET}",  # noqa: E501
                    f"{Y}{'=' * 13} REAL TIME CPU LOAD {'=' * 14}{RESET}",
                ]
            )

        # Print the output
        print("\n".join(output))

        # Move the cursor up for the next update, if the replay hasn't ended:
        if not end_type:
            print(self.MOVE_CURSOR_UP * len(output), end="", flush=True)

        # Print the end of replay message if the replay has ended
        match end_type:
            case DisplayEndingType.NATURAL:
                print(f"{R}{'=' * 14} END OF REPLAY {'=' * 14}{RESET}")
            case DisplayEndingType.INTERRUPTED:
                print(f"{R}{'=' * 12} INTERRUPTED REPLAY {'=' * 13}{RESET}")
            case DisplayEndingType.TAKEOFF:
                print(f"{R}{'=' * 13} ROCKET LAUNCHED {'=' * 14}{RESET}")

