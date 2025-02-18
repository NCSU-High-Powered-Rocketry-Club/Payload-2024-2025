"""Module for processing IMU data on a higher level."""

import ahrs
import numpy as np
from scipy.spatial.transform import Rotation as R

from payload.constants import (
    ACCEL_DEADBAND_METERS_PER_SECOND_SQUARED,
    ALTITUDE_DEADBAND_METERS,
    GRAVITY_METERS_PER_SECOND_SQUARED,
)
from payload.data_handling.packets.imu_data_packet import IMUDataPacket
from payload.data_handling.packets.processor_data_packet import ProcessorDataPacket
from payload.utils import convert_milliseconds_to_seconds, deadband


class DataProcessor:
    """
    Performs high level calculations on the data packets received from the IMU. Includes
    calculating the rolling averages of acceleration, maximum altitude so far, etc., from the set of
    data points.
    """

    __slots__ = (
        "_current_altitude",
        "_data_packet",
        "_filter",
        "_initial_altitude",
        "_last_data_packet",
        "_last_velocity_calculation_packet",
        "_max_altitude",
        "_previous_vertical_velocity",
        "_time_difference",
        "_vertical_velocity",
    )

    def __init__(self):
        """
        Initializes the DataProcessor object. It processes data points to calculate various
        things we need such as the maximum altitude, current altitude, velocity, etc. All numbers
        in this class are handled with numpy.

        This class has properties for the maximum altitude, current altitude, velocity, and
        maximum velocity of the rocket.
        """
        self._max_altitude: np.float64 = np.float64(0.0)
        self._initial_altitude: np.float64 | None = None
        self._current_altitude: np.float64 = np.float64(0.0)
        self._last_data_packet: IMUDataPacket | None = None
        self._data_packet: IMUDataPacket | None = None
        self._time_difference: np.float64 = np.float64(0.0)
        self._previous_vertical_velocity: np.float64 = np.float64(0.0)
        self._vertical_velocity: np.float64 = np.float64(0.0)
        self._last_velocity_calculation_packet: IMUDataPacket | None = None
        self._filter = ahrs.filters.Davenport(magnetic_dip=62, weights=[3,1])

    @property
    def max_altitude(self) -> float:
        """
        Returns the highest altitude (zeroed out) attained by the rocket for the entire flight
        so far, in meters.
        """
        return float(self._max_altitude)

    @property
    def current_altitude(self) -> float:
        """
        Returns the altitude of the rocket (calibrated from initial altitude) from the data points,
        in meters.
        """
        return float(self._current_altitude)

    @property
    def vertical_velocity(self) -> float:
        """
        Returns the vertical velocity of the rocket in m/s. Calculated by differentiating the
        altitude.
        """
        return float(self._vertical_velocity)

    @property
    def max_vertical_velocity(self) -> float:
        """
        Returns the highest vertical velocity attained by the rocket for the entire flight
        so far, in meters per second.
        """
        return float(self._max_velocity)

    @property
    def current_timestamp(self) -> int:
        """The timestamp of the last data packet in milliseconds."""
        try:
            return self._last_data_packet.timestamp
        except AttributeError:  # If we don't have a last data packet
            return 0


    def update(self, data_packet: IMUDataPacket) -> None:
        """
        Updates the data points to process. This will recompute all calculations for altitude,
        velocity, acceleration, and crew survivability.
        :param data_packet: An IMUDataPacket object to process
        """
        # If we don't have a data packet, return early
        if not data_packet:
            return

        self._data_packet = data_packet

        # If we don't have a last data point, we can't calculate the time differences needed
        # for velocity calculation:
        if self._last_data_packet is None:
            self._first_update()

        self._time_difference = np.float64(
            convert_milliseconds_to_seconds(
                self._data_packet.timestamp - self._last_data_packet.timestamp
            )
        )

        self._vertical_velocity = self._calculate_velocity_from_altitude()

        self._current_altitude = self._calculate_current_altitude()
        self._max_altitude = max(self._current_altitude, self._max_altitude)
        self._max_velocity = max(self._vertical_velocity, self._max_velocity)

        # Store the last data point for the next update
        self._last_data_packet = data_packet

    def get_processor_data_packet(self) -> ProcessorDataPacket:
        """
        Processes the data points and returns a ProcessedDataPacket object.

        :return: A ProcessedDataPacket object.
        """
        return ProcessorDataPacket(
            current_altitude=self._current_altitude,
            vertical_velocity=self._vertical_velocity,
            time_since_last_data_packet=self._time_difference,
            maximum_altitude=np.float64(self.max_altitude),
            maximum_velocity=np.float64(self.max_vertical_velocity),
            # TODO: Implement these
            crew_survivability=0.0,
            landing_velocity=0.0,
        )

    def _first_update(self) -> None:
        """
        Sets up the initial values for the data processor. This includes setting the initial
        altitude. This should
        only be called once, when the first data packets are passed in.
        """
        # Setting last data packet as this packet makes it so that the time diff
        # automatically becomes 0, and the velocity becomes 0
        self._last_data_packet = self._data_packet

        # This is us getting the rocket's initial altitude from the first data packets
        self._initial_altitude = self._data_packet.pressureAlt

    def _calculate_current_altitude(self) -> np.float64:
        """
        Calculates the current altitude, by zeroing out the initial altitude.
        :return: the current altitude of the rocket
        """
        # Get the pressure altitude from the data points and zero out the initial altitude
        return self._data_packet.pressureAlt - self._initial_altitude

    def _calculate_velocity_from_altitude(self) -> np.float64:
        """
        Calculates the velocity of the rocket based by differentiating the altitude.
        :return: The velocity of the rocket in m/s.
        """
        # If we don't have a last velocity timestamp, we can't calculate the velocity
        if self._last_velocity_calculation_packet is None:
            self._last_velocity_calculation_packet = self._data_packet
            return np.float64(0.0)

        # If we have a different altitude, we can calculate the velocity
        if (
            deadband(
                self._data_packet.pressureAlt - self._last_velocity_calculation_packet.pressureAlt,
                ALTITUDE_DEADBAND_METERS,
            )
            != 0
        ):
            # Calculate the velocity using the altitude difference and the time difference
            velocity = np.float64(
                (self._data_packet.pressureAlt - self._last_velocity_calculation_packet.pressureAlt)
                / convert_milliseconds_to_seconds(
                    self._data_packet.timestamp - self._last_velocity_calculation_packet.timestamp
                )
            )
            # Update the last velocity packet for the next update
            self._last_velocity_calculation_packet = self._data_packet
        else:
            # If the altitude hasn't changed, we use the last velocity
            velocity = self._vertical_velocity
        return velocity

    def calculate_orientation(self) -> tuple:
        """
        Calculates the orientation of the rocket using the magnetometer and accelerometer.
        :return: a tuple of roll, pitch, and yaw.
        """
        acc = np.array(
            [
                self._data_packet.estCompensatedAccelX,
                self._data_packet.estCompensatedAccelY,
                self._data_packet.estCompensatedAccelZ,
            ]
        )

        mag = np.array(
            [
                self._data_packet.magneticFieldX,
                self._data_packet.magneticFieldY,
                self._data_packet.magneticFieldZ,
            ]
        )

        if any(mag_data_point is None for mag_data_point in mag):
            return None

        orientation = self._filter.estimate(acc=acc, mag=mag)
        return tuple(R.from_quat(orientation, scalar_first=True).as_euler("xyz", degrees=True))
