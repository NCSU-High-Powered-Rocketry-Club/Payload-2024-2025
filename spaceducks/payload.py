from enum import Enum, auto
import time
import sys
import threading
import logging
import math


from .shared.xbee_interface import XbeeInterface
from .radio_interface import RFInterface
from .shared.state import SensorState, FlightStats, MESSAGE_TYPES, Message
from .flight_states import BaseState, StandbyState, LandedState, RecoverState
from .sensors import SensorReader


class LaunchState(Enum):
    STANDBY = auto()
    ARMED = auto()
    LANDED = auto()
    RECOVER = auto()


class PayloadSystem:
    # Name of the log file
    LOG_FILENAME = "payload.log"

    # Interval (seconds) to log data at
    LOG_INTERVAL = 0.1

    # Interval (seconds) to transmit data at
    TX_INTERVAL = 0.5

    # Time to wait between reading sensors (seconds)
    SENSOR_WAIT_TIME = 0.05

    # Sea level pressure used to calibrate altimeter (hPa)
    SEA_LEVEL_PRESSURE = 1013.25  # this is the default from adafruit docs

    def __init__(self, callsign: str, xbee_port: str, feather_port: str):
        # Initialize the logger
        self.setup_logger()
        logging.debug("Initializing payload...")

        # Initialize payload state machine
        self.running = True
        self.state: BaseState = StandbyState()

        self.last_log_time = time.time()
        self.last_tx_time = time.time()

        self.data = SensorState()
        self.stats = FlightStats()


        self.xbee = XbeeInterface(xbee_port, self.receive_message)
        self.xbee.start()

        self.sensor_reader = SensorReader(self, feather_port)
        self.sensor_reader.start()


        if callsign != "NOTRANSMIT":
            self.radio = RFInterface(callsign, None)
        else:
            self.radio = None

        self.log_thread = threading.Thread(target=self.log_data)


        logging.debug("Starting data logging thread...")
        self.log_thread.start()

        logging.debug("Payload initialized.")
        #self.xbee.send_data(Message("Howdy!"))

    def setup_logger(self):
        """Set up the logger to log to file and stderr"""

        logging.basicConfig(
            handlers=[logging.FileHandler(self.LOG_FILENAME), logging.StreamHandler()],
            level=logging.DEBUG,
            format="[%(asctime)s] %(message)s",
            datefmt="%m/%d/%Y %I:%M:%S %p",
        )

    def log_data(self):
        """Threaded function to read sensors continuously in the background"""

        while self.running:
            # using epsilon here because this can't be exactly zero
            # (because then it might not switch threads at all)

            time.sleep(sys.float_info.epsilon)


            # If enough time has passed, let's log this data
            if (time.time() - self.last_log_time) >= self.LOG_INTERVAL:
                logging.info(str(self.data))
                self.last_log_time = time.time()

            # and if enough time has passed, transmit it to the ground station
            if (time.time() - self.last_tx_time) >= self.TX_INTERVAL:
                #self.xbee.send_data(self.data)
                self.last_tx_time = time.time()

    def update_stats(self):
        """Update flight statistics (max/min/etc) from our sensor state to transmit later"""

        if self.data.altitude > self.stats.max_altitude:
            self.stats.max_altitude = self.data.altitude

        if self.data.temperature > self.stats.max_temperature:
            self.stats.max_temperature = self.data.temperature

        # Include gravity since we're getting overall accel
        magnitude = math.sqrt(sum(axis**2 for axis in self.data.accel))
        if magnitude > self.stats.max_acceleration:
            self.stats.max_acceleration = magnitude

    def update(self):
        """Update the main payload state machine"""

        current_state = self.state

        current_state.update(self)

        # Ensure the main thread also doesn't hog thread time
        time.sleep(sys.float_info.epsilon)

    def shutdown(self):
        self.running = False

        # Stop our xbee and sensor reader
        self.xbee.stop()
        self.sensor_reader.stop()

        # Wait for the sensor thread to finish
        self.log_thread.join()

    def receive_message(self, data: MESSAGE_TYPES):
        if type(data) is Message:
            if data.message == "!transmitnow":
                self.state = LandedState()

            elif data.message == "!recover":
                self.state = RecoverState()
