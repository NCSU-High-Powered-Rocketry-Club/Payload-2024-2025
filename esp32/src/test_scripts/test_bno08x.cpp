#include <Arduino.h>
#include <Adafruit_BNO08x.h>
#include <Adafruit_DPS310.h>
#include <Wire.h>
#include <SparkFun_u-blox_GNSS_v3.h>
SFE_UBLOX_GNSS myGNSS;

// BNO08x pin definitions (I2C mode)
#define BNO08X_RESET -1

// Sensor objects
Adafruit_BNO08x bno08x(BNO08X_RESET);
Adafruit_DPS310 dps;
sh2_SensorValue_t sensorValue;

// BNO08x report types and intervals (matching your original)
sh2_SensorId_t reportTypes[] = {
  SH2_ROTATION_VECTOR,
  SH2_LINEAR_ACCELERATION,
  SH2_GYROSCOPE_CALIBRATED,
  SH2_MAGNETIC_FIELD_CALIBRATED
};
long reportIntervalUs[] = {
  10000,  // 100Hz
  10000,  // 100Hz
  10000,  // 100Hz
  20000   // 50Hz
};
const int numReports = sizeof(reportTypes) / sizeof(reportTypes[0]);

void setBNO08xReports() {
  Serial.println("Setting BNO08x reports");
  for (int i = 0; i < numReports; i++) {
    if (!bno08x.enableReport(reportTypes[i], reportIntervalUs[i])) {
      Serial.print("Could not enable report: ");
      Serial.println(reportTypes[i]);
    }
  }
}

void setup(void) {
  Serial.begin(115200);
  while (!Serial) delay(10);

  Serial.println("BNO08x + DPS310 Test");

  // Initialize I2C
  Wire.begin();
  Wire.setClock(800000UL);

  // Initialize BNO08x
  if (!bno08x.begin_I2C()) {
    Serial.println("Failed to find BNO08x");
    while (1) delay(10);
  }
  Serial.println("BNO08x Found!");
  setBNO08xReports();

  // Initialize DPS310
  if (!dps.begin_I2C(0x77) && !dps.begin_I2C(0x76)) {  // Try both addresses
    Serial.println("Failed to find DPS310");
    while (1) delay(10);
  }
  Serial.println("DPS310 Found!");
  dps.configurePressure(DPS310_64HZ, DPS310_16SAMPLES);
  dps.configureTemperature(DPS310_64HZ, DPS310_16SAMPLES);
  dps.setMode(DPS310_CONT_PRESTEMP);

  if (myGNSS.begin()) {
    Serial.println("GPS Found!");
    myGNSS.setI2COutput(COM_TYPE_UBX);
    myGNSS.setNavigationFrequency(60);
  }
  else {
    Serial.println("Failed to find GPS");
  }

  Serial.println("Reading events");
  delay(100);
}

void loop() {
  // BNO08x handling
  if (bno08x.wasReset()) {
    Serial.print("BNO08x was reset ");
    setBNO08xReports();
  }

  // Serial.println(millis());

  if (bno08x.getSensorEvent(&sensorValue)) {
    switch (sensorValue.sensorId) {
      case SH2_ROTATION_VECTOR:
        Serial.print("Rotation Vector - quat x: ");
        Serial.print(sensorValue.un.rotationVector.i);
        Serial.print(" y: ");
        Serial.print(sensorValue.un.rotationVector.j);
        Serial.print(" z: ");
        Serial.print(sensorValue.un.rotationVector.k);
        Serial.print(" w: ");
        Serial.println(sensorValue.un.rotationVector.real);
        Serial.print("Status: ");
        Serial.println(sensorValue.status);
        break;

      case SH2_LINEAR_ACCELERATION:
        Serial.print("Linear Accel - X: ");
        Serial.print(sensorValue.un.linearAcceleration.x);
        Serial.print(" Y: ");
        Serial.print(sensorValue.un.linearAcceleration.y);
        Serial.print(" Z: ");
        Serial.println(sensorValue.un.linearAcceleration.z);
        Serial.print("Status: ");
        Serial.println(sensorValue.status);
        break;

      case SH2_GYROSCOPE_CALIBRATED:
        Serial.print("Gyro - X: ");
        Serial.print(sensorValue.un.gyroscope.x);
        Serial.print(" Y: ");
        Serial.print(sensorValue.un.gyroscope.y);
        Serial.print(" Z: ");
        Serial.println(sensorValue.un.gyroscope.z);
        Serial.print("Status: ");
        Serial.println(sensorValue.status);
        break;

      case SH2_MAGNETIC_FIELD_CALIBRATED:
        Serial.print("Mag - X: ");
        Serial.print(sensorValue.un.magneticField.x);
        Serial.print(" Y: ");
        Serial.print(sensorValue.un.magneticField.y);
        Serial.print(" Z: ");
        Serial.println(sensorValue.un.magneticField.z);
        Serial.print("Status: ");
        Serial.println(sensorValue.status);
        break;
    }
  } else {
    // Serial.println("BNO08x: Failed to get sensor event");
  }

  // DPS310 handling
  sensors_event_t temp_event, pressure_event;
  if (dps.getEvents(&temp_event, &pressure_event)) {
    // Serial.print("DPS310 - Temp: ");
    // Serial.print(temp_event.temperature);
    // Serial.print(" °C, Pressure: ");
    // Serial.print(pressure_event.pressure);
    // Serial.println(" hPa");
  } else {
    // Serial.println("DPS310: Failed to get events");
  }

  if (myGNSS.getPVT(50)) {  // 50ms timeout
      // Serial.print("GPS - Lat: ");
      // Serial.print(myGNSS.getLatitude() / 10000000.0, 6);
      // Serial.print(" Lon: ");
      // Serial.print(myGNSS.getLongitude() / 10000000.0, 6);
      // Serial.print(" Alt: ");
      // Serial.println(myGNSS.getAltitudeMSL() / 1000.0);
    } else {
      // Serial.println("GPS: Failed to get PVT");
    }
  // delay(100);  // Keep 10Hz polling
}