import smbus2
import time

# Define I2C bus and address
I2C_BUS = 1  # Use the appropriate I2C bus (e.g., 1 for Raspberry Pi)
SAM_M10Q_ADDRESS = 0x42  # SAM M10Q default I2C address

# Initialize I2C
bus = smbus2.SMBus(I2C_BUS)

def read_gps_data():
    try:
        # Continuously read data from the SAM M10Q
        data = ""
        while True:
            # Read 32 bytes at a time from the GPS module
            bytes_data = bus.read_i2c_block_data(SAM_M10Q_ADDRESS, 0x00, 1)
            # Convert bytes to ASCII characters and append to the data string
            data += ''.join(chr(b) for b in bytes_data if b != 0x00)
            
            # Split data into sentences using newline
            sentences = data.split('\n')
            
            # Process complete sentences
            for sentence in sentences[:-1]:
                # Check for GGA or RMC sentence types, which contain location data
                if sentence.startswith('$GNGGA') or sentence.startswith('$GNRMC'):
                    print(f"Received NMEA Sentence: {sentence}")
                    parse_nmea_sentence(sentence)
            
            # Keep the last incomplete sentence
            data = sentences[-1]
            
            # Wait a bit before reading again
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("Stopped by User")
    finally:
        bus.close()

def parse_nmea_sentence(sentence):
    fields = sentence.split(',')
    if sentence.startswith('$GNGGA'):
        # Parse GGA sentence
        latitude = nmea_to_decimal(fields[2], fields[3])
        longitude = nmea_to_decimal(fields[4], fields[5])
        print(f"Latitude: {latitude}, Longitude: {longitude}")
    elif sentence.startswith('$GNRMC'):
        # Parse RMC sentence
        latitude = nmea_to_decimal(fields[3], fields[4])
        longitude = nmea_to_decimal(fields[5], fields[6])
        print(f"Latitude: {latitude}, Longitude: {longitude}")

def nmea_to_decimal(value, direction):
    # Convert NMEA format (DDMM.MMMM) to decimal degrees
    if not value:
        return None
    degrees = float(value[:2])
    minutes = float(value[2:]) / 60
    decimal = degrees + minutes
    if direction == 'S' or direction == 'W':
        decimal = -decimal
    return decimal

# Run the GPS data read function
read_gps_data()
