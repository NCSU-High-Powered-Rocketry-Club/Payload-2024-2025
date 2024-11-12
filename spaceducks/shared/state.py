# Data storage and serialization
import msgspec
from typing import Union


class Message(msgspec.Struct, array_like=True, tag=True):
    message: str


class SensorState(msgspec.Struct, array_like=True, tag=True):
    altitude: float = 0.0
    temperature: float = 0.0
    orientation: tuple[float, float, float] = (0.0, 0.0, 0.0)

    # For measuring forces on STEMnauts
    acceleration: tuple[float, float, float] = (0.0, 0.0, 0.0)
    # For detecting launch
    linear_accel: tuple[float, float, float] = (0.0, 0.0, 0.0)

    def __str__(self) -> str:
        return (
            f"altitude: {self.altitude:5.2f}, "
            f"temperature: {self.temperature:5.2f},"
            f"orientation: {[f'{val:5.2f}' for val in self.orientation ]}, "
            f"acceleration: {[f'{val:5.2f}' for val in self.acceleration ]}, "
            f"linear_acceleration: {[f'{val:5.2f}' for val in self.linear_accel ]}"
        )


class FlightStats(msgspec.Struct, array_like=True, tag=True):
    current_alt: float = 0.0
    max_acceleration: float = 0.0
    max_temperature: float = 0.0
    max_altitude: float = 0.0
    survivability_rating: float = 0.0

    def __str__(self) -> str:
        """This string will be used for text-to-speech"""

        return (
            f"Maximum Acceleration: {self.max_acceleration}. "
            f"Maximum Temperature: {self.max_temperature}. "
            f"Maximum Altitude: {self.max_altitude}. "
            f"STEMnaut Survivability: {self.survivability_rating * 100.0} percent."
        )


MESSAGE_TYPES = Union[Message, SensorState, FlightStats]
