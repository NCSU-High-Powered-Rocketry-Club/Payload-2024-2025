#include <Wire.h>
#include <SparkFun_u-blox_GNSS_v3.h> // Include the SparkFun u-blox GNSS library
#include <Arduino.h>

SFE_UBLOX_GNSS myGNSS;

void setup()
{
  Serial.begin(115200);
  Wire.begin();

  if (myGNSS.begin() == false)
  {
    Serial.println("u-blox GNSS not detected. Check wiring.");
    while (1);
  }
  Serial.println("u-blox GNSS module connected!");

  // Optional: Configure settings here if needed
}

void loop()
{
  // Print position, velocity, and time data
  long latitude = myGNSS.getLatitude();
  long longitude = myGNSS.getLongitude();
  long altitude = myGNSS.getAltitude();
  byte SIV = myGNSS.getSIV(); // Satellites in View

  Serial.print("Lat: ");
  Serial.print(latitude);
  Serial.print(", Lon: ");
  Serial.print(longitude);
  Serial.print(", Alt: ");
  Serial.print(altitude);
  Serial.print(", SIV: ");
  Serial.println(SIV);

  delay(1000);
}
