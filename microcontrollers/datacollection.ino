#include <Adafruit_DPS310.h>         // DPS310 Library
#include <Adafruit_BNO08x.h>          // BNO08x Library
#include <SparkFun_u-blox_GNSS_v3.h>  // GNSS (GPS) Library
#include <Wire.h>                     // Wire Library for I2C
// DPS310 (pressure/temperature sensor)
Adafruit_DPS310 dps310;
// BNO085 (IMU sensor)
Adafruit_BNO08x bno = Adafruit_BNO08x();
#define BNO_REPORT_ACCELEROMETER       0x01
#define BNO_REPORT_GYROSCOPE           0x02
#define BNO_REPORT_MAGNETOMETER        0x03
#define BNO_REPORT_ROTATION_VECTOR     0x05
#define BNO_REPORT_LINEAR_ACCELERATION 0x04  // Linear acceleration report
// SAM-M10Q (GPS)
SFE_UBLOX_GNSS myGNSS;
#define mySerial Serial1 // Define Serial1 for GPS communication
// Voltage measurement parameters
#define VOLTAGE_PIN A0
#define MIN_VOLTAGE 530  // ADC reading for 0% battery (2.6V)
#define MAX_VOLTAGE 614  // ADC reading for 100% battery (3.01V)
bool gpsInitialized = false;
void setup() {
  Serial.begin(115200);
  delay(1000);
  // Initialize sensors
  if (!dps310.begin_I2C()) {
    Serial.println("DPS310 initialization failed!");
  }
  if (!bno.begin_I2C()) {
    Serial.println("BNO085 initialization failed!");
  } else {
    bno.enableReport(BNO_REPORT_ACCELEROMETER, 100);       // Accelerometer
    bno.enableReport(BNO_REPORT_GYROSCOPE, 100);           // Gyroscope
    bno.enableReport(BNO_REPORT_MAGNETOMETER, 100);        // Magnetometer
    bno.enableReport(BNO_REPORT_ROTATION_VECTOR, 100);     // Quaternion (rotation vector)
    bno.enableReport(BNO_REPORT_LINEAR_ACCELERATION, 100); // Linear acceleration
  }
  mySerial.begin(9600);
  gpsInitialized = myGNSS.begin(mySerial);
}
void loop() {
  // Collect data
  String data = "";
  // Voltage
  int voltageRaw = analogRead(VOLTAGE_PIN);
  float voltage = (voltageRaw * 3.3) / 1023.0;
  float percentage = (voltageRaw - MIN_VOLTAGE) * 100.0 / (MAX_VOLTAGE - MIN_VOLTAGE);
  data += "Voltage: " + String(voltage, 2) + " V, ";
  data += "Battery Level: " + String(constrain(percentage, 0, 100), 2) + " %, ";
  // DPS310
  sensors_event_t temp_event, pressure_event;
  if (dps310.getEvents(&temp_event, &pressure_event)) {
    data += "Temperature: " + String(temp_event.temperature, 2) + " °C, ";
    data += "Pressure: " + String(pressure_event.pressure, 2) + " Pa, ";
  } else {
    data += "Temperature: NA, Pressure: NA, ";
  }
  // BNO085
  sh2_SensorValue_t sensorValue;
  if (bno.getSensorEvent(&sensorValue)) {
    switch (sensorValue.sensorId) {
      case SH2_ACCELEROMETER:
        data += "Accel: " + String(sensorValue.un.accelerometer.x, 2) + ", " +
                String(sensorValue.un.accelerometer.y, 2) + ", " +
                String(sensorValue.un.accelerometer.z, 2) + ", ";
        break;
      case SH2_GYROSCOPE_CALIBRATED:
        data += "Gyro: " + String(sensorValue.un.gyroscope.x, 2) + ", " +
                String(sensorValue.un.gyroscope.y, 2) + ", " +
                String(sensorValue.un.gyroscope.z, 2) + ", ";
        break;
      case SH2_MAGNETIC_FIELD_CALIBRATED:
        data += "Mag: " + String(sensorValue.un.magneticField.x, 2) + ", " +
                String(sensorValue.un.magneticField.y, 2) + ", " +
                String(sensorValue.un.magneticField.z, 2) + ", ";
        break;
      case SH2_ROTATION_VECTOR:
        data += "Quat: " + String(sensorValue.un.rotationVector.i, 2) + ", " +
                String(sensorValue.un.rotationVector.j, 2) + ", " +
                String(sensorValue.un.rotationVector.k, 2) + ", " +
                String(sensorValue.un.rotationVector.real, 2) + ", ";
        break;
      case SH2_LINEAR_ACCELERATION:
        data += "Lin Accel: " + String(sensorValue.un.linearAcceleration.x, 2) + ", " +
                String(sensorValue.un.linearAcceleration.y, 2) + ", " +
                String(sensorValue.un.linearAcceleration.z, 2) + ", ";
        break;
      default:
        data += "IMU: Unknown data, ";
        break;
    }
  } else {
    data += "IMU: No data, ";
  }
  // GPS
  if (gpsInitialized && myGNSS.getPVT()) {
    data += "Lat: " + String(myGNSS.getLatitude() / 10000000.0, 7) + ", ";
    data += "Lon: " + String(myGNSS.getLongitude() / 10000000.0, 7) + ", ";
    data += "Alt: " + String(myGNSS.getAltitudeMSL() / 1000.0, 2) + " m";
  } else {
    data += "GPS: No data";
  }
  // Send data
  Serial.println(data);
  delay(300);  // Adjust as needed
}