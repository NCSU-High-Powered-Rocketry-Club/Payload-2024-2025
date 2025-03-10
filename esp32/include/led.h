#ifndef LED_H
#define LED_H

#include <Arduino.h>
#include "config.h"

// LED state variables
extern unsigned long lastLedToggle;
extern bool ledState;

// Function declaration
void updateHeartbeatLED();

#endif