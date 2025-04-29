"""Module for the finite state machine that represents which state of flight we are in."""

import threading
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from payload.constants import (
    GROUND_ALTITUDE_METERS,
    MAX_FREE_FALL_SECONDS,
    SECONDS_TO_CONSIDERED_LANDED,
    MOTOR_BURN_TIME_SECONDS,
    TAKEOFF_HEIGHT_METERS,
    TAKEOFF_VELOCITY_METERS_PER_SECOND,
    MAX_VELOCITY_THRESHOLD,
    MAX_ALTITUDE_THRESHOLD,
)
from payload.utils import convert_milliseconds_to_seconds

if TYPE_CHECKING:
    from payload.payload import PayloadContext


class State(ABC):
    """
    Abstract Base class for the states of the payload system. Each state will have an update
    method that will be called every loop iteration and a next_state method that will be called
    when the state is over.

    For payload, we will have 5 states:
    1. Stand By - when the rocket is on the rail on the ground
    2. Motor Burn - when the motor is burning and the rocket is accelerating
    3. Flight - when the motor has burned out and the rocket is coasting
    4. Free Fall - when the rocket is falling back to the ground after apogee
    5. Landed - when the rocket has landed
    """

    __slots__ = (
        "context",
        "start_time_ms",
    )

    def __init__(self, context: "PayloadContext"):
        """
        :param context: The state context object that will be used to interact with the electronics
        """
        self.context = context
        self.start_time_ms = context.data_processor.current_timestamp

    @property
    def name(self):
        """
        :return: The name of the state
        """
        return self.__class__.__name__

    @abstractmethod
    def update(self):
        """
        Called every loop iteration. Uses the context to interact with the hardware and decides
        when to move to the next state.
        """

    @abstractmethod
    def next_state(self):
        """
        We never expect/want to go back a state e.g. We're never going to go
        from Flight to Motor Burn, so this method just goes to the next state.
        """


class StandbyState(State):
    """
    When the rocket is on the rail on the ground.
    """

    __slots__ = ()

    def update(self):
        """
        Checks if the rocket has launched, based on our velocity and altitude.
        """
        # We need to check if the rocket has launched, if it has, we move to the next state.
        # For that we can check:
        # 1) Altitude - If the altitude is above a threshold, the rocket has launched.
        # Ideally we would directly communicate with the motor, but we don't have that capability.
        data = self.context.data_processor

        if (
            data.current_altitude > TAKEOFF_HEIGHT_METERS
            and data.velocity_moving_average > TAKEOFF_VELOCITY_METERS_PER_SECOND
        ):
            self.next_state()
            return

    def next_state(self):
        self.context.state = MotorBurnState(self.context)


class MotorBurnState(State):
    """
    When the motor is burning and the rocket is accelerating.
    """

    __slots__ = ()

    def __init__(self, context: "PayloadContext"):
        """Overrides the __init__ to start the camera recording."""
        super().__init__(context)
        self.context.start_saving_camera_recording()

    def update(self):
        """Checks to see if the acceleration has dropped to zero, indicating the motor has
        burned out."""
        data = self.context.data_processor

        # If our current velocity is less than our max velocity, that means we have stopped
        # accelerating. This is the same thing as checking if our accel sign has flipped
        # We make sure that it is not just a temporary fluctuation by checking if the velocity is a
        # bit less than the max velocity
        if (
            convert_milliseconds_to_seconds(
                self.context.data_processor.current_timestamp - self.start_time_ms
            ) >= MOTOR_BURN_TIME_SECONDS
        ):
            self.next_state()
            return

    def next_state(self):
        self.context.state = CoastState(self.context)


class CoastState(State):
    """
    When the motor has burned out and the rocket is coasting to apogee.
    """

    __slots__ = ()

    def __init__(self, context: "PayloadContext"):
        super().__init__(context)
        self.context.start_survivability_calculation()

    def update(self):
        """Checks to see if the rocket has reached apogee, indicating the start of free fall."""
        data = self.context.data_processor

        # If our current altitude is less than 90% of max altitude, we are in free fall.
        if data.current_altitude <= data.max_altitude * MAX_ALTITUDE_THRESHOLD:
            self.next_state()
            return

    def next_state(self):
        self.context.state = FreeFallState(self.context)


class FreeFallState(State):
    """
    When the rocket is falling back to the ground after apogee.
    """

    __slots__ = ("countdown_to_landed_timer", "_counter_started")

    def __init__(self, context):
        super().__init__(context)
        self.countdown_to_landed_timer = threading.Timer(
            interval=SECONDS_TO_CONSIDERED_LANDED, function=self.next_state
        )
        self._counter_started: bool = False

    def update(self):
        """Check if the rocket has landed, based on our altitude."""
        data = self.context.data_processor

        # If our altitude is around 0, we start a timer and then switch states, to make sure
        # we have landed.
        if data.current_altitude <= GROUND_ALTITUDE_METERS and not self._counter_started:
            self._counter_started = True
            self.context.stop_survivability_calculation()
            self.context.data_processor.calculate_landing_velocity()
            self.countdown_to_landed_timer.start()

        # If we have been in free fall for too long, we move to the landed state
        if (
            convert_milliseconds_to_seconds(
                self.context.data_processor.current_timestamp - self.start_time_ms
            )
            >= MAX_FREE_FALL_SECONDS
        ):
            self.next_state()

    def next_state(self):
        self.context.state = LandedState(self.context)


class LandedState(State):
    """
    When the rocket has landed.
    """

    __slots__ = ()

    def __init__(self, context: "PayloadContext"):
        super().__init__(context)

        # Starts the transmission at the beginning of landed state
        self.context.transmit_data()

        # Once we land we stop the camera recording
        self.context.end_video_recording()

    def update(self):
        """This method does nothing"""

    def next_state(self):
        # Explicitly do nothing, there is no next state
        pass
