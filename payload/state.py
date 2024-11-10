"""Module for the finite state machine that represents which state of flight we are in."""

from abc import ABC, abstractmethod

from constants import TAKEOFF_VELOCITY, TAKEOFF_HEIGHT, MAX_VELOCITY_THRESHOLD, GROUND_ALTITUDE
from payload import PayloadContext


class State(ABC):
    """
    Abstract Base class for the states of the payload system. Each state will have an update
    method that will be called every loop iteration and a next_state method that will be called
    when the state is over.

    For Payload, we will have 5 states:
    1. Stand By - when the rocket is on the rail on the ground
    2. Motor Burn - when the motor is burning and the rocket is accelerating
    3. Flight - when the motor has burned out and the rocket is coasting
    4. Free Fall - when the rocket is falling back to the ground after apogee
    5. Landed - when the rocket has landed
    """

    __slots__ = ("context",)

    def __init__(self, context: "PayloadContext"):
        """
        :param context: The state context object that will be used to interact with the electronics
        """
        self.context = context

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
        # 1) Velocity - If the velocity of the rocket is above a threshold, the rocket has
        # launched.
        # 2) Altitude - If the altitude is above a threshold, the rocket has launched.
        # Ideally we would directly communicate with the motor, but we don't have that capability.

        data = self.context.data_processor

        if data.vertical_velocity > TAKEOFF_VELOCITY:
            self.next_state()
            return

        if data.current_altitude > TAKEOFF_HEIGHT:
            self.next_state()
            return

    def next_state(self):
        self.context.state = MotorBurnState(self.context)


class MotorBurnState(State):
    """
    When the motor is burning and the rocket is accelerating.
    """

    __slots__ = ("start_time_ns",)

    def __init__(self, context: "PayloadContext"):
        super().__init__(context)
        # This will only be called once, when the motor starts burning
        self.start_time_ns = context.data_processor.current_timestamp

    def update(self):
        """Checks to see if the acceleration has dropped to zero, indicating the motor has
        burned out."""

        data = self.context.data_processor

        # If our current velocity is less than our max velocity, that means we have stopped
        # accelerating. This is the same thing as checking if our accel sign has flipped
        # We make sure that it is not just a temporary fluctuation by checking if the velocity is a
        # bit less than the max velocity
        if (
            data.vertical_velocity
            < data.max_vertical_velocity - data.max_vertical_velocity * MAX_VELOCITY_THRESHOLD
        ):
            self.next_state()
            return

    def next_state(self):
        self.context.state = CoastState(self.context)


class CoastState(State):
    """
    When the motor has burned out and the rocket is coasting to apogee.
    """

    def update(self):
        """Checks to see if the rocket has reached apogee, indicating the start of free fall."""
        data = self.context.data_processor

        # if our velocity is close to zero or negative, we are in free fall.
        if data.vertical_velocity <= 0:
            self.next_state()
            return

        # As backup in case of error, if our current altitude is less than 90% of max altitude, we
        # are in free fall.
        if data.current_altitude <= data.max_altitude * 0.9:
            self.next_state()
            return

    def next_state(self):
        self.context.state = FreeFallState(self.context)


class FreeFallState(State):
    """
    When the rocket is falling back to the ground after apogee.
    """

    __slots__ = ()

    def update(self):
        """Check if the rocket has landed, based on our altitude."""

        data = self.context.data_processor

        # If our altitude is 0, we have landed:
        if data.current_altitude <= GROUND_ALTITUDE:
            self.next_state()

    def next_state(self):
        self.context.state = LandedState(self.context)


class LandedState(State):
    """
    When the rocket has landed.
    """

    __slots__ = ()

    def update(self):
        pass

    def next_state(self):
        # Explicitly do nothing, there is no next state
        pass
