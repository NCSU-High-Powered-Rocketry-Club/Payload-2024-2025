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

  // Get the document from collectSensorData
  JsonDocument doc = collectSensorData();

  // Serialize to MsgPack
  size_t msgpack_size = measureMsgPack(doc);
  uint8_t buffer[msgpack_size];
  serializeMsgPack(doc, buffer, msgpack_size);

  uint16_t size = msgpack_size;
  // Transmit binary data
  if (Serial.availableForWrite() >= sizeof(PACKET_START_MARKER) + sizeof(size) + msgpack_size) {
    Serial.write(PACKET_START_MARKER, sizeof(PACKET_START_MARKER));
    Serial.write((uint8_t*)&size, sizeof(size));
    Serial.write(buffer, msgpack_size);
  }

  #if DEBUG_MODE
  printHumanReadableData(data);
  #endif
}