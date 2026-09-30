// Solar tracker + telemetry. Board: ESP32 DevKit (30-pin).
// Libraries: ESP32Servo, Adafruit INA219, Adafruit BME280, Adafruit MPU6050, Adafruit Unified Sensor.
#include <Wire.h>
#include <math.h>
#include <ESP32Servo.h>
#include <Adafruit_INA219.h>
#include <Adafruit_BME280.h>
#include <Adafruit_MPU6050.h>

// Pins
#define PIN_PAN   18
#define PIN_TILT  19
#define LDR_TL 34
#define LDR_TR 35
#define LDR_BL 32
#define LDR_BR 33
#define UART_TX2 17   // -> ESP32-CAM RX (GPIO3)
#define UART_RX2 16

// Tracking
#define DEADBAND   150     // ADC counts (0-4095)
#define STEP_DEG   1
#define PAN_MIN 10
#define PAN_MAX 170
#define TILT_MIN 20
#define TILT_MAX 160
#define LOOP_MS 100
#define TELEM_MS 1000

Servo pan, tilt;
int panA = 90, tiltA = 90;
Adafruit_INA219 inaSolar(0x40), inaBatt(0x41);   // solder A0 on the second board for 0x41
Adafruit_BME280 bme;
Adafruit_MPU6050 mpu;
bool okSolar, okBatt, okBme, okMpu;
uint32_t lastTelem = 0;

int readAvg(int pin) {
  long s = 0;
  for (int i = 0; i < 16; i++) s += analogRead(pin);
  return s / 16;
}

void setup() {
  Serial.begin(115200);
  Serial2.begin(115200, SERIAL_8N1, UART_RX2, UART_TX2);
  Wire.begin(21, 22);
  analogReadResolution(12);
  pan.setPeriodHertz(50);  tilt.setPeriodHertz(50);
  pan.attach(PIN_PAN, 500, 2400);
  tilt.attach(PIN_TILT, 500, 2400);
  pan.write(panA); tilt.write(tiltA);
  okSolar = inaSolar.begin();
  okBatt  = inaBatt.begin();
  okBme   = bme.begin(0x76);
  okMpu   = mpu.begin();
  Serial.println("INFO,Solar tracker booting...");
  Serial.printf("INFO,INA_Solar:%d INA_Batt:%d BME280:%d MPU6050:%d\n", okSolar, okBatt, okBme, okMpu);
}

void track() {
  int tl = readAvg(LDR_TL), tr = readAvg(LDR_TR), bl = readAvg(LDR_BL), br = readAvg(LDR_BR);
  int top = (tl + tr) / 2, bot = (bl + br) / 2;
  int left = (tl + bl) / 2, right = (tr + br) / 2;
  // Flip signs if your mechanics move the wrong way
  if (abs(top - bot) > DEADBAND)   tiltA += (top > bot) ? STEP_DEG : -STEP_DEG;
  if (abs(left - right) > DEADBAND) panA += (left > right) ? -STEP_DEG : STEP_DEG;
  panA = constrain(panA, PAN_MIN, PAN_MAX);
  tiltA = constrain(tiltA, TILT_MIN, TILT_MAX);
  pan.write(panA); tilt.write(tiltA);
}

void telemetry() {
  float sv = okSolar ? inaSolar.getBusVoltage_V() : 0, sm = okSolar ? inaSolar.getCurrent_mA() : 0;
  float bv = okBatt ? inaBatt.getBusVoltage_V() : 0,  bm = okBatt ? inaBatt.getCurrent_mA() : 0;
  float t = okBme ? bme.readTemperature() : 0, p = okBme ? bme.readPressure() / 100.0 : 0, h = okBme ? bme.readHumidity() : 0;
  float pitch = 0, roll = 0;
  if (okMpu) {
    sensors_event_t a, g, tmp;
    mpu.getEvent(&a, &g, &tmp);
    pitch = atan2(a.acceleration.x, sqrt(a.acceleration.y * a.acceleration.y + a.acceleration.z * a.acceleration.z)) * 57.2958;
    roll  = atan2(a.acceleration.y, a.acceleration.z) * 57.2958;
  }
  char line[160];
  snprintf(line, sizeof(line), "T,%.2f,%.0f,%.2f,%.0f,%.1f,%.1f,%.0f,%.0f,%.0f,%d,%d",
           sv, sm, bv, bm, t, p, h, pitch, roll, panA, tiltA);
  Serial2.println(line);
  Serial.println(line);
}

void loop() {
  track();
  if (millis() - lastTelem >= TELEM_MS) { lastTelem = millis(); telemetry(); }
  delay(LOOP_MS);
}
