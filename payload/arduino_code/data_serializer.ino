#include <Wire.h>
#include <Adafruit_DPS310.h>
#include <Adafruit_BNO08x.h>
#include <SparkFun_u-blox_GNSS_v3.h>  // GNSS Library for SAM-M10Q

#define SEALEVEL_PRESSURE_HPA 1013.25f  
#define VOLTAGE_PIN 35         // ADC pin for battery voltage
#define SENSOR_TIMEOUT 300     // Timeout in milliseconds for sensor readings
#define MAX_IMU_ATTEMPTS 40    // Maximum attempts to read IMU data before moving on
#define LED_PIN 2              // ESP32's onboard LED pin (usually GPIO2)
#define LED_INTERVAL 500       // LED blink interval in milliseconds

// Debug settings
#define DEBUG_MODE 0           // Set to 1 for human-readable output, 0 for binary only
#define DEBUG_SERIAL Serial    // Which serial port to use for debug output
static const uint8_t PACKET_START_MARKER[] = {0xFF, 0xFE, 0xFD, 0xFC};  // New 4-byte packet marker

// Sensor objects
Adafruit_DPS310 dps;
Adafruit_BNO08x bno08x(-1);
SFE_UBLOX_GNSS myGNSS;

uint8_t status_flags = 0;

// Data packet structure
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
};

// Status flag bits
#define STATUS_DPS310_OK    0x01
#define STATUS_BNO08X_ACCEL 0x02
#define STATUS_BNO08X_GYRO  0x04
#define STATUS_BNO08X_ROT   0x08
#define STATUS_GPS_OK       0x10
#define STATUS_BNO08X_MAG   0x20

// Battery voltage filtering
static float filtBatteryVoltage = 0.0;
static unsigned long lastBattReadTime = 0;
static unsigned long lastLedToggle = 0;
static bool ledState = false;

// Function to update LED state - call this frequently
void updateHeartbeatLED() {
  unsigned long currentMillis = millis();
  if (currentMillis - lastLedToggle >= LED_INTERVAL) {
    lastLedToggle = currentMillis;
    ledState = !ledState;
    digitalWrite(LED_PIN, ledState);
  }
}

// Function to print human-readable data
void printHumanReadableData(const DataPacket &data) {
  if (!DEBUG_MODE) return;
  
  DEBUG_SERIAL.println("\n------ SENSOR DATA ------");
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
  DEBUG_SERIAL.print("DPS310: ");
  DEBUG_SERIAL.print((status_flags & STATUS_DPS310_OK) ? "OK" : "FAIL");
  DEBUG_SERIAL.print(" | Accel: ");
  DEBUG_SERIAL.print((status_flags & STATUS_BNO08X_ACCEL) ? "OK" : "FAIL");
  DEBUG_SERIAL.print(" | Gyro: ");
  DEBUG_SERIAL.print((status_flags & STATUS_BNO08X_GYRO) ? "OK" : "FAIL");
  DEBUG_SERIAL.print(" | Quat: ");
  DEBUG_SERIAL.print((status_flags & STATUS_BNO08X_ROT) ? "OK" : "FAIL");
  DEBUG_SERIAL.print(" | MAG: ");
  DEBUG_SERIAL.print((status_flags & STATUS_BNO08X_MAG) ? "OK" : "FAIL");
  DEBUG_SERIAL.print(" | GPS: ");
  DEBUG_SERIAL.println((status_flags & STATUS_GPS_OK) ? "OK" : "FAIL");
  DEBUG_SERIAL.print("SIZE OF DATA: ");
  DEBUG_SERIAL.println(sizeof(data));
  DEBUG_SERIAL.println("--------------------------\n");
}

void setup() {
  Serial.begin(115200);
  unsigned long startTime = millis();
  while (!Serial && (millis() - startTime < 5000)) { delay(10); }  // Wait for Serial with timeout
  
  // Setup LED for heartbeat
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);

  if (DEBUG_MODE) {
    DEBUG_SERIAL.println("\n=================================");
    DEBUG_SERIAL.println("Sensor System Starting");
    DEBUG_SERIAL.println("=================================");
    DEBUG_SERIAL.print("Debug mode: ");
    DEBUG_SERIAL.println(DEBUG_MODE ? "ENABLED" : "DISABLED");
    DEBUG_SERIAL.println("Initializing sensors...");
  }

  Wire.begin();
  Wire.setClock(400000UL);

  // Initialize DPS310 Pressure/Temperature Sensor
  if (!dps.begin_I2C(0x77) && !dps.begin_I2C(0x76)) {  
    if (DEBUG_MODE) DEBUG_SERIAL.println("** DPS310 not found! **");
  } else {
    if (DEBUG_MODE) DEBUG_SERIAL.println("DPS310 initialized.");
    dps.configurePressure(DPS310_64HZ, DPS310_64SAMPLES);
    dps.configureTemperature(DPS310_64HZ, DPS310_64SAMPLES);
    dps.setMode(DPS310_CONT_PRESTEMP);
  }

  updateHeartbeatLED();

  // Initialize BNO085 IMU
  if (bno08x.begin_I2C()) {
    if (DEBUG_MODE) DEBUG_SERIAL.println("BNO08x IMU initialized.");
    bno08x.enableReport(SH2_ROTATION_VECTOR);
    bno08x.enableReport(SH2_LINEAR_ACCELERATION);
    bno08x.enableReport(SH2_GYROSCOPE_CALIBRATED, 20000);
    bno08x.enableReport(SH2_MAGNETIC_FIELD_CALIBRATED, 20000);
  } else {
    if (DEBUG_MODE) DEBUG_SERIAL.println("** BNO08x IMU not detected! **");
  }

  updateHeartbeatLED();

  // Initialize GPS
  if (myGNSS.begin()) {
    if (DEBUG_MODE) DEBUG_SERIAL.println("GPS initialized.");
    myGNSS.setI2COutput(COM_TYPE_UBX);  // Set the I2C port to output UBX only
    myGNSS.setNavigationFrequency(60);
  } else {
    if (DEBUG_MODE) DEBUG_SERIAL.println("** GPS not detected! **");
  }

  pinMode(VOLTAGE_PIN, INPUT);
  analogReadResolution(12);            
  analogSetAttenuation(ADC_11db);      
  filtBatteryVoltage = 0.0;            
  lastBattReadTime = millis();

  if (DEBUG_MODE) {
    DEBUG_SERIAL.println("Setup complete.");
    DEBUG_SERIAL.println("=================================");
  }
}

DataPacket collectIMUData(DataPacket packet) {
  uint8_t executed_cases = 0;
  const uint8_t all_cases_executed = (STATUS_BNO08X_ACCEL | STATUS_BNO08X_GYRO | STATUS_BNO08X_ROT | STATUS_BNO08X_MAG);
  
  unsigned long startTime = millis();
  int attempts = 0;
  
  while ((executed_cases != all_cases_executed) && 
         (millis() - startTime < SENSOR_TIMEOUT) && 
         (attempts < MAX_IMU_ATTEMPTS)) {
    
    updateHeartbeatLED();
    
    attempts++;
    sh2_SensorValue_t sensorValue;
    
    if (bno08x.getSensorEvent(&sensorValue)) {
      switch (sensorValue.sensorId) {
        case SH2_LINEAR_ACCELERATION:
          packet.comp_accel_x = float(sensorValue.un.linearAcceleration.x);
          packet.comp_accel_y = float(sensorValue.un.linearAcceleration.y);
          packet.comp_accel_z = float(sensorValue.un.linearAcceleration.z);
          executed_cases |= STATUS_BNO08X_ACCEL;
          break;
          
        case SH2_GYROSCOPE_CALIBRATED:
          packet.gyro_x = float(sensorValue.un.gyroscope.x);
          packet.gyro_y = float(sensorValue.un.gyroscope.y);
          packet.gyro_z = float(sensorValue.un.gyroscope.z);
          executed_cases |= STATUS_BNO08X_GYRO;
          break;
          
        case SH2_ROTATION_VECTOR:
          packet.quat_x = float(sensorValue.un.rotationVector.i);
          packet.quat_y = float(sensorValue.un.rotationVector.j);
          packet.quat_z = float(sensorValue.un.rotationVector.k);
          packet.quat_w = float(sensorValue.un.rotationVector.real);
          executed_cases |= STATUS_BNO08X_ROT;
          break;

        case SH2_MAGNETIC_FIELD_CALIBRATED:
          packet.magnetic_x = float(sensorValue.un.magneticField.x);
          packet.magnetic_y = float(sensorValue.un.magneticField.y);
          packet.magnetic_z = float(sensorValue.un.magneticField.z);
          executed_cases |= STATUS_BNO08X_MAG;
          break;

        default:
          break;
      }
    }
    
    delay(1);
  }
  
  status_flags |= executed_cases;
  
  return packet;
}

void loop() {
  updateHeartbeatLED();

  DataPacket data = {0};  // Initialize all values to 0
  data.timestamp = millis();
  status_flags = 0;  // Clear status flags
  
  // Read Battery Voltage
  int raw_voltage = analogRead(VOLTAGE_PIN);
  data.voltage = (raw_voltage * 3.3) / 64.0;
  
  updateHeartbeatLED();
  
  // Read DPS310 Sensor with timeout
  sensors_event_t temp_event, pressure_event;
  unsigned long dpsStartTime = millis();
  bool dpsSuccess = false;
  
  while (!dpsSuccess && (millis() - dpsStartTime < SENSOR_TIMEOUT)) {
    updateHeartbeatLED();
    
    if (dps.getEvents(&temp_event, &pressure_event)) {
      data.temperature = temp_event.temperature;
      data.pressure = pressure_event.pressure;
      data.altitude = 44330.0 * (1.0 - pow(data.pressure / SEALEVEL_PRESSURE_HPA, 0.1903));
      // Sanity check for barometric altitude
      if (data.altitude > 10000 || data.altitude < -1000) {
        data.altitude = 0;  // Invalid value indicator
      }
      status_flags |= STATUS_DPS310_OK;
      dpsSuccess = true;
    }
    delay(1);
  }
  
  updateHeartbeatLED();
  
  // Get GPS data with timeout and fix validation
  if (myGNSS.getPVT(SENSOR_TIMEOUT)) {
    if (myGNSS.getGnssFixOk()) {  // Only use data if fix is valid
      data.gps_lat = float(myGNSS.getLatitude() / 10000000.0);
      data.gps_long = float(myGNSS.getLongitude() / 10000000.0);
      data.gps_alt = float(myGNSS.getAltitudeMSL() / 1000.0);
      // Sanity check for GPS altitude
      if (data.gps_alt > 10000 || data.gps_alt < -1000) {
        data.gps_alt = 0;  // Invalid value indicator
      }
      status_flags |= STATUS_GPS_OK;
    }
  }
  
  updateHeartbeatLED();
  
  // Collect IMU data
  data = collectIMUData(data);
  
  updateHeartbeatLED();
  
  // Transmit Binary Data Over Serial with new 4-byte marker
  if (Serial.availableForWrite() >= sizeof(data) + sizeof(PACKET_START_MARKER)) {
    Serial.write(PACKET_START_MARKER, sizeof(PACKET_START_MARKER));  // Write 4-byte header
    Serial.write((byte*)&data, sizeof(data));
  }

  // Print human-readable data if debug is enabled
  if (DEBUG_MODE) {
    printHumanReadableData(data);
  }
  
  delay(10);
}