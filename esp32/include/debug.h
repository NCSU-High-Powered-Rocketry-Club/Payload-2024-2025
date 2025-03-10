#ifndef DEBUG_H
#define DEBUG_H

#include "config.h"

#if DEBUG_MODE
void printHumanReadableData(const JsonDocument &obj);
#endif

#endif