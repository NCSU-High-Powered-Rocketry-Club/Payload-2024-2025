"""Module for the mock transmitter class (MockTransmitter)"""

from pathlib import Path
from typing import TextIO

from payload.interfaces.base_transmitter import BaseTransmitter


class MockTransmitter(BaseTransmitter):
    """
    This is the class that mocks the SA85 transceiver. Rather than actually transmitting messages it
    just writes them to a file.
    """

    def __init__(self, message_file_path: Path) -> None:
        """
        Initializes the mock transmitter with the specified message file path.
        :param message_file_path: The path to the file where messages will be written.
        """
        self.message_file_path = message_file_path
        self.file: TextIO | None = None

    def start(self) -> None:
        """Opens the message file in write mode to clear it and keep it open for writing."""
        self.file = Path.open(self.message_file_path, "w")

    def stop(self) -> None:
        """Closes the file when stopping the transmitter."""
        if self.file:
            self.file.close()

    def send_message(self, message: str) -> None:
        """
        Sends a message to the ground station.
        :param message: The message to send.
        """
        if self.file:
            self.file.write(message + "\n")
            # Makes sure the message is written to the file immediately rather than waiting for the
            # buffer to fill
            self.file.flush()
