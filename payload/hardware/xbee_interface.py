import logging
import threading
import time
from collections.abc import Callable

import msgspec
import serial

from ..spaceducks.shared.state import MESSAGE_TYPES
from ..spaceducks.shared.utils import readline


class XbeeInterface:
    def __init__(self, port: str, callback: Callable[[MESSAGE_TYPES], None]) -> None:
        self.xbee = serial.Serial(port)
        self.encoder = msgspec.msgpack.Encoder()
        self.decoder = msgspec.msgpack.Decoder(MESSAGE_TYPES)
        self.recv_thread = threading.Thread(target=self.receive_thread)

        self.running = True
        self.lock = threading.Lock()

        # Callback for whenever we receive data
        self.callback = callback

    def send_data(self, data: MESSAGE_TYPES):
        with self.lock:
            self.xbee.write(self.encoder.encode(data) + b";")

    def start(self):
        self.running = True
        self.recv_thread.start()

    def stop(self):
        self.running = False
        self.xbee.close()
        self.recv_thread.join()

    def process_data(self, data: bytes):
        decoded_data: MESSAGE_TYPES = self.decoder.decode(data)
        self.callback(decoded_data)

    def receive_thread(self):
        """
        Listen thread for incoming data from the xbee/arduino

        To avoid all kinds of newline wackiness, we use semicolons to separate data.
        Since it's just a regular ascii character it's less prone to silliness from
        protocols and such

        """
        while self.running:
            # Avoid hogging thread time
            time.sleep(0.0001)

            data = readline(self.xbee, b";", lambda: self.running)

            if data == b"":
                continue

            try:
                self.process_data(data)
            except Exception as e:
                logging.error(e)
                logging.error(f"Error on processing data {data}")
