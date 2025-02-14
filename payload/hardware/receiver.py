import threading

import serial

from payload.constants import NO_MESSAGE
from payload.interfaces.base_receiver import BaseReceiver


class Receiver(BaseReceiver):
    """
    This is the class that controls the Xbee Pro s3b. On a separate thread, it listens for incoming
    messages from the transmitter and then makes them available to the main thread.
    """

    __slots__ = ("_latest_message", "_stop_event", "_thread", "_baud_rate", "_port", "_lock", "_serial")

    def __init__(self, port: str, baud_rate: int) -> None:
        self._port = port
        self._baud_rate = baud_rate
        self._serial = None

        self._latest_message: str = NO_MESSAGE

        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._listen, daemon=True)

    @property
    def latest_message(self) -> str:
        """Property to get the most recently received message."""
        # The lock makes sure that the latest message is not being updated while it is being read.
        with self._lock:
            return self._latest_message

    def start(self) -> None:
        """Starts the listening thread."""
        self._serial = serial.Serial(self._port, self._baud_rate, timeout=1)
        self._stop_event.clear()
        self._thread.start()

    def stop(self) -> None:
        """Stops the listening thread."""
        self._stop_event.set()
        self._serial.close()
        self._thread.join(timeout=3)

    def _listen(self) -> None:
        """Continuously listens for serial input."""
        # TODO: clean up these prints and expand docstring
        try:
            print(f"Listening on {self._port} at {self._baud_rate} baud rate...")
            while not self._stop_event.is_set():
                if self._serial.in_waiting > 0:  # Check if data is available
                    line = self._serial.readline().decode("utf-8", errors="ignore").strip()
                    print("got line")
                    if line:
                        with self._lock:
                            self._latest_message = line.strip()
                            print(f"Received: {self._latest_message}")
            print("exitted while loop")
        except serial.SerialException as e:
            print(f"Error: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")
        finally:
            print("Stopped listening.")
