"""Module for the Transmitter class that controls the SA85 transceiver."""

import math
import re
import subprocess
import threading
import time

from payload.interfaces.base_transmitter import BaseTransmitter

try:
    # TODO: convert this to gpiozero, also go through and organize methods
    from RPi import GPIO
except (ImportError, RuntimeError):
    pass

from payload.data_handling.packets.transmitter_data_packet import TransmitterDataPacket
from payload.interfaces.base_transmitter import BaseTransmitter
from payload.constants import (
    DIREWOLF_CONFIG_PATH,
    TRANSMITTER_PIN,
    NUMBER_OF_TRANSMISSIONS,
    TRANSMISSION_WINDOW_SECONDS,
    TRANSMISSION_DELAY,
)


class Transmitter(BaseTransmitter):
    """
    This is the class that controls the SA85 transceiver. It is responsible for sending messages
    to our ground station.
    """

    __slots__ = ("_stop_event", "config_path", "gpio_pin", "message_worker_thread")

    def __init__(self, gpio_pin, config_path) -> None:
        """
        Initializes the transmitter with the specified GPIO pin and Direwolf configuration file
        path.
        :param gpio_pin: The GPIO pin number that is connected to the PTT pin of the transceiver.
        :param config_path: The path to the Direwolf configuration file.
        """
        self.gpio_pin = TRANSMITTER_PIN
        self.config_path = config_path
        self._stop_event = threading.Event()
        self.message_worker_thread = None

        self.setup_gpio()

    def setup_gpio(self):
        GPIO.setmode(GPIO.BCM)  # Use Broadcom pin-numbering scheme
        GPIO.setup(self.gpio_pin, GPIO.OUT, initial=GPIO.LOW)

    def pull_pin_low(self):
        #     """
        #     Pulls the GPIO pin low. This pulls the PTT high. This deactivates the PTT (Push-To-Talk) of the transceiver.
        #     """
        GPIO.setmode(GPIO.BCM)
        GPIO.output(self.gpio_pin, GPIO.LOW)

    def pull_pin_high(self):
        #     """
        #     Pulls the GPIO pin high. This pulls the PTT low. This activates the PTT (Push-To-Talk) of the transceiver.
        #     """
        GPIO.setmode(GPIO.BCM)
        GPIO.output(self.gpio_pin, GPIO.HIGH)

    def cleanup_gpio(self):
        GPIO.cleanup()  # Clean up GPIO to ensure no resources are left hanging

    def _create_beacon_line(self, message: TransmitterDataPacket) -> str:
        lat = message.landing_coords[0]
        lon = message.landing_coords[1]

        lat_hemi = "N" if lat > 0 else "S"
        lat_frac, lat_degrees = math.modf(abs(lat))
        lat_degrees = int(lat_degrees)
        lat_minutes = lat_frac * 60.0
        lat_str = f"{lat_degrees:02}^{lat_minutes:05.2f}{lat_hemi}"

        lon_hemi = "E" if lon > 0 else "W"
        lon_frac, lon_degrees = math.modf(abs(lon))
        lon_degrees = int(lon_degrees)
        lon_minutes = lon_frac * 60.0
        lon_str = f"{lon_degrees:03}^{lon_minutes:05.2f}{lon_hemi}"

        return f'PBEACON delay=0:1 every=0:5 overlay=S symbol=\\O lat={lat_str} long={lon_str} comment="{message.compress_packet()}"'

    def _update_beacon_comment(self, message: TransmitterDataPacket) -> bool:
        """
        Updates the Direwolf configuration file with the new comment.
        :param message: The new comment to set in the Direwolf configuration file.
        :return: True if the configuration was updated successfully, False otherwise.
        """
        try:
            with open(self.config_path) as file:
                lines = file.readlines()

            found = False
            for i, line in enumerate(lines):
                if line.startswith("PBEACON"):
                    lines[i] = self._create_beacon_line(message)
                    found = True
                    break

            if not found:
                print("PBEACON line not found in the configuration file.")
                return False

            with open(self.config_path, "w") as file:
                file.writelines(lines)

            return True
        except FileNotFoundError:
            print("Configuration file not found.")
            return False
        except Exception as e:
            print(f"Error updating configuration: {e}")
            return False

    def restart_direwolf(self):
        subprocess.run(["pkill", "-f", "direwolf"], check=False)  # Try to stop Direwolf
        time.sleep(2)  # Wait for a moment to ensure the process has terminated
        subprocess.Popen(
            ["direwolf"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )  # Start Direwolf again

    def _send_message_worker(self, message: TransmitterDataPacket) -> None:
        """
        When sending a message we sleep to give the transceiver time to start transmitting. We then
        pull the PTT pin low to start the transmission. We then sleep for the duration of the
        transmission before pulling the PTT pin high to stop the transmission. Because sleeping is
        blocking, we run this in a separate thread.
        :param message: The message to send.
        """

        # self.setup_gpio()
        config_path = DIREWOLF_CONFIG_PATH

        # if not self._update_beacon_comment(message):
        #     print("Failed to update the configuration. Message not sent.")
        #     return

        if self._update_beacon_comment(message):
            for i in range(NUMBER_OF_TRANSMISSIONS):
                # print("Configuration updated successfully.")
                self.pull_pin_high()  # Activate PTT via GPIO pin pull-down
                self.restart_direwolf()

                time.sleep(
                    TRANSMISSION_WINDOW_SECONDS
                )  # Duration for which the pin should remain low

                self.pull_pin_low()  # Deactivate PTT via GPIO pin pull-up
                # print("Transmission complete. Pin reset.")
                subprocess.run(["pkill", "-f", "direwolf"], check=False)  # Try to stop Direwolf

                time.sleep(TRANSMISSION_DELAY)

        else:
            print("Failed to update the configuration. Please check the file and try again.")

    def start(self) -> None:
        """
        Starts the transmitter.
        """
        pass

    def stop(self) -> None:
        """
        Cleans up the GPIO pins when the transmitter is stopped.
        """

        self.pull_pin_low()  # Deactivate PTT via GPIO pin pull-up

        try:
            subprocess.run(["pkill", "-f", "direwolf"], check=True)  # Stop Direwolf if running
        except subprocess.CalledProcessError as e:
            if e.returncode == 1:
                print("Direwolf is not running. Nothing to kill.")
            else:
                print(f"Error while stopping Direwolf: {e}")

        self._stop_event.set()

        if self.message_worker_thread:
            self.message_worker_thread.join(5)

        # GPIO.cleanup()

        print("Stopped Transmitter")

    def send_message(self, message: TransmitterDataPacket) -> None:
        """
        Sends a message to the ground station.
        """
        self.message_worker_thread = threading.Thread(
            target=self._send_message_worker, args=(message,)
        )
        self.message_worker_thread.start()
