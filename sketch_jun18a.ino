#include <Wire.h>
#include <Adafruit_ADS1X15.h>
#include <ArduinoJson.h>
#include <FS.h> // For SPIFFS

Adafruit_ADS1115 ads; // ADS1115 instance

void setup() {
  Serial.begin(115200);
  ads.begin();

  if (!SPIFFS.begin()) {
    Serial.println("Failed to mount SPIFFS");
    return;
  }

  delay(1000);
  writeToJSON(); // Initial reading
}

void loop() {
  delay(5000); // Every 5 sec
  writeToJSON();
}

// ---- Voltage RMS measurement using calibrated multiplier ----
float readVoltageRMS(int samples = 1000) {
  long sumSq = 0;
  for (int i = 0; i < samples; i++) {
    int16_t raw = ads.readADC_SingleEnded(0);  // ZMPT101B on A0
    float volts = raw * 0.1875 / 1000.0;        // Convert to volts
    float centered = volts - 1.65;              // Centered around 1.65V
    sumSq += centered * centered * 1e6;         // Scale for precision

    delayMicroseconds(500);                     // Sampling interval
    if (i % 100 == 0) yield();                  // Let ESP handle WiFi etc.
  }

  float meanSq = sumSq / (float)samples;
  float rms = sqrt(meanSq) / 1000.0;            // Back to volts

  float calibratedVoltage = rms * 138.53 * 6.3; // Calibrated to 230V at 1.66V ADC
  return calibratedVoltage;
}

// ---- Current measurement using SCT-013-030 (30A/1V) ----
float readCurrent() {
  int16_t raw = ads.readADC_SingleEnded(1);     // A1 = current sensor
  float volts = raw * 0.1875 / 1000.0;           // Convert to volts
  float current = abs(volts / 0.030);            // SCT-013-030 = 30A/1V
  return current;
}

// ---- Write voltage, current, power to JSON ----
void writeToJSON() {
  float voltage = readVoltageRMS();
  float current = readCurrent();
  float power = voltage * current;

  String timestamp = "2025-05-01T00:00:00"; // Placeholder

  StaticJsonDocument<256> doc;
  doc["timestamp"] = timestamp;
  doc["voltage"] = voltage;
  doc["current"] = current;
  doc["power"] = power;

  File file = SPIFFS.open("/iot.json", "w");
  if (!file) {
    Serial.println("Failed to open file for writing");
    return;
  }

  serializeJsonPretty(doc, file);
  file.close();

  Serial.println("iot.json written:");
  serializeJsonPretty(doc, Serial);
  Serial.println();
}
