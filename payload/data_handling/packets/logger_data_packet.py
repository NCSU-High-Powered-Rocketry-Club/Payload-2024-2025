"""Module for describing the data packet for the logger to log"""

from typing import TypedDict


class LoggerDataPacket(TypedDict, total=False):  # total=False means all fields are NotRequired
    """
    Represents a collection of all data that the logger can log in a line. Not every field will be
    filled in every packet. If you want properties from another packet to be logged, you have to
    make sure they have the exact same name.
    """

    # Context Data Packet Fields
    state_name: str
    transmitted_message: str
    received_message: str
    update_timestamp_ns: int

    # IMU Data Packet Fields
    timestamp: float | None
    voltage_pi: float | None
    voltage_tx: float | None
    ambientTemperature: float | None
    ambientPressure: float | None
    pressureAlt: float | None
    estCompensatedAccelX: float | None
    estCompensatedAccelY: float | None
    estCompensatedAccelZ: float | None
    estAngularRateX: float | None
    estAngularRateY: float | None
    estAngularRateZ: float | None
    magneticFieldX: float | None
    magneticFieldY: float | None
    magneticFieldZ: float | None
    estOrientQuaternionW: float | None
    estOrientQuaternionX: float | None
    estOrientQuaternionY: float | None
    estOrientQuaternionZ: float | None
    gpsLatitude: float | None
    gpsLongitude: float | None
    gpsAltitude: float | None
    # statusFlag: float | None

    # Processed Data Packet Fields
    current_altitude: float | None
    vertical_velocity: float | None
    velocity_moving_average: float | None
    maximum_altitude: float | None
    maximum_velocity: float | None
    landing_velocity: float | None
    crew_survivability: float | None
