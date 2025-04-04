#ifndef SENSORS_H
#define SENSORS_H

#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_DPS310.h>
#include <Adafruit_BNO08x.h>
#include <SparkFun_u-blox_GNSS_v3.h>
#include "config.h"

// Sensor objects
extern Adafruit_DPS310 dps;
extern Adafruit_BNO08x bno08x;
extern SFE_UBLOX_GNSS myGNSS;

// IMU reset tracking
extern unsigned long lastIMUResetTime;
extern bool badIMUDataDetected;

// Status flags
extern uint8_t status_flags;

// Function declarations
void setBNO08xReports();
void initSensors();
void collectSensorData(DataPacket &data);
void collectIMUData(DataPacket &data);

#endif