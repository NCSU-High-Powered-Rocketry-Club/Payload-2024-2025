"""Module for the Transmitter class that controls the SA85 transceiver."""

import re
import subprocess
import threading
import time

from gpiozero import OutputDevice
from payload.interfaces.base_transmitter import BaseTransmitter


class Transmitter(BaseTransmitter):
    """
    This is the class that controls the SA85 transceiver. It is responsible for sending messages
    to our ground station.
    """

    __slots__ = ("_stop_event", "config_path", "transmitter_pin", "message_worker_thread")

    def __init__(self, gpio_pin, config_path) -> None:
        """
        Initializes the transmitter with the specified GPIO pin and Direwolf configuration file
        path.
        :param gpio_pin: The GPIO pin number that is connected to the PTT pin of the transceiver.
        :param config_path: The path to the Direwolf configuration file.
        """
        # Sets the GPIO pin to be an output pin and has it start set high (inactive).
        self.transmitter_pin = OutputDevice(gpio_pin, initial_value=True)
        self.config_path = config_path
        self._stop_event = threading.Event()
        self.message_worker_thread = None

    def _pull_pin_low(self) -> None:
        """
        Pulls the GPIO pin low. This activates the PTT (Push-To-Talk) of the transceiver.
        """
        # Pull the pin low, means setting it to 0V
        self.transmitter_pin.off()

    def _pull_pin_high(self) -> None:
        """
        Pulls the GPIO pin high. This deactivates the PTT (Push-To-Talk) of the transceiver.
        """
        # Pull the pin high, means setting it to 3.3V (I think? Maybe 5V?)
        self.transmitter_pin.on()

    def _update_beacon_comment(self, new_comment: str) -> bool:
        """
        Updates the Direwolf configuration file with the new comment.
        :param new_comment: The new comment to set in the Direwolf configuration file.
        """
        try:
            with open(self.config_path) as file:
                lines = file.readlines()

            found = False
            for i, line in enumerate(lines):
                if line.startswith("PBEACON"):
                    lines[i] = re.sub(r'comment="[^"]*"', f'comment="{new_comment}"', line)
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

    def _send_message_worker(self, message: str) -> None:
        """
        Handles the message transmission process in a separate thread.
        """
        if not self._update_beacon_comment(message):
            print("Failed to update the configuration. Message not sent.")
            return

        subprocess.Popen(["direwolf"], stdout=subprocess.DEVNULL)  # Start Direwolf
        time.sleep(2)
        for i in range(20):
            if self._stop_event.is_set():
                self._pull_pin_high()  # Deactivate PTT via GPIO pin pull-up
                break
            self._pull_pin_low()  # Activate PTT via GPIO pin pull-down

            time.sleep(5)  # Keep the pin low for the transmission duration

            if self._stop_event.is_set():
                break

            self._pull_pin_high()  # Deactivate PTT via GPIO pin pull-up

            time.sleep(5)  # Keep the pin low for the transmission duration

        self._pull_pin_high()  # Deactivate PTT via GPIO pin pull-up

    def start(self) -> None:
        """
        Starts the transmitter.
        """
        raise NotImplementedError("Not implemented yet")

    def stop(self) -> None:
        """
        Stops the transmitter and cleans up GPIO resources.
        """
        self._pull_pin_high()
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
        print("Stopped Transmitter")

    def send_message(self, message: str) -> None:
        """
        Sends a message to the ground station.
        """
        self.message_worker_thread = threading.Thread(
            target=self._send_message_worker, args=(message,)
        )
        self.message_worker_thread.start()
