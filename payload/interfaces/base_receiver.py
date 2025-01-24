"""Module defining the base class (BaseReceiver)"""
from abc import ABC, abstractmethod


class BaseReceiver(ABC):
    """
    Represents the receiver on the rocket. This class will read data and package it into an
    ReceiverDataPacket that can be fetched with the fetch_data method.
    """

    @abstractmethod
    @property
    def latest_message(self) -> str:
        """
        Property to get the most recently received message.
        """

    @abstractmethod
    def start(self) -> None:
        """
        Starts the receiver.
        """

    @abstractmethod
    def stop(self) -> None:
        """
        Stops the receiver.
        """