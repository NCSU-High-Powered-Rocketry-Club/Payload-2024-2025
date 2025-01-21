#include <Adafruit_DPS310.h>          // DPS310 Library
#include <Adafruit_BNO08x.h>          // BNO085 Library
#include <SparkFun_u-blox_GNSS_v3.h>  // SAM-M10Q GPS Library
#include <Wire.h>                     // I2C Library

// Pin definitions
#define VOLTAGE_PIN A0   // Analog pin for voltage sensor
#define MIN_VOLTAGE 530  // ADC value for 0% battery (2.6V)
#define MAX_VOLTAGE 614  // ADC value for 100% battery (3.01V)

// DPS310 sensor object
Adafruit_DPS310 dps_310;

// BNO085 IMU object
Adafruit_BNO08x bno = Adafruit_BNO08x();
#define BNO_REPORT_ACCELEROMETER 0x01
#define BNO_REPORT_GYROSCOPE 0x02
#define BNO_REPORT_MAGNETOMETER 0x03
#define BNO_REPORT_ROTATION_VECTOR 0x05

// GNSS object
SFE_UBLOX_GNSS my_GNSS;
#define mySerial Serial2  // Use Serial1 to connect to the GNSS module

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

void setup() {
  // Start serial communication
  delay(3000);  // Allow time for the Serial Monitor to initialize

  Wire.begin();
  Wire.setClock(400000UL);

  // Initialize DPS310
 !dps_310.begin_I2C();

  // Initialize BNO085
  while (!bno.begin_I2C()) {
      delay(1000); // Wait for 1 second before retrying
  }

  // If initialization succeeds, enable reports
  bno.enableReport(BNO_REPORT_ACCELEROMETER, 40);
  bno.enableReport(BNO_REPORT_GYROSCOPE, 40);
  bno.enableReport(BNO_REPORT_MAGNETOMETER, 20);
  bno.enableReport(BNO_REPORT_ROTATION_VECTOR, 40);


  // Initialize GPS
  while (my_GNSS.begin() == false) {
    delay(1000);
  }
  my_GNSS.setI2COutput(COM_TYPE_UBX);  //Set the I2C port to output UBX only
  my_GNSS.setNavigationFrequency(60);
  Serial.begin(115200);
}

struct DataPacket collect(struct DataPacket packet) {
  // Add timestamp
  packet.timestamp = float(millis());

  // reading voltage sensor
  int raw_voltage = analogRead(VOLTAGE_PIN);
  packet.voltage = float((raw_voltage * 3.3) / 1023.0);

  uint8_t executed_cases = 0b000; // Bitmask for 5 cases (5 bits, all initially 0)
  const uint8_t all_cases_executed = 0b111  ; // All cases executed when all bits are 1

  while (executed_cases != all_cases_executed) {
    sh2_SensorValue_t sensor_value;
    if (bno.getSensorEvent(&sensor_value)) {
      switch (sensor_value.sensorId) {
        case SH2_ACCELEROMETER:
          packet.comp_accel_x = float(sensor_value.un.accelerometer.x);
          packet.comp_accel_y = float(sensor_value.un.accelerometer.y);
          packet.comp_accel_z = float(sensor_value.un.accelerometer.z);
          executed_cases |= (1 << 0); // Mark case 0 as executed
          break;

        case SH2_GYROSCOPE_CALIBRATED:
          packet.gyro_x = float(sensor_value.un.gyroscope.x);
          packet.gyro_y = float(sensor_value.un.gyroscope.y);
          packet.gyro_z = float(sensor_value.un.gyroscope.z);
          executed_cases |= (1 << 1); // Mark case 1 as executed
          break;

        case SH2_ROTATION_VECTOR:
          packet.quat_x = float(sensor_value.un.rotationVector.i);
          packet.quat_y = float(sensor_value.un.rotationVector.j);
          packet.quat_z = float(sensor_value.un.rotationVector.k);
          packet.quat_w = float(sensor_value.un.rotationVector.real);
          executed_cases |= (1 << 2); // Mark case 2 as executed
          break;

        case SH2_MAGNETIC_FIELD_CALIBRATED:
          packet.magnetic_x = float(sensor_value.un.magneticField.x);
          packet.magnetic_y = float(sensor_value.un.magneticField.y);
          packet.magnetic_z = float(sensor_value.un.magneticField.z);
          // the magnetic field is only at 25hz max, so we don't want to throttle the other sensor measurements
          break;

        default:
          break; // Ignore other reports
      }
    }
    // Serial.print(executed_cases);
    // Serial.println(" "+all_cases_executed);
  }
  return packet;
}

void loop() {
  // create data packet
  DataPacket data;

  // DPS310 (pressure and temperature)
  sensors_event_t temp_event, pressure_event;
  if (dps_310.getEvents(&temp_event, &pressure_event)) {
    data.temperature = float(temp_event.temperature);
    data.pressure = float(pressure_event.pressure);
    data.altitude = dps_310.readAltitude();
  } else {
    data.temperature = 0.0;
    data.pressure = 0.0;
  }

  // GNSS (latitude, longitude, altitude)
  // The 20 represents the delay for the most part.
  if (my_GNSS.getPVT(20) == true) {
    data.gps_lat = float(my_GNSS.getLatitude() / 10000000.0);
    data.gps_long = float(my_GNSS.getLongitude() / 10000000.0);
    data.gps_alt = float(my_GNSS.getAltitudeMSL() / 1000.0);
  } else {
    data.gps_lat = 0.0;
    data.gps_long = 0.0;
    data.gps_alt = 0.0;
  }

  data = collect(data);

  //Serial.println("=== DataPacket ===");
  // Serial.print("Timestamp: "); Serial.println(data.timestamp);
  // Serial.print("Voltage: "); Serial.println(data.voltage);
  // Serial.print("Temperature: "); Serial.println(data.temperature);
  // Serial.print("Pressure: "); Serial.println(data.pressure);
  // Serial.print("Comp Accel X: "); Serial.println(data.comp_accel_x);
  // Serial.print("Comp Accel Y: "); Serial.println(data.comp_accel_y);
  // Serial.print("Comp Accel Z: "); Serial.println(data.comp_accel_z);
  // Serial.print("Gyro X: "); Serial.println(data.gyro_x);
  // Serial.print("Gyro Y: "); Serial.println(data.gyro_y);
  // Serial.print("Gyro Z: "); Serial.println(data.gyro_z);
  // Serial.print("Magnetic X: "); Serial.println(data.magnetic_x);
  // Serial.print("Magnetic Y: "); Serial.println(data.magnetic_y);
  // Serial.print("Magnetic Z: "); Serial.println(data.magnetic_z);
  // Serial.print("Quat W: "); Serial.println(data.quat_w);
  // Serial.print("Quat X: "); Serial.println(data.quat_x);
  // Serial.print("Quat Y: "); Serial.println(data.quat_y);
  // Serial.print("Quat Z: "); Serial.println(data.quat_z);
  // Serial.print("GPS Lat: "); Serial.println(data.gps_lat);
  // Serial.print("GPS Long: "); Serial.println(data.gps_long);
  // Serial.print("GPS Alt: "); Serial.println(data.gps_alt);
  // Serial.println("==================");
  //Serial.println(Serial.availableForWrite());
  if (Serial.availableForWrite() >= sizeof(data)) {
    Serial.write('\n');
    Serial.write((byte*)&data, sizeof(data));
  } else {
    Serial.println(Serial.availableForWrite());
  }
  
}
