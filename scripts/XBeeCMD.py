import threading
import time

from ..spaceducks.shared.utils import readline
from ..spaceducks.shared.xbee_interface import XbeeInterface

xbee_port = 10  # RX pin


class XBeeCMD:
    def __init__(self) -> None:
        self.xbee = XbeeInterface(xbee_port, self.receive_message)
        self.xbee.start()

        self.running = True
        self.recv_thread = threading.Thread(target=self.receive_thread)

        self.lock = threading.Lock()

    def start(self):
        self.running = True
        self.recv_thread.start()

    def stop(self):
        self.running = False
        self.recv_thread.join()
        self.xbee.close()

    def receive_thread(self):
        while self.running:
            time.sleep(0.001)
            data = readline(self.xbee, b";", lambda: self.running)

            if data == b"":
                continue

            try:
                print(data)
            except Exception:
                print("ERROR")
