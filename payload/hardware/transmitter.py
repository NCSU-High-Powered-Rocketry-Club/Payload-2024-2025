import re
import subprocess
import threading
import time


try:
    from RPi import GPIO
except ImportError:
    pass


class Transmitter:
    """
    This is the class that controls the SA858 transceiver. It is responsible for sending messages
    to our ground station.
    """

    def __init__(self, gpio_pin, config_path) -> None:
        """
        Initializes the transmitter with the specified GPIO pin and Direwolf configuration file
        path.
        :param gpio_pin: The GPIO pin number that is connected to the PTT pin of the transceiver.
        :param config_path: The path to the Direwolf configuration file.
        """
        self.gpio_pin = gpio_pin
        self.config_path = config_path
        GPIO.setmode(GPIO.BCM)  # Use Broadcom pin-numbering scheme
        GPIO.setup(self.gpio_pin, GPIO.OUT, initial=GPIO.HIGH)  # Set pin as output, initially high

    def _pull_pin_low(self) -> None:
        """
        Pulls the GPIO pin low. This activates the PTT (Push-To-Talk) of the transceiver.
        """
        GPIO.output(self.gpio_pin, GPIO.LOW)  # Pull the pin low

    def _pull_pin_high(self) -> None:
        """
        Pulls the GPIO pin high. This deactivates the PTT (Push-To-Talk) of the transceiver.
        """
        GPIO.output(self.gpio_pin, GPIO.HIGH)  # Pull the pin high

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
        When sending a message we sleep to give the transceiver time to start transmitting. We then
        pull the PTT pin low to start the transmission. We then sleep for the duration of the
        transmission before pulling the PTT pin high to stop the transmission. Because sleeping is
        blocking, we run this in a separate thread.
        :param message: The message to send.
        """
        if not self._update_beacon_comment(message):
            print("Failed to update the configuration. Message not sent.")
            return

        self._pull_pin_low()  # Activate PTT via GPIO pin pull-down

        subprocess.run(["pkill", "-f", "direwolf"], check=False)  # Stop Direwolf if running
        time.sleep(2)  # Wait for a moment to ensure process termination
        subprocess.Popen(["direwolf"])  # Start Direwolf

        time.sleep(5)  # Keep the pin low for the transmission duration
        self._pull_pin_high()  # Deactivate PTT via GPIO pin pull-up
        print("Transmission complete. Pin reset.")

        subprocess.run(["pkill", "-f", "direwolf"], check=False)  # Stop Direwolf

    def stop(self) -> None:
        """
        Cleans up the GPIO pins when the transmitter is stopped.
        """
        GPIO.cleanup()

    def send_message(self, message: str) -> None:
        """
        Sends a message to the ground station.
        """
        threading.Thread(target=self._send_message_worker, args=(message,), daemon=True).start()
