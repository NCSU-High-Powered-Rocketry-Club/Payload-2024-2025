"""Module for the ContextDataPacket class."""

from typing import Literal

import msgspec


class ContextDataPacket(msgspec.Struct):
    """
    This data packet keeps data owned by the PayloadContext as well as metadata about the context.
    """

    state_name: Literal["S", "M", "C", "F", "L"]
    """Represents the stage of flight we are in. Will only be a single letter."""

    transmitted_message: str
    """The message transmitted to the ground station."""

    received_message: str
    """The message received from the ground station."""

    update_timestamp_ns: int
    """The timestamp reported by the local computer at which we processed
    and logged this data packet. This is used to compare the time difference between
    what is reported by the IMU, and when we finished processing the data packet."""
