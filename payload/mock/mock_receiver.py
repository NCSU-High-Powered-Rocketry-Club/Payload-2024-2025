"""Module for the MockReceiver class."""

import threading
import time

from payload.constants import NO_MESSAGE
from payload.interfaces.base_receiver import BaseReceiver


class MockReceiver(BaseReceiver):
    """
    This is a mock class that simulates the Receiver. It will return a predetermined message when
    fetch_data is called.
    """

    __slots__ = (
        "_running",
        "_thread",
        "initial_delay",
        "message",
        "receive_delay",
        "receive_message",
    )

    def __init__(self, initial_delay: float, receive_delay: float, receive_message: str) -> None:
        self.message: str = NO_MESSAGE
        self.initial_delay: float = initial_delay
        self.receive_delay: float = receive_delay
        self.receive_message: str = receive_message
        self._running: bool = False
        self._thread: threading.Thread = threading.Thread(target=self._listen, daemon=True)

    @property
    def latest_message(self) -> str:
        """Returns the predetermined message."""
        return self.message

    def _listen(self) -> None:
        """Simulates listening by periodically updating the message."""
        time.sleep(self.initial_delay)
        while self._running:
            self.message = self.receive_message
            time.sleep(self.receive_delay)

    def start(self) -> None:
        """Starts the listening process in a separate thread."""
        if not self._running:
            self._running = True
            self._thread.start()

    def stop(self) -> None:
        """Stops the listening process."""
        if self._running:
            self._running = False
            self._thread.join()
