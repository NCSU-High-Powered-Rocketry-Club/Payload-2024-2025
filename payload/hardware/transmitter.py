"""Module for the Transmitter class that controls the SA85 transceiver."""

import threading
import time
import socket

from RPi import GPIO

from payload.data_handling.packets.transmitter_data_packet import TransmitterDataPacket
from payload.interfaces.base_transmitter import BaseTransmitter
from payload.constants import TRANSMITTER_PIN, KISS_HOST, KISS_PORT, NUMBER_OF_TRANSMISSIONS, \
    TRANSMISSION_WINDOW_SECONDS


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

    def start(self) -> None:
        """
        Starts the transmitter.
        """
        GPIO.setmode(GPIO.BCM)  # Use Broadcom pin-numbering scheme
        # Set pin as an output and initially high
        GPIO.setup(TRANSMITTER_PIN, GPIO.OUT, initial=GPIO.LOW)

    def stop(self) -> None:
        """
        Stops the transmitter and cleans up GPIO resources.
        """
        # Pull the pin low to stop transmitting
        GPIO.output(TRANSMITTER_PIN, GPIO.LOW)
        self._stop_event.set()
        # If we stop the program before a message is sent, the thread won't exist
        if self.message_worker_thread:
            self.message_worker_thread.join(5)

    def send_message(self, message: str) -> None:
        """
        Sends a message to the ground station.
        """
        self.message_worker_thread = threading.Thread(
            target=self._send_message_worker, args=(message,)
        )
        self.message_worker_thread.start()

    @staticmethod
    def _send_kiss_packet(message: str) -> None:
        """
        Send an APRS packet using the KISS TCP interface to Direwolf.
        :param message: The APRS message to send.
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect((KISS_HOST, KISS_PORT))
                # KISS frame: 0xC0 (Start), 0x00 (Data Frame), message, 0xC0 (End)
                kiss_frame = b"\xc0\x00" + message.encode() + b"\xc0"
                sock.sendall(kiss_frame)
            print("✅ APRS packet sent successfully via KISS mode.")
        except Exception as e:
            print(f"❌ Failed to send APRS packet: {e}")

    def _send_message_worker(self, message: TransmitterDataPacket) -> None:
        """
        Handles the message transmission process in a separate thread.
        """
        # TODO: add the lat and long
        lat, long = message.landing_coords
        compressed_message = message.compress_packet()
        for i in range(NUMBER_OF_TRANSMISSIONS):
            GPIO.output(TRANSMITTER_PIN, GPIO.HIGH)
            # TODO: test if we can move this outside of the for loop
            self._send_kiss_packet(compressed_message)
            time.sleep(TRANSMISSION_WINDOW_SECONDS)
            GPIO.output(TRANSMITTER_PIN, GPIO.LOW)
