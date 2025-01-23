import re
import subprocess
import threading
import time
import RPi.GPIO as GPIO

class SA_Transceiver:

    def __init__(self, gpio_pin, config_path):
        self.gpio_pin = gpio_pin
        self.config_path = config_path
        GPIO.setmode(GPIO.BCM)  # Use Broadcom pin-numbering scheme
        GPIO.setup(self.gpio_pin, GPIO.OUT,
                   initial=GPIO.HIGH)  # Set pin as output, initially high

    def _pull_pin_low(self):
        GPIO.output(self.gpio_pin, GPIO.LOW)  # Pull the pin low

    def _pull_pin_high(self):
        GPIO.output(self.gpio_pin, GPIO.HIGH)  # Pull the pin high

    def _update_beacon_comment(self, new_comment):
        try:
            with open(self.config_path, 'r') as file:
                lines = file.readlines()

            found = False
            for i, line in enumerate(lines):
                if line.startswith('PBEACON'):
                    lines[i] = re.sub(r'comment="[^"]*"', f'comment="{new_comment}"', line)
                    found = True
                    break

            if not found:
                print("PBEACON line not found in the configuration file.")
                return False

            with open(self.config_path, 'w') as file:
                file.writelines(lines)

            return True
        except FileNotFoundError:
            print("Configuration file not found.")
            return False
        except Exception as e:
            print(f"Error updating configuration: {e}")
            return False

    def _send_message_worker(self, message):
        if not self._update_beacon_comment(message):
            print("Failed to update the configuration. Message not sent.")
            return

        self._pull_pin_low()  # Activate PTT via GPIO pin pull-down

        subprocess.run(['pkill', '-f', 'direwolf'], check=False)  # Stop Direwolf if running
        time.sleep(2)  # Wait for a moment to ensure process termination
        subprocess.Popen(['direwolf'])  # Start Direwolf

        time.sleep(5)  # Keep the pin low for the transmission duration
        self._pull_pin_high()  # Deactivate PTT via GPIO pin pull-up
        print("Transmission complete. Pin reset.")

        subprocess.run(['pkill', '-f', 'direwolf'], check=False)  # Stop Direwolf

    def stop(self):
        GPIO.cleanup()

    def send_message(self, message):
        threading.Thread(target=self._send_message_worker, args=(message,), daemon=True).start()
