"""Module for describing the data packet created for the IMU"""

import msgspec


class IMUDataPacket(msgspec.Struct):
    """
    This class represents all the data we receive from the IMU.
    """

    timestamp: int  # In milliseconds
    voltage: float | None = None
    # temperature in celsius
    ambientTemperature: float | None = None
    # pressure in mbar
    ambientPressure: float | None = None
    # estCompensatedAccel units are in m/s^2, including gravity
    estCompensatedAccelX: float | None = None
    estCompensatedAccelY: float | None = None
    estCompensatedAccelZ: float | None = None  # this will be ~-9.81 m/s^2 when the IMU is at rest
    # angular rate units in radians per second
    estAngularRateX: float | None = None
    estAngularRateY: float | None = None
    estAngularRateZ: float | None = None
    # magnetic field
    magneticFieldX: float | None = None
    magneticFieldY: float | None = None
    magneticFieldZ: float | None = None
    estOrientQuaternionW: float | None = None
    estOrientQuaternionX: float | None = None
    estOrientQuaternionY: float | None = None
    estOrientQuaternionZ: float | None = None
    gpsLatitude: float | None = None
    gpsLongitude: float | None = None
    gpsAltitude: float | None = None
