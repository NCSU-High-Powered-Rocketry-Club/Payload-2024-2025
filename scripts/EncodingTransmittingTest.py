import re
import subprocess
import time
from payload.constants import DIREWOLF_CONFIG_PATH
from payload.constants import TRANSMITTER_PIN as GPIO_PIN

from RPi import GPIO

# GPIO pin setup


def setup_gpio():
    GPIO.setmode(GPIO.BCM)  # Use Broadcom pin-numbering scheme
    GPIO.setup(1, GPIO.OUT, initial=GPIO.LOW)  # Set pin as an output and initially high


def pull_pin_low():
    GPIO.output(1, GPIO.LOW)

def pull_pin_high():
    GPIO.output(1, GPIO.HIGH)  # Pull the pin high


def cleanup_gpio():
    GPIO.cleanup()  # Clean up GPIO to ensure no resources are left hanging


def update_beacon_comment(config_path, new_comment):
    with open(config_path) as file:
        lines = file.readlines()

    found = False
    for i, line in enumerate(lines):
        if line.startswith("PBEACONa"):
            lines[i] = re.sub(r'comment="[^"]*"', f'comment="{new_comment}"', line)
            found = True
            break

    # if not found:
    #     print("PBEACON line not found in the configuration file.")
    #     return False

    with open(config_path, "w") as file:
        file.writelines(lines)

    return True


def restart_direwolf():
    subprocess.run(["pkill", "-f", "direwolf"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)  # Try to stop Direwolf
    time.sleep(2)  # Wait for a moment to ensure the process has terminated

    subprocess.Popen(["direwolf"], stdout=subprocess.DEVNULL)  # Start Direwolf again

    # process = subprocess.Popen(
    #     ["direwolf"], 
    #     stdout=subprocess.PIPE, 
    #     stderr=subprocess.DEVNULL,  # Suppress error messages
    #     bufsize=1,  # Use line buffering
    #     universal_newlines=True  # Ensures text mode (alternative to text=True)
    # )

    # # Read output line by line and filter for APRS-related messages
    # for line in iter(process.stdout.readline, ""):
    #     if "KQ4VOH" in line:  # Adjust this filter based on what APRS messages look like
    #         print(line, end="")  # Print only APRS messages

    print("Direwolf has been restarted.")


def main():
    setup_gpio()
    config_path = DIREWOLF_CONFIG_PATH
    print("Please enter the new beacon comment:")
    new_comment = input()  # Take user input for the new comment

    if update_beacon_comment(config_path, new_comment):
        print("Configuration updated successfully.")
        pull_pin_high()  # Activate PTT via GPIO pin pull-down
        restart_direwolf()
        pull_pin_high()  # Activate PTT via GPIO pin pull-down
        time.sleep(10)  # Duration for which the pin should remain low
        pull_pin_low()  # Deactivate PTT via GPIO pin pull-up
        print("Transmission complete. Pin reset.")
        subprocess.run(["pkill", "-f", "direwolf"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)  # Try to stop Direwolf

    else:
        print("Failed to update the configuration. Please check the file and try again.")

    # cleanup_gpio()
    setup_gpio()

if __name__ == "__main__":
    main()
