"""Module for the Transmitter class that controls the SA85 transceiver."""

import subprocess
import threading
import time
import socket

from RPi import GPIO

from payload.data_handling.packets.transmitter_data_packet import TransmitterDataPacket
from payload.interfaces.base_transmitter import BaseTransmitter
from payload.constants import DIREWOLF_CONFIG_PATH
from payload.constants import TRANSMITTER_PIN

class Transmitter(BaseTransmitter):
    """
    This is the class that controls the SA85 transceiver. It is responsible for sending messages
    to our ground station.
    """

    __slots__ = ("_stop_event", "config_path", "message_worker_thread", "transmitter_pin")

    def __init__(self, gpio_pin, config_path) -> None:
        """
        Initializes the transmitter with the specified GPIO pin and Direwolf configuration file
        path.
        :param gpio_pin: The GPIO pin number that is connected to the PTT pin of the transceiver.
        :param config_path: The path to the Direwolf configuration file.
        """
        # Sets the GPIO pin to be an output pin and has it start set high (inactive).
        self.config_path = config_path
        self._stop_event = threading.Event()
        self.message_worker_thread = None

        GPIO.setmode(GPIO.BCM)  # Use Broadcom pin-numbering scheme
        GPIO.setup(TRANSMITTER_PIN, GPIO.OUT, initial=GPIO.LOW)  # Set pin as an output and initially high 

    def _pull_pin_low(self) -> None:
        """
        Pulls the GPIO pin low. This deactivates the PTT (Push-To-Talk) of the transceiver.
        """
        GPIO.output(TRANSMITTER_PIN, GPIO.LOW)

    def _pull_pin_high(self) -> None:
        """
        Pulls the GPIO pin high. This activates the PTT (Push-To-Talk) of the transceiver.
        """
        GPIO.output(TRANSMITTER_PIN, GPIO.HIGH)

    def _send_message_worker(self, message: TransmitterDataPacket) -> None:
        """
        Handles the message transmission process in a separate thread.
        """
        lat, long = message.landing_coords
        compressed_message = message.compress_packet()
        for i in range(2):
            self._pull_pin_high()
            self.send_kiss_packet(message.compress_packet())
            time.sleep(5)
            self._pull_pin_low()    

    def start(self) -> None:
        """
        Starts the transmitter.
        """
        # TODO

    def stop(self) -> None:
        """
        Stops the transmitter and cleans up GPIO resources.
        """
        self._pull_pin_low()
        self._stop_event.set()
        if self.message_worker_thread:
            self.message_worker_thread.join(5)
        print("Stopped Transmitter")

    def send_message(self, message: str) -> None:
        """
        Sends a message to the ground station.
        """
        self.message_worker_thread = threading.Thread(
            target=self._send_message_worker, args=(message,)
        )
        self.message_worker_thread.start()

    def send_kiss_packet(self, message):
        """Send an APRS packet using the KISS TCP interface to Direwolf."""
        KISS_HOST = "127.0.0.1"  # Localhost where Direwolf is running
        KISS_PORT = 8001  # KISS TCP port
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect((KISS_HOST, KISS_PORT))
                # KISS frame: 0xC0 (Start), 0x00 (Data Frame), message, 0xC0 (End)
                kiss_frame = b"\xc0\x00" + message.encode() + b"\xc0"
                sock.sendall(kiss_frame)
            print("✅ APRS packet sent successfully via KISS mode.")
        except Exception as e:
            print(f"❌ Failed to send APRS packet: {e}")
