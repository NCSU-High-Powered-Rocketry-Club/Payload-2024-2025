import time
import board
import busio
import adafruit_dps310

# Initialize I2C bus and sensor
i2c = busio.I2C(board.SCL, board.SDA)
dps310 = adafruit_dps310.DPS310(i2c)

print("Reading DPS310 sensor data...")

try:
    while True:
        # Read temperature and pressure data
        temperature = dps310.temperature  # in degrees Celsius
        pressure = dps310.pressure        # in hPa

        # Display the data
        print(f"Temperature: {temperature:.2f} °C")
        print(f"Pressure: {pressure:.2f} hPa")
        print("-" * 40)

        time.sleep(1)  # Delay between readings

except KeyboardInterrupt:
    print("Test interrupted by user.")
except Exception as e:
    print(f"An error occurred: {e}")
