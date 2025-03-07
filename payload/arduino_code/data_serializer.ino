#include <Wire.h>
#include <Adafruit_DPS310.h>
#include <Adafruit_BNO08x.h>
#include <SparkFun_u-blox_GNSS_v3.h>  // GNSS Library for SAM-M10Q

#define SEALEVEL_PRESSURE_HPA 1013.25f
#define VOLTAGE_PIN 35         // ADC pin for battery voltage
#define SENSOR_TIMEOUT 50      // Reduced timeout for faster operation
#define MAX_IMU_ATTEMPTS 40    // Reduced max attempts
#define LED_PIN 2              // ESP32's onboard LED
#define LED_INTERVAL 500       // LED blink interval in milliseconds

// Debug settings - Set to 0 for max speed
#define DEBUG_MODE 0           // Set to 1 for human-readable output, 0 for binary only
#define DEBUG_SERIAL Serial    // Which serial port to use for debug output
#define PACKET_START_MARKER1 0xAA
#define PACKET_START_MARKER2 0x55

// Sensor objects
Adafruit_DPS310 dps;
Adafruit_BNO08x bno08x(-1);
SFE_UBLOX_GNSS myGNSS;
static const uint8_t PACKET_START_MARKER[] = {0xFF, 0xFE, 0xFD, 0xFC};

// Add a global boolean flag for bad data detection
bool badIMUDataDetected = false;
uint8_t status_flags = 0;

// Data packet structure - UNTOUCHED as requested
struct DataPacket {
  float timestamp;
  float voltage;
  float temperature;
  float pressure;
  float altitude;
  float comp_accel_x, comp_accel_y, comp_accel_z;
  float gyro_x, gyro_y, gyro_z;
  float magnetic_x, magnetic_y, magnetic_z;
  float quat_w, quat_x, quat_y, quat_z;
  float gps_lat, gps_long, gps_alt;
  // uint8_t status_flags;  // Bit flags to indicate which sensors provided valid data
};

// Status flag bits
#define STATUS_DPS310_OK    0x01
#define STATUS_BNO08X_ACCEL 0x02
#define STATUS_BNO08X_GYRO  0x04
#define STATUS_BNO08X_ROT   0x08
#define STATUS_GPS_OK       0x10
#define STATUS_BNO08X_MAG   0x20

// LED variables
static unsigned long lastLedToggle = 0;
static bool ledState = false;

// Faster LED update - simplified
inline void updateHeartbeatLED() {
  const unsigned long currentMillis = millis();
  if (currentMillis - lastLedToggle >= LED_INTERVAL) {
    lastLedToggle = currentMillis;
    ledState = !ledState;
    digitalWrite(LED_PIN, ledState);
  }
}

// Only compile debug function if needed
#if DEBUG_MODE
void printHumanReadableData(const DataPacket &data) {
  DEBUG_SERIAL.println("\n------ SENSOR DATA ------");
  DEBUG_SERIAL.print("BAD IMU DATA DETECTED: ");
  DEBUG_SERIAL.println(badIMUDataDetected ? "YES" : "NO");
  DEBUG_SERIAL.print("Time: ");
  DEBUG_SERIAL.print(data.timestamp / 1000.0, 2);
  DEBUG_SERIAL.println(" sec");

  DEBUG_SERIAL.print("Battery: ");
  DEBUG_SERIAL.print(data.voltage, 2);
  DEBUG_SERIAL.println(" V");

  DEBUG_SERIAL.println("\n- Environmental -");
  if (status_flags & STATUS_DPS310_OK) {
    DEBUG_SERIAL.print("Temperature: ");
    DEBUG_SERIAL.print(data.temperature, 1);
    DEBUG_SERIAL.println(" °C");

    DEBUG_SERIAL.print("Pressure: ");
    DEBUG_SERIAL.print(data.pressure, 1);
    DEBUG_SERIAL.println(" hPa");

    DEBUG_SERIAL.print("Altitude: ");
    DEBUG_SERIAL.print(data.altitude, 1);
    DEBUG_SERIAL.println(" m");
  } else {
    DEBUG_SERIAL.println("DPS310 data unavailable");
  }

  DEBUG_SERIAL.println("\n- Motion -");
  if (status_flags & STATUS_BNO08X_ACCEL) {
    DEBUG_SERIAL.print("Acceleration (m/s²): X=");
    DEBUG_SERIAL.print(data.comp_accel_x, 2);
    DEBUG_SERIAL.print(" Y=");
    DEBUG_SERIAL.print(data.comp_accel_y, 2);
    DEBUG_SERIAL.print(" Z=");
    DEBUG_SERIAL.println(data.comp_accel_z, 2);
  } else {
    DEBUG_SERIAL.println("Acceleration data unavailable");
  }

  if (status_flags & STATUS_BNO08X_GYRO) {
    DEBUG_SERIAL.print("Gyroscope (rad/s): X=");
    DEBUG_SERIAL.print(data.gyro_x, 2);
    DEBUG_SERIAL.print(" Y=");
    DEBUG_SERIAL.print(data.gyro_y, 2);
    DEBUG_SERIAL.print(" Z=");
    DEBUG_SERIAL.println(data.gyro_z, 2);
  } else {
    DEBUG_SERIAL.println("Gyroscope data unavailable");
  }

  if (status_flags & STATUS_BNO08X_ROT) {
    DEBUG_SERIAL.print("Quaternion: W=");
    DEBUG_SERIAL.print(data.quat_w, 3);
    DEBUG_SERIAL.print(" X=");
    DEBUG_SERIAL.print(data.quat_x, 3);
    DEBUG_SERIAL.print(" Y=");
    DEBUG_SERIAL.print(data.quat_y, 3);
    DEBUG_SERIAL.print(" Z=");
    DEBUG_SERIAL.println(data.quat_z, 3);
  } else {
    DEBUG_SERIAL.println("Orientation data unavailable");
  }

  if (status_flags & STATUS_BNO08X_MAG) {
    DEBUG_SERIAL.print("Magnetometer: X=");
    DEBUG_SERIAL.print(data.magnetic_x, 3);
    DEBUG_SERIAL.print(" Y=");
    DEBUG_SERIAL.print(data.magnetic_y, 3);
    DEBUG_SERIAL.print(" Z =");
    DEBUG_SERIAL.println(data.magnetic_z, 3);
  } else {
    DEBUG_SERIAL.println("Magnetometer data unavailable");
  }

  DEBUG_SERIAL.println("\n- Location -");
  if (status_flags & STATUS_GPS_OK) {
    DEBUG_SERIAL.print("GPS: Lat=");
    DEBUG_SERIAL.print(data.gps_lat, 6);
    DEBUG_SERIAL.print(" Lon=");
    DEBUG_SERIAL.print(data.gps_long, 6);
    DEBUG_SERIAL.print(" Alt=");
    DEBUG_SERIAL.print(data.gps_alt, 1);
    DEBUG_SERIAL.println(" m");
  } else {
    DEBUG_SERIAL.println("GPS data unavailable");
  }

  DEBUG_SERIAL.println("\n- Status Summary -");
  DEBUG_SERIAL.print("Status flags: 0x");
  DEBUG_SERIAL.println(status_flags, HEX);
  DEBUG_SERIAL.print("SIZE OF DATA: ");
  DEBUG_SERIAL.println(sizeof(data));
  DEBUG_SERIAL.println("--------------------------\n");
}
#endif

void setup() {
  Serial.begin(115200);
  // Reduced wait time for serial
  unsigned long startTime = millis();
  while (!Serial && (millis() - startTime < 1000)) { delay(10); }

  // Setup LED for heartbeat
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);

  #if DEBUG_MODE
  DEBUG_SERIAL.println("Sensor System Starting");
  #endif

  // Faster I2C clock
  Wire.begin();
  Wire.setClock(800000UL);  // Increase to 800kHz for ESP32

  // Initialize DPS310 with minimal checks
  if (dps.begin_I2C(0x77) || dps.begin_I2C(0x76)) {
    #if DEBUG_MODE
    DEBUG_SERIAL.println("DPS310 initialized.");
    #endif
    dps.configurePressure(DPS310_64HZ, DPS310_16SAMPLES);  // Lower samples for faster reads
    dps.configureTemperature(DPS310_64HZ, DPS310_16SAMPLES);
    dps.setMode(DPS310_CONT_PRESTEMP);
  }

  // Initialize BNO085 IMU with faster reporting rates
  if (bno08x.begin_I2C()) {
    #if DEBUG_MODE
    DEBUG_SERIAL.println("BNO08x IMU initialized.");
    #endif
    // More frequent reports (microseconds)
    bno08x.enableReport(SH2_ROTATION_VECTOR, 10000);
    bno08x.enableReport(SH2_LINEAR_ACCELERATION, 10000);
    bno08x.enableReport(SH2_GYROSCOPE_CALIBRATED, 10000);
    bno08x.enableReport(SH2_MAGNETIC_FIELD_CALIBRATED, 20000);
  }

  // Initialize GPS with minimal checks
  if (myGNSS.begin()) {
    #if DEBUG_MODE
    DEBUG_SERIAL.println("GPS initialized.");
    #endif
    myGNSS.setI2COutput(COM_TYPE_UBX);
    myGNSS.setNavigationFrequency(10);  // Set higher rate (10Hz)
  }

  // ADC setup
  pinMode(VOLTAGE_PIN, INPUT);
  analogReadResolution(12);
  analogSetAttenuation(ADC_11db);
}

// Define threshold constants for filtering
#define MAX_ACCEL_VALUE 3.0f      // Maximum acceptable acceleration (m/s²)
#define MAX_GYRO_VALUE 10.0f       // Maximum acceptable gyroscope value (rad/s)
#define MAX_MAG_VALUE 500.0f       // Maximum acceptable magnetometer value (uT)
#define MAX_QUAT_VALUE 1.0f        // Maximum acceptable quaternion value (should be <= 1.0)

unsigned long lastIMUResetTime = 0;
const unsigned long IMU_RESET_INTERVAL = 5000; // Only attempt reset every 5 seconds

// Optimized IMU data collection with filtering
inline void collectIMUData(DataPacket &packet) {
  // Track which sensor values we've received
  uint8_t executed_cases = 0;
  const uint8_t all_cases_executed = (STATUS_BNO08X_ACCEL | STATUS_BNO08X_GYRO | STATUS_BNO08X_ROT | STATUS_BNO08X_MAG);

  // Set timeout to ensure we don't get stuck
  unsigned long startTime = millis();
  int attempts = 0;
  bool attemptReset = false;

  // Try to get IMU data with timeout
  while ((executed_cases != all_cases_executed) &&
         (millis() - startTime < SENSOR_TIMEOUT) &&
         (attempts < MAX_IMU_ATTEMPTS)) {

    attempts++;
    sh2_SensorValue_t sensorValue;

    if (bno08x.getSensorEvent(&sensorValue)) {
      switch (sensorValue.sensorId) {
        case SH2_LINEAR_ACCELERATION:
          // Check for out-of-range values but don't zero them immediately
          if (abs(sensorValue.un.linearAcceleration.x) > MAX_ACCEL_VALUE ||
              abs(sensorValue.un.linearAcceleration.y) > MAX_ACCEL_VALUE ||
              abs(sensorValue.un.linearAcceleration.z) > MAX_ACCEL_VALUE) {
            badIMUDataDetected = true;
            #if DEBUG_MODE
            DEBUG_SERIAL.print("Bad accel data: ");
            DEBUG_SERIAL.print(sensorValue.un.linearAcceleration.x);
            DEBUG_SERIAL.print(", ");
            DEBUG_SERIAL.print(sensorValue.un.linearAcceleration.y);
            DEBUG_SERIAL.print(", ");
            DEBUG_SERIAL.println(sensorValue.un.linearAcceleration.z);
            #endif
            // Use last cycle's values or acceptable range
            packet.comp_accel_x = constrain(sensorValue.un.linearAcceleration.x, -MAX_ACCEL_VALUE, MAX_ACCEL_VALUE);
            packet.comp_accel_y = constrain(sensorValue.un.linearAcceleration.y, -MAX_ACCEL_VALUE, MAX_ACCEL_VALUE);
            packet.comp_accel_z = constrain(sensorValue.un.linearAcceleration.z, -MAX_ACCEL_VALUE, MAX_ACCEL_VALUE);
          } else {
            packet.comp_accel_x = sensorValue.un.linearAcceleration.x;
            packet.comp_accel_y = sensorValue.un.linearAcceleration.y;
            packet.comp_accel_z = sensorValue.un.linearAcceleration.z;
          }
          executed_cases |= STATUS_BNO08X_ACCEL;
          break;

        case SH2_GYROSCOPE_CALIBRATED:
          if (abs(sensorValue.un.gyroscope.x) > MAX_GYRO_VALUE ||
              abs(sensorValue.un.gyroscope.y) > MAX_GYRO_VALUE ||
              abs(sensorValue.un.gyroscope.z) > MAX_GYRO_VALUE) {
            badIMUDataDetected = true;
            #if DEBUG_MODE
            DEBUG_SERIAL.print("Bad gyro data: ");
            DEBUG_SERIAL.print(sensorValue.un.gyroscope.x);
            DEBUG_SERIAL.print(", ");
            DEBUG_SERIAL.print(sensorValue.un.gyroscope.y);
            DEBUG_SERIAL.print(", ");
            DEBUG_SERIAL.println(sensorValue.un.gyroscope.z);
            #endif
            // Use constrained values instead of zeros
            packet.gyro_x = constrain(sensorValue.un.gyroscope.x, -MAX_GYRO_VALUE, MAX_GYRO_VALUE);
            packet.gyro_y = constrain(sensorValue.un.gyroscope.y, -MAX_GYRO_VALUE, MAX_GYRO_VALUE);
            packet.gyro_z = constrain(sensorValue.un.gyroscope.z, -MAX_GYRO_VALUE, MAX_GYRO_VALUE);
          } else {
            packet.gyro_x = sensorValue.un.gyroscope.x;
            packet.gyro_y = sensorValue.un.gyroscope.y;
            packet.gyro_z = sensorValue.un.gyroscope.z;
          }
          executed_cases |= STATUS_BNO08X_GYRO;
          break;

        case SH2_ROTATION_VECTOR:
          if (abs(sensorValue.un.rotationVector.i) > MAX_QUAT_VALUE ||
              abs(sensorValue.un.rotationVector.j) > MAX_QUAT_VALUE ||
              abs(sensorValue.un.rotationVector.k) > MAX_QUAT_VALUE ||
              abs(sensorValue.un.rotationVector.real) > MAX_QUAT_VALUE) {
            badIMUDataDetected = true;
            #if DEBUG_MODE
            DEBUG_SERIAL.print("Bad quat data: ");
            DEBUG_SERIAL.print(sensorValue.un.rotationVector.i);
            DEBUG_SERIAL.print(", ");
            DEBUG_SERIAL.print(sensorValue.un.rotationVector.j);
            DEBUG_SERIAL.print(", ");
            DEBUG_SERIAL.print(sensorValue.un.rotationVector.k);
            DEBUG_SERIAL.print(", ");
            DEBUG_SERIAL.println(sensorValue.un.rotationVector.real);
            #endif
            // Normalize quaternion instead of resetting to identity
            float norm = sqrt(
              sensorValue.un.rotationVector.i * sensorValue.un.rotationVector.i +
              sensorValue.un.rotationVector.j * sensorValue.un.rotationVector.j +
              sensorValue.un.rotationVector.k * sensorValue.un.rotationVector.k +
              sensorValue.un.rotationVector.real * sensorValue.un.rotationVector.real
            );
            
            if (norm > 0) {
              packet.quat_x = sensorValue.un.rotationVector.i / norm;
              packet.quat_y = sensorValue.un.rotationVector.j / norm;
              packet.quat_z = sensorValue.un.rotationVector.k / norm;
              packet.quat_w = sensorValue.un.rotationVector.real / norm;
            } else {
              // If normalization fails, use identity quaternion
              packet.quat_x = 0.0f;
              packet.quat_y = 0.0f;
              packet.quat_z = 0.0f;
              packet.quat_w = 1.0f;
            }
          } else {
            packet.quat_x = sensorValue.un.rotationVector.i;
            packet.quat_y = sensorValue.un.rotationVector.j;
            packet.quat_z = sensorValue.un.rotationVector.k;
            packet.quat_w = sensorValue.un.rotationVector.real;
          }
          executed_cases |= STATUS_BNO08X_ROT;
          break;

        case SH2_MAGNETIC_FIELD_CALIBRATED:
          if (abs(sensorValue.un.magneticField.x) > MAX_MAG_VALUE ||
              abs(sensorValue.un.magneticField.y) > MAX_MAG_VALUE ||
              abs(sensorValue.un.magneticField.z) > MAX_MAG_VALUE) {
            badIMUDataDetected = true;
            #if DEBUG_MODE
            DEBUG_SERIAL.print("Bad mag data: ");
            DEBUG_SERIAL.print(sensorValue.un.magneticField.x);
            DEBUG_SERIAL.print(", ");
            DEBUG_SERIAL.print(sensorValue.un.magneticField.y);
            DEBUG_SERIAL.print(", ");
            DEBUG_SERIAL.println(sensorValue.un.magneticField.z);
            #endif
            // Use constrained values instead of zeros
            packet.magnetic_x = constrain(sensorValue.un.magneticField.x, -MAX_MAG_VALUE, MAX_MAG_VALUE);
            packet.magnetic_y = constrain(sensorValue.un.magneticField.y, -MAX_MAG_VALUE, MAX_MAG_VALUE);
            packet.magnetic_z = constrain(sensorValue.un.magneticField.z, -MAX_MAG_VALUE, MAX_MAG_VALUE);
          } else {
            packet.magnetic_x = sensorValue.un.magneticField.x;
            packet.magnetic_y = sensorValue.un.magneticField.y;
            packet.magnetic_z = sensorValue.un.magneticField.z;
          }
          executed_cases |= STATUS_BNO08X_MAG;
          break;
      }
    } else {
      // If we can't get any sensor events, consider attempting a reset
      attemptReset = true;
    }
  }

  // Only attempt to reset if we couldn't get any sensor values
  // and enough time has passed since the last reset
  if (attemptReset && (executed_cases == 0) && 
      (millis() - lastIMUResetTime >= IMU_RESET_INTERVAL)) {
    #if DEBUG_MODE
    DEBUG_SERIAL.println("IMU not responding - attempting reset");
    #endif
    
    // Re-initialize BNO085
    if (bno08x.begin_I2C()) {
      #if DEBUG_MODE
      DEBUG_SERIAL.println("BNO08x IMU reinitialized successfully.");
      #endif
      // More frequent reports (microseconds)
      bno08x.enableReport(SH2_ROTATION_VECTOR, 10000);
      bno08x.enableReport(SH2_LINEAR_ACCELERATION, 10000);
      bno08x.enableReport(SH2_GYROSCOPE_CALIBRATED, 10000);
      bno08x.enableReport(SH2_MAGNETIC_FIELD_CALIBRATED, 20000);
      lastIMUResetTime = millis();
    } else {
      #if DEBUG_MODE
      DEBUG_SERIAL.println("BNO08x IMU reset failed.");
      #endif
    }
  }

  // Update status flags with what we got
  status_flags |= executed_cases;
}

void loop() {
  // Update heartbeat LED
  updateHeartbeatLED();

  // Initialize data packet
  DataPacket data = {0};
  data.timestamp = millis();
  status_flags = 0;

  // Read battery voltage - direct calculation without filtering
  data.voltage = (analogRead(VOLTAGE_PIN) * 3.3) / 64.0;

  // Read DPS310 with shorter timeout
  sensors_event_t temp_event, pressure_event;
  if (dps.getEvents(&temp_event, &pressure_event)) {
    data.temperature = temp_event.temperature;
    data.pressure = pressure_event.pressure;
    data.altitude = 44330.0 * (1.0 - pow(data.pressure / SEALEVEL_PRESSURE_HPA, 0.1903));
    status_flags |= STATUS_DPS310_OK;
  }

  // Get GPS data with shorter timeout
  if (myGNSS.getPVT(SENSOR_TIMEOUT)) {
    data.gps_lat = myGNSS.getLatitude() / 10000000.0;
    data.gps_long = myGNSS.getLongitude() / 10000000.0;
    data.gps_alt = myGNSS.getAltitudeMSL() / 1000.0;
    status_flags |= STATUS_GPS_OK;
  }

  // Collect IMU data
  collectIMUData(data);

  // Transmit binary data - check only once for available space
  if (Serial.availableForWrite() >= sizeof(data) + sizeof(PACKET_START_MARKER)) {
    Serial.write(PACKET_START_MARKER, sizeof(PACKET_START_MARKER));
    Serial.write((byte*)&data, sizeof(data));
  }

  // Only print debug if enabled
  #if DEBUG_MODE
  printHumanReadableData(data);
  #endif

  // No delay at end of loop for maximum speed
}