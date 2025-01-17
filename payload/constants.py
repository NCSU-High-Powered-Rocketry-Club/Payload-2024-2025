"""Contains the constants used in the payload module"""

from enum import Enum, StrEnum
from pathlib import Path

# -------------------------------------------------------
# Display Configuration
# -------------------------------------------------------


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

SERIAL_PORT = "COM8"
"""The port that the Arduino is connected to. This is typically the default port where the IMU
connects to the Raspberry Pi."""
BAUD_RATE = 115200
"""The baud rate of the channel"""
PACKET_BYTE_SIZE = 80
"""Size of the data packet being sent from the Arduino in bytes"""

RAW_DATA_PACKET_SAMPLING_RATE = 1 / 1000
"""The frequency at which the IMU sends raw data packets, this is 1kHz"""
EST_DATA_PACKET_SAMPLING_RATE = 1 / 500
"""The frequency at which the IMU sends estimated data packets, this is 500Hz"""

# This is used by all queues to keep things consistent:
MAX_FETCHED_PACKETS = 15
"""This is used to limit how many packets we fetch from the imu at once."""

# Timeouts for get() queue operations:
MAX_GET_TIMEOUT_SECONDS = 100  # seconds
"""The maximum amount of time in seconds to wait for a get operation on the queue."""

# Max bytes to put/get from the queue at once:
BUFFER_SIZE_IN_BYTES = 1000 * 1000 * 20  # 20 Mb
"""The maximum number of bytes to put or get from the queue at once. This is an increase from the
default value of 1Mb, which is too small sometimes for our data packets, e.g. when logging the
entire buffer, which is 5000 packets."""

MAX_QUEUE_SIZE = 100_000
"""The maximum size of the queue that holds the data packets. This is to prevent the queue from"
growing too large and taking up too much memory. This is a very large number, so it should not be
reached in normal operation."""

IMU_TIMEOUT_SECONDS = 3.0
"""The maximum amount of time in seconds the IMU process to do something (e.g. read a packet) before
it is considered to have timed out. This is used to prevent the program from deadlocking if the IMU
stops sending data."""

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


# Formula for converting number of packets to seconds and vice versa:
# If N = total number of packets, T = total time in seconds:
# f = EstimatedDataPacket.frequency + RawDataPacket.frequency = 500 + 1000 = 1500 Hz
# T = N/f => T = N/1500

IDLE_LOG_CAPACITY = 5000  # Using the formula above, this is 3.33 seconds of data
"""The maximum number of data packets to log in the StandbyState and LandedState. This is to prevent
log file sizes from growing too large. Some of our 2023-2024 launches were >300 mb."""
LOG_BUFFER_SIZE = 5000
"""Buffer size if CAPACITY is reached. Once the state changes, this buffer will be logged to make
sure we don't lose data"""

# -------------------------------------------------------
# State Machine Configuration
# -------------------------------------------------------

# Arbitrarily set values for transition between states:

# ----------------- Standby to MotorBurn ----------------
ACCEL_DEADBAND_METERS_PER_SECOND_SQUARED = 0.35
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
LANDED_ACCELERATION_METERS_PER_SECOND_SQUARED = 50.0
"""The acceleration in m/s^2 that the rocket must be above before we consider it to have landed."""

# -------------------------------------------------------
# Data Processor Configuration
# -------------------------------------------------------
GRAVITY_METERS_PER_SECOND_SQUARED = 9.798
"""This is the standard gravity on Earth."""
