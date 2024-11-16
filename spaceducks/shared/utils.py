import serial
from typing import Callable


def readline(
    serial: serial.Serial, eol: bytes, check_running: Callable[[], bool]
) -> bytes:
    """
    Taken almost wholesale from
    https://stackoverflow.com/questions/16470903/pyserial-2-6-specify-end-of-line-in-readline

    Modified so it actually blocks until fully read incoming data rather than receiving a
    half-finished string because the incoming stream paused
    """

    leneol = len(eol)
    line = bytearray()
    while check_running():
        c = serial.read(1)
        line += c
        if line[-leneol:] == eol:
            line = line.strip(eol)
            break

    return bytes(line)
