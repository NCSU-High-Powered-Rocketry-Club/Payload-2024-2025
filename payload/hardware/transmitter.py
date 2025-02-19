"""Module for the Transmitter class that controls the SA85 transceiver."""

import subprocess
import threading
import time

from gpiozero import OutputDevice

from payload.data_handling.packets.transmitter_data_packet import TransmitterDataPacket
from payload.interfaces.base_transmitter import BaseTransmitter


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

    def _update_beacon_comment(self, new_comment: str, lat: float, long: float) -> bool:
        """
        Updates the Direwolf configuration file with the new comment.
        :param new_comment: The new comment to set in the Direwolf configuration file.
        :param lat: The latitude of the landing site.
        :param long: The longitude of the landing site.
        """
        try:
            # Read the existing configuration file
            with self.config_path.open() as file:
                lines = file.readlines()

            found = False
            for i, line in enumerate(lines):
                if line.startswith("PBEACON"):
                    # Split the line into parts (words)
                    parts = line.strip().split()

                    # Find and update the comment field
                    updated_parts = []
                    for part in parts:
                        if part.startswith("comment="):
                            # Replace the comment value, keeping the "comment=" prefix
                            updated_parts.append(f'comment="{new_comment}"')
                        elif part.startswith("lat="):
                            # Update latitude, formatting it to match APRS format (DD^MM.MM)
                            lat_deg = int(lat)
                            lat_min = (lat - lat_deg) * 60
                            lat_str = f"{lat_deg:02d}^{lat_min:05.2f}N"
                            updated_parts.append(f"lat={lat_str}")
                        elif part.startswith("long="):
                            # Update longitude, formatting it to match APRS format (DDD^MM.MM)
                            long_deg = int(long)
                            long_min = (long - long_deg) * 60
                            long_str = f"{long_deg:03d}^{long_min:05.2f}W"
                            updated_parts.append(f"long={long_str}")
                        else:
                            updated_parts.append(part)

                    # Reconstruct the line
                    lines[i] = " ".join(updated_parts) + "\n"
                    found = True
                    break

            if not found:
                print("PBEACON line not found in the configuration file.")
                return False

            # Write the updated configuration back to the file
            with self.config_path.open("w") as file:
                file.writelines(lines)

            return True
        except FileNotFoundError:
            print("Configuration file not found.")
            return False
        except Exception as e:
            print(f"Error updating configuration: {e}")
            return False

    def _send_message_worker(self, message: TransmitterDataPacket) -> None:
        """
        Handles the message transmission process in a separate thread.
        """
        lat, long = message.landing_coords
        compressed_message = message.compress_packet()

        if not self._update_beacon_comment(compressed_message, lat, long):
            print("Failed to update the configuration. Message not sent.")
            return

        subprocess.Popen(["direwolf"], stdout=subprocess.DEVNULL)  # Start Direwolf
        time.sleep(2)
        for _i in range(20):
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
