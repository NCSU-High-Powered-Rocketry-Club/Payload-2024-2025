"""Module for processing IMU data on a higher level."""

import numpy as np
from scipy.spatial.transform import Rotation as R

from payload.constants import (
    ACCEL_DEADBAND_METERS_PER_SECOND_SQUARED,
    ALTITUDE_DEADBAND_METERS,
    ANGULAR_RATE_WEIGHT,
    GRAVITY_METERS_PER_SECOND_SQUARED,
    INTENSITY_PERCENT_THRESHOLD,
    LANDING_VELOCITY_DEDUCTION,
    LANDING_VELOCITY_THRESHOLD,
    PITCH_WEIGHT,
    VELOCITY_FROM_ALTITUDE_WINDOW_SIZE,
    VERTICAL_ACCELERATION_WEIGHT,
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
        "_crew_survivability",
        "_current_altitude",
        "_current_orientation_quaternions",
        "_data_packet",
        "_initial_altitude",
        "_landing_velocity",
        "_last_data_packet",
        "_last_velocity_calculation_packet",
        "_max_altitude",
        "_max_velocity_from_acceleration",
        "_pitch",
        "_previous_vertical_velocity",
        "_roll",
        "_rotated_acceleration",
        "_time_difference",
        "_velocity_from_acceleration",
        "_velocity_from_altitude",
        "_velocity_rolling_average",
        "_yaw",
        "calculating_crew_survivability",
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
        self._velocity_from_acceleration: np.float64 = np.float64(0.0)
        self._max_velocity_from_acceleration: np.float64 = np.float64(0.0)
        self._initial_altitude: np.float64 | None = None
        self._current_altitude: np.float64 = np.float64(0.0)
        self._last_data_packet: IMUDataPacket | None = None
        self._current_orientation_quaternions: R | None = None
        self._rotated_acceleration: np.float64 = np.float64(0.0)
        self._data_packet: IMUDataPacket | None = None
        self._time_difference: np.float64 = np.float64(0.0)
        self._crew_survivability: np.float64 = np.float64(1.0)
        self._roll: np.float64 = np.float64(0.0)
        self._pitch: np.float64 = np.float64(0.0)
        self._yaw: np.float64 = np.float64(0.0)
        self.calculating_crew_survivability = False
        self._previous_vertical_velocity: np.float64 = np.float64(0.0)
        self._velocity_from_altitude: np.float64 = np.float64(0.0)
        self._last_velocity_calculation_packet: IMUDataPacket | None = None
        self._velocity_rolling_average: list[np.float64] = []
        self._landing_velocity: np.float64 = np.float64(0.0)

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
    def velocity_from_altitude(self) -> float:
        """
        Returns the vertical velocity of the rocket in m/s. Calculated by differentiating the
        altitude.
        """
        return float(self._velocity_from_altitude)

    @property
    def velocity_from_acceleration(self) -> float:
        """The current vertical velocity of the rocket in m/s. Calculated by integrating the
        compensated acceleration."""
        return float(self._velocity_from_acceleration)

    @property
    def max_velocity_from_acceleration(self) -> float:
        """The maximum vertical velocity the rocket has attained during the flight, in m/s."""
        return float(self._max_velocity_from_acceleration)

    @property
    def vertical_acceleration(self) -> float:
        """The vertical acceleration of the rocket in m/s^2."""
        return float(self._rotated_acceleration)

    @property
    def current_timestamp(self) -> int:
        """The timestamp of the last data packet in milliseconds."""
        try:
            return self._last_data_packet.timestamp
        except AttributeError:  # If we don't have a last data packet
            return 0

    @property
    def roll_pitch_yaw(self) -> tuple[np.float64, np.float64, np.float64]:
        """The roll pitch and yaw of the rocket, in degrees."""
        return tuple(self._current_orientation_quaternions.as_euler("xyz", degrees=True))

    @property
    def velocity_moving_average(self):
        """List of the 10 previous velocity calculations for use in a moving average"""
        return self._velocity_rolling_average

    def update(self, data_packet: IMUDataPacket) -> None:
        """
        Updates the data points to process. This will recompute all information and handle math
        related to orientation (quaternions/pitch roll yaw) such as altitude, velocity,
        acceleration, and crew survivability.
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

        self._rotated_acceleration = self._calculate_rotated_acceleration()
        self._velocity_from_acceleration = self._calculate_velocity_from_acceleration()
        self._velocity_from_altitude = self._calculate_velocity_from_altitude()
        self._max_velocity_from_acceleration = max(
            self._velocity_from_acceleration, self._max_velocity_from_acceleration
        )

        self._current_altitude = self._calculate_current_altitude()
        self._max_altitude = max(self._current_altitude, self._max_altitude)

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
            velocity_from_acceleration=self._velocity_from_acceleration,
            velocity_from_altitude=self._velocity_from_altitude,
            vertical_acceleration=self._rotated_acceleration,
            time_since_last_data_packet=self._time_difference,
            maximum_altitude=np.float64(self.max_altitude),
            maximum_velocity=np.float64(self.max_velocity_from_acceleration),
            crew_survivability=self._crew_survivability,
            roll=self.roll_pitch_yaw[0],
            pitch=self.roll_pitch_yaw[1],
            yaw=self.roll_pitch_yaw[2],
            landing_velocity=self._landing_velocity,
        )

    def _first_update(self) -> None:
        """
        Sets up the initial values for the data processor. This includes setting the initial
        altitude, and the initial orientation of the rocket. This should
        only be called once, when the first data packets are passed in.
        """
        # Setting last data packet as this packet makes it so that the time diff
        # automatically becomes 0, and the velocity becomes 0
        self._last_data_packet = self._data_packet

        # This is us getting the rocket's initial altitude from the first data packets
        self._initial_altitude = self._data_packet.pressureAlt

        # This is us getting the rocket's initial orientation
        # Convert initial orientation quaternion array to a scipy Rotation object
        # This will automatically normalize the quaternion as well:
        self._current_orientation_quaternions = R.from_quat(
            np.array(
                [
                    self._data_packet.estOrientQuaternionW,
                    self._data_packet.estOrientQuaternionX,
                    self._data_packet.estOrientQuaternionY,
                    self._data_packet.estOrientQuaternionZ,
                ]
            ),
            scalar_first=True,  # This means the order is w, x, y, z.
        )

    def _calculate_current_altitude(self) -> np.float64:
        """
        Calculates the current altitude, by zeroing out the initial altitude.
        :return: the current altitude of the rocket
        """
        # Get the pressure altitude from the data points and zero out the initial altitude
        return self._data_packet.pressureAlt - self._initial_altitude

    def _calculate_rotated_acceleration(self) -> np.float64:
        """
        Calculates the rotated vertical acceleration.

        :return: float containing the vertical acceleration
        """
        self._current_orientation_quaternions = R.from_quat(
            np.array(
                [
                    self._data_packet.estOrientQuaternionW,
                    self._data_packet.estOrientQuaternionX,
                    self._data_packet.estOrientQuaternionY,
                    self._data_packet.estOrientQuaternionZ,
                ]
            ),
            scalar_first=True,  # This means the order is w, x, y, z.
        )

        # Accelerations are in m/s^2
        x_accel = self._data_packet.estCompensatedAccelX
        y_accel = self._data_packet.estCompensatedAccelY
        z_accel = self._data_packet.estCompensatedAccelZ

        # Rotate the acceleration vector using the orientation
        rotated_accel = self._current_orientation_quaternions.apply([x_accel, y_accel, z_accel])

        # Vertical acceleration will always be the 3rd element of the rotated vector,
        # regardless of orientation.
        return -rotated_accel[2]

    def _calculate_velocity_from_acceleration(self) -> np.float64:
        """
        Calculates the velocity of the rocket based on the rotated compensated acceleration.
        Integrates that acceleration to get the velocity.
        :return: A numpy array of the velocity of the rocket at each data packet
        """
        # Gets the vertical acceleration from the rotated vertical acceleration. gravity needs to be
        # subtracted from vertical acceleration, Then deadbanded.
        vertical_acceleration = deadband(
            self._rotated_acceleration - GRAVITY_METERS_PER_SECOND_SQUARED,
            ACCEL_DEADBAND_METERS_PER_SECOND_SQUARED,
        )

        # Integrate the acceleration to get the velocity
        vertical_velocity = (
            self._previous_vertical_velocity + vertical_acceleration * self._time_difference
        )

        # Store the last calculated velocity vector
        self._previous_vertical_velocity = vertical_velocity

        return vertical_velocity

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
            velocity = self._velocity_from_altitude

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

    def _calculate_crew_survivability(self) -> np.float64:
        """
        Calculates the probability that our crew of STEMnauts is alive depending on
        conditions during the flight. The surviabililty is only dependent on events after
        motor burn out. and ground hit velocity
        :return: A float with the percent chance that our crew is still alive
        """

        updated_survival_chance = self._crew_survivability

        # These constants are optimized so that no constant alone largely affects the chance
        # of survival
        intensity_percent = (
            np.abs(self.vertical_acceleration) * VERTICAL_ACCELERATION_WEIGHT
            + np.abs(self._data_packet.estAngularRateY) * ANGULAR_RATE_WEIGHT
            + np.sin(self.roll_pitch_yaw[1] / 2) * PITCH_WEIGHT
        ) / 100.0

        if intensity_percent > INTENSITY_PERCENT_THRESHOLD:
            # Since the code is updated so frequently, intensity percent is divided by large
            # factor to not instantly remove all survival chance
            updated_survival_chance = self._crew_survivability * (1.0 - intensity_percent / 100)

        return updated_survival_chance

    def finalize_crew_survivability(self):
        """
        Deducts a percentage of survival chance based on the ground hit velocity
        """
        if(self._landing_velocity < LANDING_VELOCITY_THRESHOLD):
            self.data_processor._crew_survivability *= LANDING_VELOCITY_DEDUCTION
