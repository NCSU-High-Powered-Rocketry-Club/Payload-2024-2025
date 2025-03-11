#include <Arduino.h>
#include "config.h"
#include "sensors.h"
#include "led.h"
#include "debug.h"

void setup() {
  Serial.begin(SERIAL_BAUD_RATE);
  unsigned long startTime = millis();
  while (!Serial && (millis() - startTime < 1000)) { delay(10); }

  // Setup LED
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);

  #if DEBUG_MODE
  DEBUG_SERIAL.println("Sensor System Starting");
  #endif

  // Initialize sensors
  initSensors();

  // ADC setup
  pinMode(VOLTAGE_PIN, INPUT);
  analogReadResolution(12);
  analogSetAttenuation(ADC_11db);
}

void loop() {
  updateHeartbeatLED();

  DataPacket data = {0};
  data.timestamp = millis();

  // Collect all sensor data
  collectSensorData(data);

  // Transmit binary data
  if (Serial.availableForWrite() >= sizeof(data) + sizeof(PACKET_START_MARKER)) {
    Serial.write(PACKET_START_MARKER, sizeof(PACKET_START_MARKER));
    Serial.write((byte*)&data, sizeof(data));
  }

  #if DEBUG_MODE
  printHumanReadableData(data);
  #endif
}