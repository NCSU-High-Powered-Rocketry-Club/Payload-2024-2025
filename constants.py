"""Contains the constants used in the payload"""

from enum import Enum
from pathlib import Path

# -------------------------------------------------------
# IMU Configuration
# -------------------------------------------------------


# The maximum size of the data queue for the packets, so we don't run into memory issues
MAX_QUEUE_SIZE = 100000

# -------------------------------------------------------
# Data Processing Configuration
# -------------------------------------------------------


# -------------------------------------------------------
# Logging Configuration
# -------------------------------------------------------

# The path of the folder to hold the log files in
LOGS_PATH = Path("logs")
TEST_LOGS_PATH = Path("test_logs")

# The signal to stop the logging process, this will be put in the queue to stop the process
# see stop() and _logging_loop() for more details.
STOP_SIGNAL = "STOP"

# Don't log more than x packets for StandbyState and LandedState
IDLE_LOG_CAPACITY = 5000  # This is equal to (x/2 + x = 3x/2 = 5000 => x = 3333 = 3.33 secs of data)
# Buffer size if CAPACITY is reached. Once the state changes, this buffer will be logged to make
# sure we don't lose data
LOG_BUFFER_SIZE = 5000

# -------------------------------------------------------
# State Machine Configuration
# -------------------------------------------------------

# Arbitrarily set values for transition between states:

# Standby to MotorBurn:
ACCELERATION_NOISE_THRESHOLD = 0.35  # m/s^2

# We will take the magnitude of acceleration for this
TAKEOFF_HEIGHT = 10  # meters
TAKEOFF_VELOCITY = 10  # m/s

# MotorBurn to Coasting:

# We will only say that the motor has stopped burning if the
# current velocity <= Max velocity * (1 - MAX_VELOCITY_THRESHOLD)
MAX_VELOCITY_THRESHOLD = 0.03
# seconds (this is slightly higher than the actual burn time, which is 2.2 seconds)
MOTOR_BURN_TIME = 2.6

# Free fall to Landing:

# Consider the rocket to have landed if it is within 15 meters of the launch site height.
GROUND_ALTITUDE = 15.0  # meters
