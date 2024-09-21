from enum import Enum, auto
import time
import sys
import threading
import logging
import math

# Hardware libraries
import board
from adafruit_bno055 import BNO055_I2C
from adafruit_bmp280 import Adafruit_BMP280_I2C

# Data storage and serialization
import msgspec


class LaunchState(Enum):
    STANDBY = auto()
    ARMED = auto()
    LANDED = auto()
    RECOVER = auto()


class SensorState(msgspec.Struct):
    altitude: float = 0.0
    temperature: float = 0.0
    orientation: tuple[float, float, float] = (0.0, 0.0, 0.0)

    # For measuring forces on STEMnauts
    acceleration: tuple[float, float, float] = (0.0, 0.0, 0.0)
    # For detecting launch
    linear_accel: tuple[float, float, float] = (0.0, 0.0, 0.0)


class FlightStats(msgspec.Struct):
    max_acceleration: float = 0.0
    max_temperature: float = 0.0
    max_altitude: float = 0.0


class PayloadSystem:
    # Name of the log file
    LOG_FILENAME = "payload.log"

    # Interval (seconds) to log data at
    LOG_INTERVAL = 0.5

    # Arm the payload if we detect at least this much acceleration
    MINIMUM_ARM_ACCEL = 3  # m/s^2

    # The maximum rest acceleration and altitude to detect if we've landed
    MAXIMUM_REST_ACCEL = 0.4  # m/s^2
    MAXIMUM_REST_ALT = 2  # meters above initial takeoff altitude to consider

    # Time to wait between reading sensors (seconds)
    SENSOR_WAIT_TIME = 0.0

    # Sea level pressure used to calibrate altimeter (hPa)
    SEA_LEVEL_PRESSURE = 1013.25  # this is the default from adafruit docs

    def __init__(self):
        # Initialize the logger
        self.setup_logger()
        logging.debug("Initializing payload...")

        # Initialize payload state
        self.state = LaunchState.STANDBY
        self.init_time = time.time()
        self.running = True
        self.data = SensorState()
        self.stats = FlightStats()
        self.last_log_time = time.time()

        # Initialize our sensors and store them.
        self.i2c_bus = board.I2C()
        self.imu = BNO055_I2C(self.i2c_bus)

        self.altimeter = Adafruit_BMP280_I2C(self.i2c_bus)
        self.altimeter.sea_level_pressure = self.SEA_LEVEL_PRESSURE

        self.sensor_thread = threading.Thread(target=self.read_sensors)

        logging.debug("Starting sensor read thread...")
        self.sensor_thread.start()

    def setup_logger(self):
        logging.basicConfig(
            handlers=[logging.FileHandler(self.LOG_FILENAME), logging.StreamHandler()],
            level=logging.DEBUG,
            format="[%(asctime)s] %(message)s",
            datefmt="%m/%d/%Y %I:%M:%S %p",
        )

    def read_sensors(self):
        while self.running:
            # Read altitude and temperature
            self.data.altitude = self.altimeter.altitude
            self.data.temperature = self.altimeter.temperature

            # Read orientation as an euler angle
            self.data.orientation = self.imu.euler

            # Read acceleration
            self.data.acceleration = self.imu.acceleration
            self.data.linear_accel = self.imu.linear_acceleration

            self.update_stats()

            # If enough time has passed, let's log this data
            if (time.time() - self.last_log_time) >= self.LOG_INTERVAL:
                logging.info(str(self.data))
                self.last_log_time = time.time()

            # using epsilon here because this can't be exactly zero
            # (because then it might not switch threads at all)
            time.sleep(sys.float_info.epsilon + self.SENSOR_WAIT_TIME)

    def update_stats(self):
        if self.data.altitude > self.stats.max_altitude:
            self.stats.max_altitude = self.data.altitude

        if self.data.temperature > self.stats.max_temperature:
            self.stats.max_temperature = self.data.temperature

        # Include gravity since we're getting overall accel
        magnitude = math.sqrt(sum(axis**2 for axis in self.data.acceleration))
        if magnitude > self.stats.max_acceleration:
            self.stats.max_acceleration = magnitude

    def update(self):
        current_state = self.state

        ### Standby state
        if current_state is LaunchState.STANDBY:
            # Update the current altitude at takeoff
            self.takeoff_altitude = self.data.altitude

            # If we detect takeoff, then we switch to armed mode
            if self.detect_takeoff():
                logging.info("Takeoff detected, switching to arm state.")
                self.state = LaunchState.ARMED

        ### Armed state
        elif current_state is LaunchState.ARMED:
            if self.detect_landing():
                logging.info("Landing detected, switching to land state.")
                self.state = LaunchState.LANDED

        ### Landed state
        elif current_state is LaunchState.LANDED:
            # TODO: Send our messages over the radio
            pass

        ### Recovery
        else:
            # Should be in recover state, shutdown
            self.shutdown()

        # Ensure the main thread also doesn't hog thread time
        time.sleep(sys.float_info.epsilon)

    def detect_takeoff(self) -> bool:
        # Simply calculate the magnitude
        # (we could use a numpy function or mathutils Vector but it's probably overkill for now)
        magnitude = math.sqrt(sum(axis**2 for axis in self.data.linear_accel))
        return magnitude >= self.MINIMUM_ARM_ACCEL

    def detect_landing(self) -> bool:
        # Detect if we've landed based on both the IMU and measured altitude
        magnitude = math.sqrt(sum(axis**2 for axis in self.data.linear_accel))
        max_alt = self.takeoff_altitude + self.MAXIMUM_REST_ALT

        return magnitude <= self.MAXIMUM_REST_ACCEL and self.data.altitude <= max_alt

    def shutdown(self):
        self.running = False

        # Wait for the sensor thread to finish
        self.sensor_thread.join()
