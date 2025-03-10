#include "led.h"

unsigned long lastLedToggle = 0;
bool ledState = false;

void updateHeartbeatLED() {
  const unsigned long currentMillis = millis();
  if (currentMillis - lastLedToggle >= LED_INTERVAL) {
    lastLedToggle = currentMillis;
    ledState = !ledState;
    digitalWrite(LED_PIN, ledState);
  }
}