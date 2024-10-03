from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .payload import FlightStats


class RFInterface:
    def __init__(self, callsign: str):
        pass

    def transmit_data(data: FlightStats):
        pass
