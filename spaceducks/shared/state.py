# Data storage and serialization
import msgspec
from typing import Union


class Message(msgspec.Struct, array_like=True, tag=True):
    message: str


class SensorState(msgspec.Struct, array_like=True, tag=True):
    altitude: float = 0.0
    battery_voltage: float = 0.0
    temperature: float = 0.0

    gyro: tuple[float, float, float] = (0, 0, 0)
    accel: tuple[float, float, float] = (0, 0, 0)
    linear_accel: tuple[float, float, float] = (0, 0, 0)
    quat: tuple[float, float, float, float] = (0, 0, 0, 1)
    gps: str = ""

    def __str__(self) -> str:
        return (
            f"altitude: {self.altitude:5.2f}, "
            f"temperature: {self.temperature:5.2f},"
            f"gyro: {[f'{val:5.2f}' for val in self.gyro ]}, "
            f"acceleration: {[f'{val:5.2f}' for val in self.accel ]}, "
            f"linear_accel: {[f'{val:5.2f}' for val in self.linear_accel ]}, "
            f"quaternion: {[f'{val:5.2f}' for val in self.quat ]}, "
            f"gps: {self.gps}"
        )


class FlightStats(msgspec.Struct, array_like=True, tag=True):
    takeoff_alt: float = 0.0
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
