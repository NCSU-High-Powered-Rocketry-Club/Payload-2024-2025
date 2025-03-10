#ifndef CONFIG_H
#define CONFIG_H

#include <Arduino.h>

// Pin definitions
#define VOLTAGE_PIN 35         // ADC pin for battery voltage
#define LED_PIN 2              // ESP32's onboard LED

// Constants
#define SERIAL_BAUD_RATE 115200
#define SEALEVEL_PRESSURE_HPA 1013.25f
#define SENSOR_TIMEOUT 50      // Timeout for sensor reads
#define MAX_IMU_ATTEMPTS 40    // Max attempts for IMU
#define LED_INTERVAL 500       // LED blink interval in milliseconds
#define IMU_RESET_INTERVAL 5000 // IMU reset interval in milliseconds

// Debug settings
#define DEBUG_MODE 0           // 0 = binary only, 1 = human-readable output
#define DEBUG_SERIAL Serial    // Serial port for debug

// Thresholds for filtering
#define MAX_ACCEL_VALUE 300.0f  // Max acceptable acceleration (m/s²)
#define MAX_GYRO_VALUE 1000.0f  // Max acceptable gyroscope value (rad/s)
#define MAX_MAG_VALUE 5000.0f   // Max acceptable magnetometer value (uT)
#define MAX_QUAT_VALUE 100.0f   // Max acceptable quaternion value

// Status flag bits
#define STATUS_DPS310_OK    0x01
#define STATUS_BNO08X_ACCEL 0x02
#define STATUS_BNO08X_GYRO  0x04
#define STATUS_BNO08X_ROT   0x08
#define STATUS_GPS_OK       0x10
#define STATUS_BNO08X_MAG   0x20

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

// Packet start marker
static const uint8_t PACKET_START_MARKER[] = {0xFF, 0xFE, 0xFD, 0xFC};

#endif