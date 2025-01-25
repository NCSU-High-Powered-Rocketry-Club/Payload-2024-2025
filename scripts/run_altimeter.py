import time
import board
from adafruit_bmp280 import Adafruit_BMP280_I2C

# Create I2C bus
i2c = board.I2C()

# Create BMP280 object
bmp280 = Adafruit_BMP280_I2C(i2c)


# Function to log data
with open("sensor_data.log", "w+") as log_file:
    while True:
        temperature = bmp280.temperature
        pressure = bmp280.pressure
        log_file.write(
            f"Temperature: {temperature:.2f} C, Pressure: {pressure:.2f} hPa\n"
        )
        log_file.flush()
        time.sleep(1)
