#include <Adafruit_DPS310.h>         // DPS310 Library
#include <Adafruit_BNO08x.h>         // BNO085 Library
#include <SparkFun_u-blox_GNSS_v3.h> // SAM-M10Q GPS Library
#include <Wire.h>                    // I2C Library

// Pin definitions
#define VOLTAGE_PIN A0               // Analog pin for voltage sensor
#define MIN_VOLTAGE 530              // ADC value for 0% battery (2.6V)
#define MAX_VOLTAGE 614              // ADC value for 100% battery (3.01V)

// DPS310 sensor object
Adafruit_DPS310 dps_310;

// BNO085 IMU object
Adafruit_BNO08x bno = Adafruit_BNO08x();
#define BNO_REPORT_ACCELEROMETER      0x01
#define BNO_REPORT_GYROSCOPE          0x02
#define BNO_REPORT_MAGNETOMETER       0x03
#define BNO_REPORT_ROTATION_VECTOR    0x05
#define BNO_REPORT_LINEAR_ACCELERATION 0x06  // Linear Acceleration report

// GNSS object
SFE_UBLOX_GNSS my_GNSS;
#define mySerial Serial2 // Use Serial1 to connect to the GNSS module

struct DataPacket {
    float timestamp;
    float voltage;
    float temperature;
    float pressure;
    float comp_accel_x, comp_accel_y, comp_accel_z;
    float gyro_x, gyro_y, gyro_z;
    float magnetic_x, magnetic_y, magnetic_z;
    float quat_w, quat_x, quat_y, quat_z;
    float lin_accel_X, lin_accel_y, lin_accel_z;
    float gps_lat, gps_long, gps_alt;
};

void setup() {
    // Start serial communication
    Serial.begin(115200);
    delay(3000); // Allow time for the Serial Monitor to initialize
    Serial.println("Initializing Sensors...");

    Wire.begin();
    Wire.setClock( 400000UL );

    // Initialize DPS310
    if (!dps_310.begin_I2C()) {
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
    while (my_GNSS.begin() == false) {
        Serial.println(F("u-blox GNSS not detected. Retrying..."));
        delay(1000);
    }

    my_GNSS.setI2COutput(COM_TYPE_UBX); //Set the I2C port to output UBX only 
    my_GNSS.setNavigationFrequency(60);
}

void loop() {
    // create data packet
    DataPacket data;

    // Add timestamp
    data.timestamp = millis();

    // reading voltage sensor
    int raw_voltage = analogRead(VOLTAGE_PIN);
    data.voltage = (raw_voltage * 3.3) / 1023.0;;

    // DPS310 (pressure and temperature)
    sensors_event_t temp_event, pressure_event;
    if (dps310.getEvents(&temp_event, &pressure_event)) {
        data.temperature = temp_event.temperature;
        data.pressure = pressure_event.pressure;
    } else {
        Serial.println("DPS310 data unavailable!");
        data.temperature = 0.0; // Null if no data
        data.pressure = 0.0;
    }

    // BNO085 (IMU and Magnetometer)
    sh2_SensorValue_t sensor_value;
    while (bno.getSensorEvent(&sensor_value)) {
        switch (sensor_value.sensorId) {
        case SH2_ACCELEROMETER:
            data.comp_accel_x = sensor_value.un.accelerometer.x;
            data.comp_accel_y = sensor_value.un.accelerometer.y;
            data.comp_accel_z = sensor_value.un.accelerometer.z;
            break;

        case SH2_GYROSCOPE_CALIBRATED:
            data.gyro_x = sensor_value.un.gyroscope.x;
            data.gyro_y = sensor_value.un.gyroscope.y;
            data.gyro_z = sensor_value.un.gyroscope.z;
            break;

        case SH2_MAGNETIC_FIELD_CALIBRATED:
            data.magnetic_x = sensor_value.un.magneticField.x;
            data.magnetic_y = sensor_value.un.magneticField.y;
            data.magnetic_z = sensor_value.un.magneticField.z;
            break;

        case SH2_ROTATION_VECTOR:
            data.quat_x = sensor_value.un.rotationVector.i;
            data.quat_y = sensor_value.un.rotationVector.j;
            data.quat_z = sensor_value.un.rotationVector.k;
            data.quat_w = sensor_value.un.rotationVector.real;
            break;

        case SH2_LINEAR_ACCELERATION:
            data.lin_accel_X = sensor_value.un.linearAcceleration.x;
            data.lin_accel_y = sensor_value.un.linearAcceleration.y;
            data.lin_accel_z = sensor_value.un.linearAcceleration.z;
            break;

        default:
            break; // Ignore other reports
        }
    }

    // GNSS (latitude, longitude, altitude)
    // The 20 represents the delay for the most part.
    if (my_GNSS.getPVT(20) == true) {
        data.gps_lat = my_GNSS.getLatitude() / 10000000.0;
        data.gps_long = my_GNSS.getLongitude() / 10000000.0;
        data.gps_alt = my_GNSS.getAltitudeMSL() / 1000.0;
    } else {
        Serial.println("GPS data unavailable!");
        data.gps_lat = 0.0;
        data.gps_long = 0.0;
        data.gps_alt = 0.0;
    }

    Serial.println(sizeof(data));
}
