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
    battery_level: float  # battery check
    orientation: tuple[np.float64, np.float64, np.float64]  # of the stemnauts
    time_of_landing: str  # time of landing
    max_velocity: np.float64  # maximum velocity reached
    landing_velocity: np.float64  # velocity on landing
    crew_survivability: np.float64  # survivability, in percent
    landing_coords: tuple[float, float]  # landing coordinates

    def compress_packet(self):
        """
        Creates a representation of the data packet which is highly compressed. Does not include
        the landing coordinates since that is a different field in the direwolf.conf.
        """
        # The `:.1f` means that we are rounding the float to one decimal place.
        return (
            f"t={self.temperature:.1f},"
            f"a={self.apogee:.1f},"
            f"b={self.battery_level:.1f},"
            f"o=(r={self.orientation[0]:.1f},p={self.orientation[1]:.1f},y={self.orientation[2]:.1f}),"
            f"tl={self.time_of_landing},"
            f"mv={self.max_velocity:.1f},"
            f"lv={self.landing_velocity:.1f},"
            f"cs={self.crew_survivability * 100:3.0f}"
        )
