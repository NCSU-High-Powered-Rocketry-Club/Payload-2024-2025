import board
import busio
import adafruit_pca9685


MAX_DUTY_CYCLE = 0xffff


# Since the driver has a very fine 16-bit hex range,
# this function corrects for that so you can use 0 - 1 range
def floatToPWMHex(inputValue: float) -> int:
    # Input should be between 0 - 1
    return int(inputValue * MAX_DUTY_CYCLE)


# The channel of the driver to produce PWM signals from (0-15)
PWM_CHANNEL_ID = 0

# PWM Frequency, in Hz. The Arduino Uno runs at about 490 Hz
PWM_FREQUENCY = 490


class PwmDriver:

    def __init__(self):
        i2c = busio.I2C(board.SCL, board.SDA)
        self.pwm_driver = adafruit_pca9685.PCA9685(i2c)
        self.pwm_driver.frequency = PWM_FREQUENCY

        self.channel = self.pwm_driver.channels[PWM_CHANNEL_ID]

    def setDutyCycle(self, value: float):
        self.channel.duty_cycle = floatToPWMHex(value)
