"""Module for processing IMU data on a higher level."""

import numpy as np
import numpy.typing as npt
from scipy.spatial.transform import Rotation as R

from payload.constants import (
    ACCEL_DEADBAND_METERS_PER_SECOND_SQUARED,
    GRAVITY_METERS_PER_SECOND_SQUARED,
)
from payload.data_handling.packets.imu_data_packet import IMUDataPacket
from payload.data_handling.packets.processed_data_packet import ProcessedDataPacket
from payload.utils import convert_milliseconds_to_seconds, deadband


class IMUDataProcessor:
    """
    Performs high level calculations on the data packets received from the IMU. Includes
    calculation the rolling averages of acceleration, maximum altitude so far, etc., from the set of
    data points.
    """

    __slots__ = (
        "_current_altitude",
        "_current_orientation_quaternions",
        "_data_packet",
        "_initial_altitude",
        "_last_data_packet",
        "_max_altitude",
        "_max_vertical_velocity",
        "_previous_vertical_velocity",
        "_rotated_acceleration",
        "_time_difference",
        "_vertical_velocity",
    )

    def __init__(self):
        """
        Initializes the IMUDataProcessor object. It processes data points to calculate various
        things we need such as the maximum altitude, current altitude, velocity, etc. All numbers
        in this class are handled with numpy.

        This class has properties for the maximum altitude, current altitude, velocity, and
        maximum velocity of the rocket.
        """
        self._max_altitude: np.float64 = np.float64(0.0)
        self._vertical_velocity: np.float64 = np.float64(0.0)
        self._max_vertical_velocity: np.float64 = np.float64(0.0)
        self._previous_vertical_velocity: np.float64 = np.float64(0.0)
        self._initial_altitude: np.float64 | None = None
        self._current_altitude: np.float64 = np.float64(0.0)
        self._last_data_packet: IMUDataPacket | None = None
        self._current_orientation_quaternions: R | None = None
        self._rotated_acceleration: np.float64 = np.float64(0.0)
        self._data_packet: IMUDataPacket | None = None
        self._time_difference: np.float64 = np.float64(0.0)

    def __str__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"max_altitude={self.max_altitude}, "
            f"current_altitude={self.current_altitude}, "
            f"velocity={self.vertical_velocity}, "
            f"max_velocity={self.max_vertical_velocity}, "
        )

    @property
    def max_altitude(self) -> float:
        """
        Returns the highest altitude (zeroed out) attained by the rocket for the entire flight
        so far, in meters.
        """
        return float(self._max_altitude)

    @property
    def current_altitude(self) -> float:
        """Returns the altitude of the rocket (zeroed out) from the data points, in meters."""
        return float(self._current_altitude)

    @property
    def vertical_velocity(self) -> float:
        """The current vertical velocity of the rocket in m/s. Calculated by integrating the
        compensated acceleration."""
        return float(self._vertical_velocity)

    @property
    def max_vertical_velocity(self) -> float:
        """The maximum vertical velocity the rocket has attained during the flight, in m/s."""
        return float(self._max_vertical_velocity)

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

    def update(self, data_packet: IMUDataPacket) -> None:
        """
        Updates the data points to process. This will recompute all information such as altitude,
        velocity, etc.
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

        self._time_difference = self._calculate_time_difference()

        self._rotated_acceleration = self._calculate_rotated_acceleration()
        self._vertical_velocity = self._calculate_vertical_velocity()
        self._max_vertical_velocity = max(self._vertical_velocity, self._max_vertical_velocity)

        self._current_altitude = self._calculate_current_altitude()
        self._max_altitude = max(self._current_altitude, self._max_altitude)

        # Store the last data point for the next update
        self._last_data_packet = data_packet

    def get_processed_data_packet(self) -> ProcessedDataPacket:
        """
        Processes the data points and returns a ProcessedDataPacket object.

        :return: A ProcessedDataPacket object.
        """
        # TODO: clean this up
        return ProcessedDataPacket(
            current_altitude=self._current_altitude,
            vertical_velocity=self._vertical_velocity,
            vertical_acceleration=self._rotated_acceleration,
            time_since_last_data_packet=self._time_difference,
            maximum_altitude=self.max_altitude,
            maximum_velocity=self.max_vertical_velocity,
            # the following are placeholders
            pitch=0.0,
            roll=0.0,
            yaw=0.0,
            crew_survivability=0.0,
            landing_velocity=0.0,
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
        Calculates the rotated vertical acceleration. Converts gyroscope data into a delta
        quaternion, and adds onto the last quaternion.

        :return: float containing the vertical acceleration
        """

        current_orientation = self._current_orientation_quaternions
        # Accelerations are in m/s^2
        x_accel = self._data_packet.estCompensatedAccelX
        y_accel = self._data_packet.estCompensatedAccelY
        z_accel = self._data_packet.estCompensatedAccelZ
        # Angular rates are in rads/s
        gyro_x = self._data_packet.estAngularRateX
        gyro_y = self._data_packet.estAngularRateY
        gyro_z = self._data_packet.estAngularRateZ

        # scipy docs for more info: https://docs.scipy.org/doc/scipy/reference/generated/scipy.spatial.transform.Rotation.html
        # Calculate the delta quaternion from the angular rates
        dt = self._time_difference
        delta_rotation = R.from_rotvec(np.array([gyro_x * dt, gyro_y * dt, gyro_z * dt]))

        # Update the current orientation by applying the delta rotation
        current_orientation = current_orientation * delta_rotation

        # Rotate the acceleration vector using the updated orientation
        rotated_accel = current_orientation.apply([x_accel, y_accel, z_accel])
        # Update the class attribute with the latest quaternion orientation
        self._current_orientation_quaternions = current_orientation
        # Vertical acceleration will always be the 3rd element of the rotated vector,
        # regardless of orientation.
        return -rotated_accel[2]

    def _calculate_vertical_velocity(self) -> npt.NDArray[np.float64]:
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

    def _calculate_time_difference(self) -> np.float64:
        """
        Calculates the time difference between the data packet and the previous data packet.
        This cannot be called on the first update as _last_data_packet is None. Units are in
        seconds.
        :return: A float with the time difference between the data packet and the previous
            data packet.
        """
        # calculate the time difference between the data packets
        # We are converting from ms to s, since we don't want to have a velocity in m/ms^2
        return np.float64(
            convert_milliseconds_to_seconds(
                self._data_packet.timestamp - self._last_data_packet.timestamp
            )
        )
