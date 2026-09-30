// ESP32-CAM node: capture JPEG, send over LoRa in CRC-protected chunks, deep sleep.
// Board: AI Thinker ESP32-CAM. Library: LoRa (Sandeep Mistry).
// Telemetry arrives as a text line on UART0 RX (GPIO3) from the tracker MCU.
// Disconnect that wire while flashing.
#include "esp_camera.h"
#include <SPI.h>
#include <LoRa.h>
#include "driver/gpio.h"

// ---- Config ----
#define SLEEP_SECONDS   60
#define LORA_FREQ       433E6   // use your region's legal band
#define LORA_SF         7
#define LORA_BW         125E3
#define CHUNK           200
#define TYPE_IMG        0x10
#define TYPE_TELEM      0x20

// LoRa SX1278 pins (TX only, DIO0 not used)
#define LORA_SCK  14
#define LORA_MISO 12
#define LORA_MOSI 13
#define LORA_SS   15
#define LORA_RST  2

// AI Thinker camera pins
#define PWDN_GPIO_NUM 32
#define RESET_GPIO_NUM -1
#define XCLK_GPIO_NUM 0
#define SIOD_GPIO_NUM 26
#define SIOC_GPIO_NUM 27
#define Y9_GPIO_NUM 35
#define Y8_GPIO_NUM 34
#define Y7_GPIO_NUM 39
#define Y6_GPIO_NUM 36
#define Y5_GPIO_NUM 21
#define Y4_GPIO_NUM 19
#define Y3_GPIO_NUM 18
#define Y2_GPIO_NUM 5
#define VSYNC_GPIO_NUM 25
#define HREF_GPIO_NUM 23
#define PCLK_GPIO_NUM 22

RTC_DATA_ATTR uint8_t imgId = 0;

uint16_t crc16(const uint8_t *d, size_t n) {
  uint16_t c = 0xFFFF;
  while (n--) {
    c ^= (uint16_t)(*d++) << 8;
    for (int i = 0; i < 8; i++) c = (c & 0x8000) ? (c << 1) ^ 0x1021 : (c << 1);
  }
  return c;
}

void sendPacket(uint8_t type, uint8_t id, uint16_t seq, uint16_t total, const uint8_t *p, uint8_t len) {
  uint8_t buf[7 + CHUNK + 2];
  buf[0] = type; buf[1] = id;
  buf[2] = seq >> 8;   buf[3] = seq & 0xFF;
  buf[4] = total >> 8; buf[5] = total & 0xFF;
  buf[6] = len;
  memcpy(buf + 7, p, len);
  uint16_t c = crc16(buf, 7 + len);
  buf[7 + len] = c >> 8;
  buf[8 + len] = c & 0xFF;
  LoRa.beginPacket();
  LoRa.write(buf, 9 + len);
  LoRa.endPacket();      // blocking until TX done
  delay(20);
}

bool camReady = false;

String readTelemetry(uint32_t timeoutMs) {
  String last = "";
  String line = "";
  uint32_t t0 = millis();
  while (millis() - t0 < timeoutMs) {
    while (Serial.available()) {
      char ch = Serial.read();
      if (ch == '\n') { if (line.startsWith("T,")) last = line; line = ""; }
      else if (ch != '\r' && line.length() < 180) line += ch;
    }
    if (last.length()) break;
  }
  return last;
}

bool initCamera() {
  camera_config_t c = {};
  c.ledc_channel = LEDC_CHANNEL_0; c.ledc_timer = LEDC_TIMER_0;
  c.pin_d0 = Y2_GPIO_NUM; c.pin_d1 = Y3_GPIO_NUM; c.pin_d2 = Y4_GPIO_NUM; c.pin_d3 = Y5_GPIO_NUM;
  c.pin_d4 = Y6_GPIO_NUM; c.pin_d5 = Y7_GPIO_NUM; c.pin_d6 = Y8_GPIO_NUM; c.pin_d7 = Y9_GPIO_NUM;
  c.pin_xclk = XCLK_GPIO_NUM; c.pin_pclk = PCLK_GPIO_NUM;
  c.pin_vsync = VSYNC_GPIO_NUM; c.pin_href = HREF_GPIO_NUM;
  c.pin_sccb_sda = SIOD_GPIO_NUM; c.pin_sccb_scl = SIOC_GPIO_NUM;
  c.pin_pwdn = PWDN_GPIO_NUM; c.pin_reset = RESET_GPIO_NUM;
  c.xclk_freq_hz = 20000000;
  c.pixel_format = PIXFORMAT_JPEG;
  c.frame_size = FRAMESIZE_QQVGA;   // 160x120
  c.jpeg_quality = 15;              // higher number = smaller file
  c.fb_count = 1;
  camReady = (esp_camera_init(&c) == ESP_OK);
  return camReady;
}

void goToSleep() {
  LoRa.sleep();
  if (camReady) esp_camera_deinit();
  pinMode(PWDN_GPIO_NUM, OUTPUT);
  digitalWrite(PWDN_GPIO_NUM, HIGH);          // camera power-down
  gpio_hold_en((gpio_num_t)PWDN_GPIO_NUM);
  gpio_deep_sleep_hold_en();
  Serial.flush();
  esp_sleep_enable_timer_wakeup((uint64_t)SLEEP_SECONDS * 1000000ULL);
  esp_deep_sleep_start();
}

void setup() {
  gpio_hold_dis((gpio_num_t)PWDN_GPIO_NUM);
  Serial.begin(115200);
  String telem = readTelemetry(3000);

  SPI.begin(LORA_SCK, LORA_MISO, LORA_MOSI, LORA_SS);
  LoRa.setPins(LORA_SS, LORA_RST, -1);
  if (!LoRa.begin(LORA_FREQ)) {
    Serial.println("ERR,LoRa init failed");
    goToSleep();
  }
  LoRa.setSpreadingFactor(LORA_SF);
  LoRa.setSignalBandwidth(LORA_BW);
  LoRa.setCodingRate4(5);
  LoRa.setTxPower(17);
  LoRa.enableCrc();

  if (telem.length()) sendPacket(TYPE_TELEM, imgId, 0, 1, (const uint8_t *)telem.c_str(), telem.length());

  if (initCamera()) {
    for (int i = 0; i < 3; i++) { camera_fb_t *f = esp_camera_fb_get(); if (f) esp_camera_fb_return(f); }
    camera_fb_t *fb = esp_camera_fb_get();
    if (fb) {
      uint16_t total = (fb->len + CHUNK - 1) / CHUNK;
      for (uint16_t s = 0; s < total; s++) {
        size_t off = (size_t)s * CHUNK;
        uint8_t n = min((size_t)CHUNK, fb->len - off);
        sendPacket(TYPE_IMG, imgId, s, total, fb->buf + off, n);
      }
      esp_camera_fb_return(fb);
      imgId++;
    }
  } else {
    Serial.println("ERR,camera init failed");
  }
  goToSleep();
}

void loop() {}
