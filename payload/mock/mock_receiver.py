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
        "message",
        "initial_delay",
        "receive_delay",
        "receive_message",
        "_running",
        "_thread",
    )

    def __init__(self, initial_delay: float, receive_delay: float, receive_message: str) -> None:
        self.message = NO_MESSAGE
        self.initial_delay = initial_delay
        self.receive_delay = receive_delay
        self.receive_message = receive_message
        self._running = False
        self._thread = None

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
            self._thread = threading.Thread(target=self._listen, daemon=True)
            self._thread.start()

    def stop(self) -> None:
        """Stops the listening process."""
        if self._running:
            self._running = False
            if self._thread is not None:
                self._thread.join()
                self._thread = None
