"""Data packet which we will use for transmitting the data via RF and direwolf."""

import msgspec
import numpy as np


class TransmitterDataPacket(msgspec.Struct):
    """
    Represents a packet of data that will be transmitted via RF. This packet is a subset of the
    ProcessorDataPacket, and is used to transmit the most important data points to the ground
    station.
    """

    temperature: np.float64  # Temperature
    apogee: np.float64  # apogee reached
    battery_level_pi: float  # battery pi check
    battery_level_tx: float  # battery tx check
    orientation: tuple[np.float64, np.float64, np.float64]  # of the stemnauts
    time_of_landing: str  # time of landing
    max_velocity: np.float64  # maximum velocity reached
    landing_velocity: np.float64  # velocity on landing
    crew_survivability: np.float64  # survivability, in percent
    landing_coords: tuple[float, float]  # landing coordinates

    def compress_packet(self) -> str:
        """
        Creates a representation of the data packet which is highly compressed. Does not include
        the landing coordinates since that is a different field in the direwolf.conf.
        """
        # The `:.2f` means that we are rounding the float to one decimal place.
        return (
            f"temperature={self.temperature*(9/5)+32:.2f}\xc2\xb0F,"
            f"apogee={self.apogee*3.28084:.2f}ft,"
            f"battery_status=CPU:{self.battery_level_pi:.2f}% | TX:{self.battery_level_tx:.2f}%,"
            f"orientation=(roll={self.orientation[0]:.2f},pitch={self.orientation[1]:.2f},yaw={self.orientation[2]:.2f}),"
            f"time_landing={self.time_of_landing},"
            f"max_vel={self.max_velocity*3.28084:.2f}ft/s,"
            f"landing_vel={self.landing_velocity*3.28084:.2f}ft/s,"
            f"crew_survival={self.crew_survivability * 100:3.1f}%"
        )
