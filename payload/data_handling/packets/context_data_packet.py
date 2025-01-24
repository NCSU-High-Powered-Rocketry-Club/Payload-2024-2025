"""Module for the ContextDataPacket class."""

from typing import Literal

import msgspec


class ContextDataPacket(msgspec.Struct):
    """
    This data packet keeps data owned by the PayloadContext as well as metadata about the context.
    """

    state_name: Literal["S", "M", "C", "F", "L"]
    """Represents the stage of flight we are in. Will only be a single letter."""

    received_message: str
    """The message received from the ground station."""
