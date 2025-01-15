#include <ArduinoJson.h>
#include <Adafruit_DPS310.h>         // DPS310 Library
#include <Adafruit_BNO08x.h>         // BNO085 Library
#include <SparkFun_u-blox_GNSS_v3.h> // SAM-M10Q GPS Library
#include <Wire.h>                    // I2C Library

// Pin definitions
#define VOLTAGE_PIN A0               // Analog pin for voltage sensor
#define MIN_VOLTAGE 530              // ADC value for 0% battery (2.6V)
#define MAX_VOLTAGE 614              // ADC value for 100% battery (3.01V)

// DPS310 sensor object
Adafruit_DPS310 dps310;

// BNO085 IMU object
Adafruit_BNO08x bno = Adafruit_BNO08x();
#define BNO_REPORT_ACCELEROMETER      0x01
#define BNO_REPORT_GYROSCOPE          0x02
#define BNO_REPORT_MAGNETOMETER       0x03
#define BNO_REPORT_ROTATION_VECTOR    0x05
#define BNO_REPORT_LINEAR_ACCELERATION 0x06  // Linear Acceleration report

// GNSS object
SFE_UBLOX_GNSS myGNSS;
#define mySerial Serial2 // Use Serial1 to connect to the GNSS module

// Variables to store previous BNO085 values
float prevAccelX = 0.0, prevAccelY = 0.0, prevAccelZ = 0.0;
float prevGyroX = 0.0, prevGyroY = 0.0, prevGyroZ = 0.0;
float prevMagX = 0.0, prevMagY = 0.0, prevMagZ = 0.0;
float prevQuatI = 0.0, prevQuatJ = 0.0, prevQuatK = 0.0, prevQuatReal = 1.0;
float prevLinearAccelX = 0.0, prevLinearAccelY = 0.0, prevLinearAccelZ = 0.0;

void setup() {
  // Start serial communication
  Serial.begin(115200);
  delay(3000); // Allow time for the Serial Monitor to initialize
  Serial.println("Initializing Sensors...");

  Wire.begin();
  Wire.setClock( 400000UL );

  // Initialize DPS310
  if (!dps310.begin_I2C()) {
    Serial.println("DPS310 initialization failed!");
  } else {
    Serial.println("DPS310 initialized successfully!");
  }

  // Initialize BNO085
  if (!bno.begin_I2C()) {
    Serial.println("BNO085 initialization failed!");
    while (1);  // Halt if initialization fails
  } else {
    Serial.println("BNO085 initialized successfully!");
    bno.enableReport(BNO_REPORT_ACCELEROMETER, 50);
    bno.enableReport(BNO_REPORT_GYROSCOPE, 50);
    bno.enableReport(BNO_REPORT_MAGNETOMETER, 50);
    bno.enableReport(BNO_REPORT_ROTATION_VECTOR, 50);
    bno.enableReport(BNO_REPORT_LINEAR_ACCELERATION, 50);
  }

  // Initialize GPS
  while (myGNSS.begin() == false) {
    Serial.println(F("u-blox GNSS not detected. Retrying..."));
    delay(1000);
  }

  myGNSS.setI2COutput(COM_TYPE_UBX); //Set the I2C port to output UBX only 
  myGNSS.setNavigationFrequency(60);
}

void loop() {
  // Create a JSON document
  StaticJsonDocument<512> jsonDoc;

  // Add timestamp
  jsonDoc["timestamp"] = millis();

  // Analog voltage sensor
  int voltageRaw = analogRead(VOLTAGE_PIN);
  float voltage = (voltageRaw * 3.3) / 1023.0;
  jsonDoc["voltage"] = voltage;

  // DPS310 (pressure and temperature)
  sensors_event_t tempEvent, pressureEvent;
  if (dps310.getEvents(&tempEvent, &pressureEvent)) {
    jsonDoc["temperature"] = tempEvent.temperature;
    jsonDoc["pressure"] = pressureEvent.pressure;
  } else {
    Serial.println("DPS310 data unavailable!");
    jsonDoc["temperature"] = nullptr; // Null if no data
    jsonDoc["pressure"] = nullptr;
  }

  // BNO085 (IMU and Magnetometer)
  sh2_SensorValue_t sensorValue;
  while (bno.getSensorEvent(&sensorValue)) {
    switch (sensorValue.sensorId) {
      case SH2_ACCELEROMETER:
        prevAccelX = sensorValue.un.accelerometer.x;
        prevAccelY = sensorValue.un.accelerometer.y;
        prevAccelZ = sensorValue.un.accelerometer.z;
        break;

      case SH2_GYROSCOPE_CALIBRATED:
        prevGyroX = sensorValue.un.gyroscope.x;
        prevGyroY = sensorValue.un.gyroscope.y;
        prevGyroZ = sensorValue.un.gyroscope.z;
        break;

      case SH2_MAGNETIC_FIELD_CALIBRATED:
        prevMagX = sensorValue.un.magneticField.x;
        prevMagY = sensorValue.un.magneticField.y;
        prevMagZ = sensorValue.un.magneticField.z;
        break;

      case SH2_ROTATION_VECTOR:
        prevQuatI = sensorValue.un.rotationVector.i;
        prevQuatJ = sensorValue.un.rotationVector.j;
        prevQuatK = sensorValue.un.rotationVector.k;
        prevQuatReal = sensorValue.un.rotationVector.real;
        break;

      case SH2_LINEAR_ACCELERATION:
        prevLinearAccelX = sensorValue.un.linearAcceleration.x;
        prevLinearAccelY = sensorValue.un.linearAcceleration.y;
        prevLinearAccelZ = sensorValue.un.linearAcceleration.z;
        break;

      default:
        break; // Ignore other reports
    }
  }

  jsonDoc["accel"]["x"] = prevAccelX;
  jsonDoc["accel"]["y"] = prevAccelY;
  jsonDoc["accel"]["z"] = prevAccelZ;

  jsonDoc["gyro"]["x"] = prevGyroX;
  jsonDoc["gyro"]["y"] = prevGyroY;
  jsonDoc["gyro"]["z"] = prevGyroZ;

  jsonDoc["mag"]["x"] = prevMagX;
  jsonDoc["mag"]["y"] = prevMagY;
  jsonDoc["mag"]["z"] = prevMagZ;

  jsonDoc["quat"]["i"] = prevQuatI;
  jsonDoc["quat"]["j"] = prevQuatJ;
  jsonDoc["quat"]["k"] = prevQuatK;
  jsonDoc["quat"]["real"] = prevQuatReal;

  jsonDoc["linearAccel"]["x"] = prevLinearAccelX;
  jsonDoc["linearAccel"]["y"] = prevLinearAccelY;
  jsonDoc["linearAccel"]["z"] = prevLinearAccelZ;

  // GNSS (latitude, longitude, altitude)
  // The 20 represents the delay for the most part.
  if (myGNSS.getPVT(20) == true) {
    jsonDoc["gps"]["lat"] = myGNSS.getLatitude() / 10000000.0;
    jsonDoc["gps"]["lon"] = myGNSS.getLongitude() / 10000000.0;
    jsonDoc["gps"]["alt"] = myGNSS.getAltitudeMSL() / 1000.0;
  } else {
    Serial.println("GPS data unavailable!");
    jsonDoc["gps"] = nullptr; // Null if no data
  }

  // Serialize JSON to Serial
  if (!serializeJson(jsonDoc, Serial)) {
    Serial.println("Serialization failed!");
  } else {
    Serial.println();
  }
}
