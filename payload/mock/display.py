"""File to handle the display of real-time flight data in the terminal."""

import argparse
import threading
import time
from typing import TYPE_CHECKING

from colorama import Fore, Style, init

from payload.constants import DisplayEndingType
from payload.utils import convert_milliseconds_to_seconds

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
        "_payload",
        "_running",
        "_start_time",
        "_thread_target",
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
        self._running = threading.Event()
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

    def start(self) -> None:
        """
        Starts the display.
        """
        self._running.set()
        self._thread_target.start()

    def stop(self) -> None:
        """
        Stops the display thread.
        """
        self._running.clear()
        self._thread_target.join()

    def update_display(self) -> None:
        """
        Updates the display with real-time data. Runs in another thread. Automatically stops when
        the replay ends.
        """
        # Don't print the flight data if we are in debug mode
        if self._args.debug:
            return

        # Update the display as long as the program is running:
        while self._running.is_set():
            self._update_display()

            # If we are running a real flight, we will stop the display when the rocket takes off:
            # if self._args.mode == "real" and self._payload.state.name == "MotorBurnState":
            #     self._update_display(DisplayEndingType.TAKEOFF)
            #     break

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
        data_processor = self._payload.data_processor
        # Set the launch time if it hasn't been set yet:
        if not self._launch_time and self._payload.state.name == "MotorBurnState":
            self._launch_time = self._payload.state.start_time_ms

        if self._launch_time:
            time_since_launch = convert_milliseconds_to_seconds(
                self._payload.data_processor.current_timestamp - self._launch_time
            )
        else:
            time_since_launch = 0

        # Prepare output
        output = [
            f"{Y}{'=' * 17} {'REPLAY' if self._args.mode == 'mock' else 'STANDBY'} INFO {'=' * 17}{RESET}",  # noqa: E501
            f"Replay file:                  {C}{self._launch_file}{RESET}",
            f"Time since replay start:      {C}{time.time() - self._start_time:<10.2f}{RESET} {R}s{RESET}",  # noqa: E501
            f"{Y}{'=' * 12} REAL TIME FLIGHT DATA {'=' * 12}{RESET}",
            # Format time as MM:SS:
            f"Launch time:               {G}T+{time.strftime('%M:%S', time.gmtime(time_since_launch))}{RESET}",  # noqa: E501
            f"State:                     {G}{self._payload.state.name:<15}{RESET}",
            f"Current Altitude:          {G}{data_processor.current_altitude:<10.2f}{RESET} {R}m{RESET}",  # noqa: E501
            f"Maximum Altitude:          {G}{data_processor.max_altitude:<10.2f}{RESET} {R}m{RESET}",  # noqa: E501
            f"Current Velocity:          {G}{data_processor.velocity_moving_average:<10.2f}{RESET} {R}m/s{RESET}",  # noqa: E501
            f"Maximum Velocity:          {G}{data_processor.max_vertical_velocity:<10.2f}{RESET} {R}m/s{RESET}",  # noqa: E501
            f"Crew survivability:        {G}{100 * data_processor._crew_survivability:<10.2f}{RESET} {R}%{RESET}",  # noqa: E501
        ]

        imu_data = self._payload.imu_data_packet

        # Adds additional info to the display if -v was specified
        if self._args.verbose and imu_data:
            output.extend(
                [
                    f"{Y}{'=' * 18} DEBUG INFO {'=' * 17}{RESET}",
                    f"Landing velocity:          {G}{data_processor._landing_velocity:<10.2f}{RESET} {R}m/s{RESET}",  # noqa: E501
                    f"Transmitter message:       {G}{str(self._payload.transmission_packet)[:14]}{RESET}",  # noqa: E501
                    f"Receiver message:          {G}{self._payload.receiver.latest_message[:14]}{RESET}",  # noqa: E501
                    f"{Y}{'=' * 19} IMU INFO {'=' * 18}{RESET}",
                    f"Timestamp:                 {G}{imu_data.timestamp:9.2f}{RESET} {R}ms{RESET}",
                    f"Voltage pi:                {G}{imu_data.voltage_pi:6.2f}{RESET} {R}%{RESET}",
                    f"Voltage tx:                {G}{imu_data.voltage_tx:6.2f}{RESET} {R}%{RESET}",
                    f"Temperature:               {G}{imu_data.ambientTemperature:6.2f}{RESET} {R}°C{RESET}",  # noqa: E501
                    f"Pressure:                  {G}{imu_data.ambientPressure:6.2f}{RESET} {R}mbar{RESET}",  # noqa: E501
                    f"Pressure Altitude:         {G}{imu_data.pressureAlt:6.2f}{RESET} {R}m{RESET}",
                    f"Compensated Accel:         {G}<{imu_data.estCompensatedAccelX:6.2f}, {imu_data.estCompensatedAccelY:6.2f}, {imu_data.estCompensatedAccelZ:6.2f}>{RESET} {R}m/s²{RESET}",  # noqa: E501
                    f"Angular Rate:              {G}<{imu_data.estAngularRateX:6.2f}, {imu_data.estAngularRateY:6.2f}, {imu_data.estAngularRateZ:6.2f}>{RESET} {R}rad/s{RESET}",  # noqa: E501
                    f"Magnetic Field:            {G}<{imu_data.magneticFieldX:6.2f}, {imu_data.magneticFieldY:6.2f}, {imu_data.magneticFieldZ:6.2f}>{RESET} {R}microT{RESET}",  # noqa: E501
                    f"Orient Quaternions:        {G}<{imu_data.estOrientQuaternionW:6.2f}, {imu_data.estOrientQuaternionX:6.2f}, {imu_data.estOrientQuaternionY:6.2f}, {imu_data.estOrientQuaternionZ:6.2f}>{RESET}",  # noqa: E501
                    f"GPS Latitude:              {G}{imu_data.gpsLatitude:8.4f}{RESET} {R}°{RESET}",
                    f"GPS Longitude:             {G}{imu_data.gpsLongitude:8.4f}{RESET} {R}°{RESET}",  # noqa: E501
                    f"GPS Altitude:              {G}{imu_data.gpsAltitude:8.4f}{RESET} {R}m{RESET}",
                    # f"Status Flag:               {G}{imu_data.statusFlag:6.2f}{RESET} {R}{RESET}",  # noqa: E501
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
                print(f"{R}{'=' * 16} END OF REPLAY {'=' * 16}{RESET}")
            case DisplayEndingType.INTERRUPTED:
                print(f"{R}{'=' * 14} INTERRUPTED REPLAY {'=' * 13}{RESET}")
            case DisplayEndingType.TAKEOFF:
                print(f"{R}{'=' * 13} ROCKET LAUNCHED {'=' * 14}{RESET}")
