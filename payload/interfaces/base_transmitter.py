"""Module for defining the base class (BaseTransmitter)"""

from abc import ABC, abstractmethod


class BaseTransmitter(ABC):
    """
    Represents the transmitter on the rocket. This class will send data to the ground station.
    """

    @abstractmethod
    def start(self) -> None:
        """
        Starts the transmitter.
        """

    @abstractmethod
    def stop(self) -> None:
        """
        Stops the transmitter.
        """

    @abstractmethod
    def send_message(self, message: str) -> None:
        """
        Sends a message to the ground station.
        :param message: The message to send.
        """
