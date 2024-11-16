from __future__ import annotations
from typing import TYPE_CHECKING

import abc
import logging
import math

from .shared.state import SensorState, FlightStats, MESSAGE_TYPES, Message

if TYPE_CHECKING:
    from .payload import PayloadSystem


class BaseState(abc.ABC):

    @abc.abstractmethod
    def update(self, payload: PayloadSystem) -> None: ...


class StandbyState(BaseState):

    # Arm the payload if we detect at least this much acceleration
    MINIMUM_ARM_ACCEL = 50  # m/s^2

    def update(self, payload: PayloadSystem) -> None:
        # Update the current altitude at takeoff
        payload.stats.takeoff_alt = payload.data.altitude

        # If we detect takeoff, then we switch to armed mode
        if self.detect_takeoff(payload):
            logging.info("Takeoff detected, switching to arm state.")
            payload.xbee.send_data(Message("Takeoff detected."))

            payload.state = ArmedState()

    def detect_takeoff(self, payload: PayloadSystem) -> bool:
        """Function to test for takeoff conditions"""

        if None in payload.data.linear_accel:
            return False

        # Simply calculate the magnitude
        # (we could use a numpy function or mathutils Vector but it's probably overkill for now)
        magnitude = math.sqrt(sum(axis**2 for axis in payload.data.linear_accel))
        return magnitude >= self.MINIMUM_ARM_ACCEL


class ArmedState(BaseState):

    # The maximum rest acceleration and altitude to detect if we've landed
    MAXIMUM_REST_ACCEL = 0.4  # m/s^2
    MAXIMUM_REST_ALT = 5  # meters above initial takeoff altitude to consider

    def update(self, payload: PayloadSystem) -> None:
        if self.detect_landing(payload):
            logging.info("Landing detected, switching to land state.")
            payload.xbee.send_data(Message("Landing detected."))

            payload.state = LandedState()

    def detect_landing(self, payload: PayloadSystem) -> bool:
        """Function to test if the rocket has likely landed"""

        if None in payload.data.linear_accel:
            return False

        # Detect if we've landed based on both the IMU and measured altitude
        magnitude = math.sqrt(sum(axis**2 for axis in payload.data.linear_accel))
        at_rest = magnitude <= self.MAXIMUM_REST_ACCEL

        max_alt = payload.stats.takeoff_alt + self.MAXIMUM_REST_ALT
        under_altitude = payload.data.altitude <= max_alt

        return at_rest and under_altitude


class LandedState(BaseState):

    def update(self, payload: PayloadSystem) -> None:
        if payload.radio:
            logging.info("Transmitting data...")
            payload.radio.transmit_data(payload.stats)

        logging.info("Landed state.")
        logging.info(str(payload.stats))
        self.state = RecoverState()


class RecoverState(BaseState):

    def update(self, payload: PayloadSystem) -> None:
        payload.shutdown()
