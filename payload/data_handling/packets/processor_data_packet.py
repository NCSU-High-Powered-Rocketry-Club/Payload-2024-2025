"""Module for describing the data packet for the processed IMU data"""

import msgspec
import numpy as np


class ProcessorDataPacket(msgspec.Struct):
    """
    Represents a packet of processed data from the IMU. All of these fields are the processed
    values of the estimated data.
    """

    current_altitude: np.float64  # This is the zeroed-out altitude of the rocket.
    # This is the velocity of the rocket, in the upward axis (whichever way is up)
    vertical_velocity: np.float64
    velocity_moving_average: np.float64
    # dt is the time difference between the current and previous data point
    time_since_last_data_packet: np.float64

    # The following data points are for the transceiver

    # maximum altitude reached in meters, zeroed-out
    maximum_altitude: np.float64
    # maximum velocity reached, in meters per second
    maximum_velocity: np.float64
    # velocity on landing
    landing_velocity: np.float64
    # survivability, in percent
    crew_survivability: np.float64

    def __str__(self):
        """
        Creates a string representation of the data packet with each field separated by a comma.
        """
        return (
            f"{self.current_altitude},"
            f"{self.vertical_velocity},"
            f"{self.velocity_moving_average},"
            f"{self.time_since_last_data_packet},"
            f"{self.maximum_altitude},"
            f"{self.maximum_velocity},"
            f"{self.landing_velocity},"
            f"{self.crew_survivability}"
        )
