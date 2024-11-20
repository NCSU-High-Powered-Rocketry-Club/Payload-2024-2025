from __future__ import annotations
import serial
import threading
import time
import logging
import msgspec
from typing import Optional, TYPE_CHECKING

from .shared.utils import readline

if TYPE_CHECKING:
    from .payload import PayloadSystem


class SensorReading(msgspec.Struct):
    altitude: float
    voltage: float
    temperature: float

    gyro: Optional[dict[str, float]] = None
    accel: Optional[dict[str, float]] = None
    mag: Optional[dict[str, float]] = None
    linearAccel: Optional[dict[str, float]] = None
    quat: Optional[dict[str, float]] = None
    gps: Optional[dict[str, float]] = None


class SensorReader:

    def __init__(
        self, payload: PayloadSystem, port: str, baudrate: int = 115200
    ) -> None:
        self.feather = serial.Serial(port, baudrate)
        self.running = True
        self.recv_thread = threading.Thread(target=self.receive_thread)

        self.decoder = msgspec.json.Decoder(SensorReading)
        self.payload = payload

    def start(self):
        self.running = True
        self.recv_thread.start()

    def stop(self):
        self.running = False
        self.feather.close()
        self.recv_thread.join()

    def process_data(self, data: bytes):
        decoded_data: SensorReading = self.decoder.decode(data)

        if decoded_data.gyro:
            received = decoded_data.gyro
            self.payload.data.gyro = (
                received["x"],
                received["y"],
                received["z"],
            )

        if decoded_data.accel:
            received = decoded_data.accel
            self.payload.data.accel = (
                received["x"],
                received["y"],
                received["z"],
            )

        if decoded_data.linearAccel:
            received = decoded_data.linearAccel
            self.payload.data.linear_accel = (
                received["x"],
                received["y"],
                received["z"],
            )
        if decoded_data.mag:
            received = decoded_data.mag
            self.payload.data.mag = (
                received["x"],
                received["y"],
                received["z"],
            )


        if decoded_data.quat:
            received = decoded_data.quat
            self.payload.data.quat = (
                received["i"],
                received["j"],
                received["k"],
                received["real"],
            )

        self.payload.data.altitude = decoded_data.altitude
        self.payload.data.temperature = decoded_data.temperature

        if decoded_data.gps:
            received = decoded_data.gps
            self.payload.data.gps = (
                received["lat"],
                received["lon"],
                received["alt"],
            )

        logging.info(data.decode())

        self.payload.update_stats()

    def receive_thread(self):
        """
        Listen thread for incoming data from the feather
        """
        while self.running:
            # Avoid hogging thread time
            time.sleep(0.0001)

            data = readline(self.feather, b"\r\n", lambda: self.running)

            if data == b"":
                continue

            try:
                self.process_data(data)
            except Exception as e:
                logging.error(e)
                logging.error(f"Error on processing data {data}")
