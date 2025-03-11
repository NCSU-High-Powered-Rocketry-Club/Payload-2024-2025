#include "debug.h"
#include "sensors.h" // For badIMUDataDetected and status_flags

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