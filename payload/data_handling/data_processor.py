"""Module for processing IMU data on a higher level."""

import ahrs
import numpy as np
from scipy.spatial.transform import Rotation as R

from payload.constants import (
    ALTITUDE_DEADBAND_METERS,
    ANGULAR_RATE_WEIGHT,
    INTENSITY_PERCENT_THRESHOLD,
    LANDING_VELOCITY_DEDUCTION,
    LANDING_VELOCITY_THRESHOLD,
    VELOCITY_FROM_ALTITUDE_WINDOW_SIZE,
    VERTICAL_ACCELERATION_WEIGHT,
    SURVIVABILITY_SCALE,
    BATTERY_ROLLING_AVG_SAMPLE_SIZE
)

from collections import deque
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
        "_crew_survivability",
        "_current_altitude",
        "_data_packet",
        "_filter",
        "_initial_altitude",
        "_landing_velocity",
        "_last_data_packet",
        "_last_velocity_calculation_packet",
        "_max_altitude",
        "_max_velocity",
        "_previous_vertical_velocity",
        "_time_difference",
        "_velocity_rolling_average",
        "_vertical_velocity",
        "calculating_crew_survivability",
        "_battery_rolling_average",
        "_battery",
        "_euler_orientation"
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
        self._max_velocity: np.float64 = np.float64(0.0)
        self._initial_altitude: np.float64 | None = None
        self._current_altitude: np.float64 = np.float64(0.0)
        self._last_data_packet: IMUDataPacket | None = None
        self._data_packet: IMUDataPacket | None = None
        self._time_difference: np.float64 = np.float64(0.0)
        self._crew_survivability: np.float64 = np.float64(1.0)
        self.calculating_crew_survivability = False
        self._previous_vertical_velocity: np.float64 = np.float64(0.0)
        self._vertical_velocity: np.float64 = np.float64(0.0)
        self._last_velocity_calculation_packet: IMUDataPacket | None = None
        self._velocity_rolling_average: list[np.float64] = []
        self._landing_velocity: np.float64 = np.float64(0.0)
        self._filter = ahrs.filters.Davenport(magnetic_dip=62, weights=[3,1])
        self._battery_rolling_average = [deque(maxlen=BATTERY_ROLLING_AVG_SAMPLE_SIZE), deque(maxlen=BATTERY_ROLLING_AVG_SAMPLE_SIZE)]
        self._battery = [100.0, 100.0]  # pi_battery, tx_battery
        self._euler_orientation: tuple = (0,0,0)

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

    @property
    def velocity_moving_average(self) -> float:
        """Average of the last 10 previous velocity calculations for use in a moving average."""
        if self._velocity_rolling_average:
            return float(np.mean(self._velocity_rolling_average))
        return self.vertical_velocity

    @property
    def battery_moving_average(self) -> tuple[float, float]:
        """"""
        return self._battery[0], self._battery[1]

    @property
    def euler_orientation(self) -> tuple:
        return self._euler_orientation

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
            self._data_packet.timestamp - self._last_data_packet.timestamp
        )

        self._vertical_velocity = self._calculate_velocity_from_altitude()

        self._current_altitude = self._calculate_current_altitude()
        self._max_altitude = max(self._current_altitude, self._max_altitude)
        self._max_velocity = max(self.velocity_moving_average, self._max_velocity)
        self._euler_orientation = self.calculate_orientation()

        self._battery = self._calculate_battery_rolling_average()

        if self.calculating_crew_survivability:
            self._crew_survivability = self._calculate_crew_survivability()

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
            velocity_moving_average=self.velocity_moving_average,
            time_since_last_data_packet=self._time_difference,
            maximum_altitude=np.float64(self.max_altitude),
            maximum_velocity=np.float64(self.max_vertical_velocity),
            crew_survivability=self._crew_survivability,
            landing_velocity=self._landing_velocity,
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
            # Calculate the velocity using the altitude difference and the time difference.
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

        self._velocity_rolling_average.append(velocity)

        if len(self._velocity_rolling_average) > VELOCITY_FROM_ALTITUDE_WINDOW_SIZE:
            self._velocity_rolling_average.pop(0)
        return sum(self._velocity_rolling_average) / len(self._velocity_rolling_average)

    def calculate_landing_velocity(self):
        """Called upon landing state detection and gathers the last velocity reading"""

        # Uses the first half of the moving average to find landing velocity upon landing detection
        landing_velocity_size = VELOCITY_FROM_ALTITUDE_WINDOW_SIZE // 2
        self._landing_velocity = (
            sum(self._velocity_rolling_average[:landing_velocity_size]) / landing_velocity_size
        )

    def _calculate_battery_rolling_average(self) -> tuple[float, float]:
        """Calculates battery RA"""
        self._battery_rolling_average[0].append(self._data_packet.voltage_pi)
        self._battery_rolling_average[1].append(self._data_packet.voltage_tx)

        pi_battery = sum(self._battery_rolling_average[0]) / len(self._battery_rolling_average[0])
        tx_battery = sum(self._battery_rolling_average[1]) / len(self._battery_rolling_average[1])

        return pi_battery, tx_battery

    def _calculate_crew_survivability(self) -> np.float64:
        """
        Calculates the probability that our crew of STEMnauts is alive depending on
        conditions during the flight. The surviabililty is only dependent on events after
        motor burn out, and the velocity with which we hit the ground.
        :return: A float with the percent chance that our crew is still alive
        """

        updated_survival_chance = self._crew_survivability

        # These constants are optimized so that no constant alone largely affects the chance
        # of survival
        intensity_percent = (
            np.abs(self._data_packet.estCompensatedAccelZ) * VERTICAL_ACCELERATION_WEIGHT
            + np.abs(self._data_packet.estAngularRateY) * ANGULAR_RATE_WEIGHT
        ) / SURVIVABILITY_SCALE

        if intensity_percent > INTENSITY_PERCENT_THRESHOLD:
            # Since the code is updated so frequently, intensity percent is divided by large
            # factor to not instantly remove all survival chance
            updated_survival_chance = self._crew_survivability * (1.0 - intensity_percent / 100)

        return updated_survival_chance

    def finalize_crew_survivability(self):
        """
        Deducts a percentage of survival chance based on the ground hit velocity
        """
        if self._landing_velocity < LANDING_VELOCITY_THRESHOLD:
            self._crew_survivability *= LANDING_VELOCITY_DEDUCTION

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
