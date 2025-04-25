"""Data packet which we will use for transmitting the data via RF and direwolf."""

import msgspec

from payload.constants import TransmitterValueRanges


class TransmitterDataPacket(msgspec.Struct):
    """
    Represents a packet of data that will be transmitted via RF. This packet is a subset of the
    ProcessorDataPacket, and is used to transmit the most important data points to the ground
    station.
    """

    temperature: float  # Temperature
    apogee: float  # apogee reached
    battery_level_pi: float  # battery pi check
    battery_level_tx: float  # battery tx check
    orientation: tuple[float, float, float]  # of the stemnauts
    time_of_landing: str  # time of landing
    max_velocity: float  # maximum velocity reached
    landing_velocity: float  # velocity on landing
    crew_survivability: float  # survivability, in percent
    landing_coords: tuple[float, float]  # landing coordinates

    def compress_packet(self) -> str:
        """
        Creates a representation of the data packet which is highly compressed. Does not include
        the landing coordinates since that is a different field in the direwolf.conf.
        """
        # The `:.2f` means that we are rounding the float to one decimal place.
        return (
            f"temperature={self.temperature * (9 / 5) + 32:.2f}\xc2\xb0F,"  # that's the degree symbol
            f"apogee={self.apogee * 3.28084:.2f}ft,"
            f"battery_status=CPU:{self.battery_level_pi:.2f}% | TX:{self.battery_level_tx:.2f}%,"
            f"orientation=(roll={self.orientation[0]:.2f},pitch={self.orientation[1]:.2f},yaw={self.orientation[2]:.2f}),"
            f"time_landing={self.time_of_landing},"
            f"max_vel={self.max_velocity * 3.28084:.2f}ft/s,"
            f"landing_vel={self.landing_velocity * 3.28084:.2f}ft/s,"
            f"crew_survival={self.crew_survivability * 100:3.1f}%"
        )

    def validate_data_points(self) -> None:
        """
        Validates the data points in the packet. This ensures that all the data is within a range,
        and if not, it will clamp the values to the range.
        """

        temp_range = TransmitterValueRanges.TEMPERATURE_RANGE_CELSIUS
        if self.temperature < temp_range[0]:
            self.temperature = temp_range[0]
        elif self.temperature > temp_range[1]:
            self.temperature = temp_range[1]
        
        max_velocity_range = TransmitterValueRanges.MAX_VELOCITY_RANGE_METERS_PER_SECOND
        if self.max_velocity < max_velocity_range[0]:
            self.max_velocity = max_velocity_range[0]
        elif self.max_velocity > max_velocity_range[1]:
            self.max_velocity = max_velocity_range[1]

        landing_velocity_range = TransmitterValueRanges.LANDING_VELOCITY_RANGE_METERS_PER_SECOND
        if self.landing_velocity < landing_velocity_range[0]:
            self.landing_velocity = landing_velocity_range[0]
        elif self.landing_velocity > landing_velocity_range[1]:
            self.landing_velocity = landing_velocity_range[1]

