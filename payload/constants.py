"""Contains the constants used in the payload module"""

from enum import StrEnum, Enum
from pathlib import Path

# -------------------------------------------------------
# Display Configuration
# -------------------------------------------------------

DISPLAY_FREQUENCY = 10
"""The frequency at which the display updates in Hz"""


class DisplayEndingType(StrEnum):
    """
    Enum that represents the different ways the display can end.
    """

    NATURAL = "natural"
    """The display ends naturally, when the rocket lands, in a mock replay."""
    INTERRUPTED = "interrupted"
    """The display ends because the user interrupted the program."""
    TAKEOFF = "takeoff"
    """The display ends because the rocket took off."""


# -------------------------------------------------------
# IMU Configuration
# -------------------------------------------------------

ARDUINO_SERIAL_PORT = "/dev/ttyUSB0"
"""The port that the Arduino is connected to. This is typically the default port where the IMU
connects to the Raspberry Pi. To check the port, run `ls /dev/ttyUSB*` in the terminal."""
# ARDUINO_SERIAL_PORT = "COM5"

ARDUINO_BAUD_RATE = 115200
"""The baud rate of the channel"""
PACKET_START_MARKER = b"\xaa"
"""The start marker of the data packet. This helps use to know where a packet starts in the stream
of bytes."""
PACKET_BYTE_SIZE = 84
"""Size of the data packet being sent from the Arduino in bytes"""

# Timeouts for get() queue operations:
MAX_GET_TIMEOUT_SECONDS = 100  # seconds
"""The maximum amount of time in seconds to wait for a get operation on the queue."""

IMU_TIMEOUT_SECONDS = 3.0
"""The maximum amount of time in seconds the IMU process to do something (e.g. read a packet) before
it is considered to have timed out. This is used to prevent the program from deadlocking if the IMU
stops sending data."""

IMU_APPROXIMATE_FREQUENCY = 50
"""The frequency at which the IMU sends data packets, this is 50Hz"""

# -------------------------------------------------------
# Camera Configuration
# -------------------------------------------------------

CAMERA_SAVE_PATH = Path("logs/video.h264")

# -------------------------------------------------------
# Logging Configuration
# -------------------------------------------------------

LOGS_PATH = Path("logs")
"""The path of the folder to hold the log files in"""
TEST_LOGS_PATH = Path("test_logs")
"""The path of the folder to hold the test log files in"""

STOP_SIGNAL = "STOP"
"""The signal to stop the logging and the apogee prediction process, this will be put in the queue
to stop the process"""

# -------------------------------------------------------
# State Machine Configuration
# -------------------------------------------------------

# Arbitrarily set values for transition between states:

# ----------------- Standby to MotorBurn ----------------
ACCEL_DEADBAND_METERS_PER_SECOND_SQUARED = 0.5
"""We integrate our acceleration to get velocity, but because IMU has some noise, and other things
like wind or being small bumps can cause this to accumulate even while the rocket is stationary, so
we deadband the accel to prevent this."""

TAKEOFF_HEIGHT_METERS = 10
"""The height in meters that the rocket must reach before we consider it to have taken off."""
TAKEOFF_VELOCITY_METERS_PER_SECOND = 10
"""The velocity in meters per second that the rocket must reach before we consider it to have taken
off."""

# ---------------- MotorBurn to Coasting ----------------
MAX_VELOCITY_THRESHOLD = 0.96
"""Because motors can behave unpredictably near the end of their burn, we will only say that the
motor has stopped burning if the current velocity is less than a percentage of the max velocity."""

# ----------------- Coasting to Freefall -----------------

# ----------------- Freefall to Landing -----------------
MAX_FREE_FALL_SECONDS = 300.0
"""The maximum amount of time in seconds that the rocket can be in freefall before we consider it to
have landed. This is to prevent the program from running indefinitely if our code never detects the
landing of the rocket. This value accounts for the worst case scenario of the main parachute
deploying at apogee."""

GROUND_ALTITUDE_METERS = 10.0
"""The altitude in meters that the rocket must be under before we consider it to have landed."""
LANDED_ACCELERATION_METERS_PER_SECOND_SQUARED = 35.0
"""The acceleration in m/s^2 that the rocket must be above before we consider it to have landed."""

# ----------------- Landing to Program Stop -----------------

STOP_AFTER_SECONDS = 5
"""The time in seconds after which the program will stop itself."""

# -------------------------------------------------------
# Data Processor Configuration
# -------------------------------------------------------
GRAVITY_METERS_PER_SECOND_SQUARED = 9.798
"""This is the standard gravity on Earth."""

ALTITUDE_DEADBAND_METERS = 0.05
"""The deadband for the altitude in meters. This is used to prevent small fluctuations in altitude
from being considered as a change in altitude."""

VELOCITY_FROM_ALTITUDE_WINDOW_SIZE = 50

# -------------------------------------------------------
# Transmitter Configuration
# -------------------------------------------------------
TRANSMITTER_PIN = 8
"""This is the GPIO pin that the transmitter is connected to."""

DIREWOLF_CONFIG_PATH = Path("/home/pi/direwolf.conf")
"""The path to the Direwolf configuration file."""

MOCK_MESSAGE_PATH = Path("mock_message.txt")
"""The path to the file that holds the message that the mock transmitter sends to the mock receiver.
This should be gitignored."""

TRANSMISSION_DELAY = 10.0
"""The amount of time we wait in between transmissions"""

NO_MESSAGE_TRANSMITTED = "NMT"

# -------------------------------------------------------
# Receiver Configuration
# -------------------------------------------------------
RECEIVER_SERIAL_PORT = "/dev/ttyAMA0"
"""The serial port that the XBee is connected to"""
RECEIVER_BAUD_RATE = 9600

NO_MESSAGE = "NMR"
"""The message that the receiver returns when there is no message to return"""
TRANSMIT_MESSAGE = "TRANSMIT"
"""The message that the transmitter sends to the receiver to start transmitting data"""
STOP_MESSAGE = "STOP"
"""The message that the transmitter sends to the receiver to stop transmitting data"""

# These are in seconds
MOCK_RECEIVER_INITIAL_DELAY = 5.0
MOCK_RECEIVER_RECEIVE_DELAY = 2.0

# -------------------------------------------------------
# Survivability metrics
# -------------------------------------------------------


LANDING_VELOCITY_THRESHOLD = -10.0 #m/s

VERTICAL_ACCELERATION_WEIGHT = 0.25
ANGULAR_RATE_WEIGHT = 1.00
PITCH_WEIGHT = 10.1

INTENSITY_PERCENT_THRESHOLD = 0.20

LANDING_VELOCITY_DEDUCTION = 0.8
