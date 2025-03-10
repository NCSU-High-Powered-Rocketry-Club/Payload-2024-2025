#include "sensors.h"
#include <ArduinoJson.h>

// Sensor object definitions
Adafruit_DPS310 dps;
Adafruit_BNO08x bno08x(-1);
SFE_UBLOX_GNSS myGNSS;

// IMU reset tracking
unsigned long lastIMUResetTime = 0;
bool badIMUDataDetected = false;

// Status flags
uint8_t status_flags = 0;

void initSensors() {
  Wire.begin();
  Wire.setClock(WIRE_CLOCK_FREQUENCY);  // 400kHz I2C

  if (dps.begin_I2C(0x77) || dps.begin_I2C(0x76)) {
    #if DEBUG_MODE
    DEBUG_SERIAL.println("DPS310 initialized.");
    #endif
    dps.configurePressure(DPS310_64HZ, DPS310_16SAMPLES);
    dps.configureTemperature(DPS310_64HZ, DPS310_16SAMPLES);
    dps.setMode(DPS310_CONT_PRESTEMP);
  }

  if (bno08x.begin_I2C()) {
    #if DEBUG_MODE
    DEBUG_SERIAL.println("BNO08x IMU initialized.");
    #endif
    bno08x.enableReport(SH2_ROTATION_VECTOR, 10000);
    bno08x.enableReport(SH2_LINEAR_ACCELERATION, 10000);
    bno08x.enableReport(SH2_GYROSCOPE_CALIBRATED, 10000);
    bno08x.enableReport(SH2_MAGNETIC_FIELD_CALIBRATED, 20000);
  }

  if (myGNSS.begin()) {
    #if DEBUG_MODE
    DEBUG_SERIAL.println("GPS initialized.");
    #endif
    myGNSS.setI2COutput(COM_TYPE_UBX);
    myGNSS.setNavigationFrequency(60);
  }
}

JsonDocument collectSensorData() {
  // Create a MsgPack buffer
  JsonDocument doc;
  status_flags = 0;

  doc["timestamp"] = millis();

  doc["voltage"] = (analogRead(VOLTAGE_PIN) * 3.3) / 1024.0; 

  sensors_event_t temp_event, pressure_event;
  if (dps.getEvents(&temp_event, &pressure_event)) {
    doc["temperature"] = temp_event.temperature;
    doc["pressure"] = pressure_event.pressure;
    doc["altitude"] = 44330.0 * (1.0 - pow(doc["pressure"].as<float>() / SEALEVEL_PRESSURE_HPA, 0.1903));
    status_flags |= STATUS_DPS310_OK;
  }

  if (myGNSS.getPVT(SENSOR_TIMEOUT)) {
    doc["gps_lat"] = myGNSS.getLatitude() / 10000000.0;
    doc["gps_long"] = myGNSS.getLongitude() / 10000000.0;
    doc["gps_alt"] = myGNSS.getAltitudeMSL() / 1000.0;
    status_flags |= STATUS_GPS_OK;
  }

  collectIMUData(doc);
  return doc;
}

void collectIMUData(JsonDocument& obj) {
  uint8_t executed_cases = 0;
  const uint8_t all_cases_executed = (STATUS_BNO08X_ACCEL | STATUS_BNO08X_GYRO | STATUS_BNO08X_ROT | STATUS_BNO08X_MAG);

  unsigned long startTime = millis();
  int attempts = 0;
  bool attemptReset = false;

  while ((executed_cases != all_cases_executed) &&
         (millis() - startTime < SENSOR_TIMEOUT) &&
         (attempts < MAX_IMU_ATTEMPTS)) {
    attempts++;
    sh2_SensorValue_t sensorValue;

    if (bno08x.getSensorEvent(&sensorValue)) {
      switch (sensorValue.sensorId) {
        case SH2_LINEAR_ACCELERATION:
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
            obj["comp_accel_x"] = constrain(sensorValue.un.linearAcceleration.x, -MAX_ACCEL_VALUE, MAX_ACCEL_VALUE);
            obj["comp_accel_y"] = constrain(sensorValue.un.linearAcceleration.y, -MAX_ACCEL_VALUE, MAX_ACCEL_VALUE);
            obj["comp_accel_z"] = constrain(sensorValue.un.linearAcceleration.z, -MAX_ACCEL_VALUE, MAX_ACCEL_VALUE);
          } else {
            obj["comp_accel_x"] = sensorValue.un.linearAcceleration.x;
            obj["comp_accel_y"] = sensorValue.un.linearAcceleration.y;
            obj["comp_accel_z"] = sensorValue.un.linearAcceleration.z;
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
            obj["gyro_x"] = constrain(sensorValue.un.gyroscope.x, -MAX_GYRO_VALUE, MAX_GYRO_VALUE);
            obj["gyro_y"] = constrain(sensorValue.un.gyroscope.y, -MAX_GYRO_VALUE, MAX_GYRO_VALUE);
            obj["gyro_z"] = constrain(sensorValue.un.gyroscope.z, -MAX_GYRO_VALUE, MAX_GYRO_VALUE);
          } else {
            obj["gyro_x"] = sensorValue.un.gyroscope.x;
            obj["gyro_y"] = sensorValue.un.gyroscope.y;
            obj["gyro_z"] = sensorValue.un.gyroscope.z;
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
            float norm = sqrt(
              sensorValue.un.rotationVector.i * sensorValue.un.rotationVector.i +
              sensorValue.un.rotationVector.j * sensorValue.un.rotationVector.j +
              sensorValue.un.rotationVector.k * sensorValue.un.rotationVector.k +
              sensorValue.un.rotationVector.real * sensorValue.un.rotationVector.real
            );
            if (norm > 0) {
              obj["quat_x"] = sensorValue.un.rotationVector.i / norm;
              obj["quat_y"] = sensorValue.un.rotationVector.j / norm;
              obj["quat_z"] = sensorValue.un.rotationVector.k / norm;
              obj["quat_w"] = sensorValue.un.rotationVector.real / norm;
            } else {
              obj["quat_x"] = 0.0f;
              obj["quat_y"] = 0.0f;
              obj["quat_z"] = 0.0f;
              obj["quat_w"] = 1.0f;
            }
          } else {
            obj["quat_x"] = sensorValue.un.rotationVector.i;
            obj["quat_y"] = sensorValue.un.rotationVector.j;
            obj["quat_z"] = sensorValue.un.rotationVector.k;
            obj["quat_w"] = sensorValue.un.rotationVector.real;
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
            obj["magnetic_x"] = constrain(sensorValue.un.magneticField.x, -MAX_MAG_VALUE, MAX_MAG_VALUE);
            obj["magnetic_y"] = constrain(sensorValue.un.magneticField.y, -MAX_MAG_VALUE, MAX_MAG_VALUE);
            obj["magnetic_z"] = constrain(sensorValue.un.magneticField.z, -MAX_MAG_VALUE, MAX_MAG_VALUE);
          } else {
            obj["magnetic_x"] = sensorValue.un.magneticField.x;
            obj["magnetic_y"] = sensorValue.un.magneticField.y;
            obj["magnetic_z"] = sensorValue.un.magneticField.z;
          }
          executed_cases |= STATUS_BNO08X_MAG;
          break;
      }
    } else {
      attemptReset = true;
    }
  }

  if (attemptReset && (executed_cases == 0) && 
      (millis() - lastIMUResetTime >= IMU_RESET_INTERVAL)) {
    #if DEBUG_MODE
    DEBUG_SERIAL.println("IMU not responding - attempting reset");
    #endif
    if (bno08x.begin_I2C()) {
      #if DEBUG_MODE
      DEBUG_SERIAL.println("BNO08x IMU reinitialized successfully.");
      #endif
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

  status_flags |= executed_cases;
}