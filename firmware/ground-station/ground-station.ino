// Ground station: ESP32 DevKit + SX1278. Verifies CRC and forwards packets over USB serial.
// Output line: PKT,<hex>,<rssi>,<snr>
#include <SPI.h>
#include <LoRa.h>

#define LORA_FREQ 433E6
#define LORA_SF   7
#define LORA_BW   125E3
#define LORA_SCK  18
#define LORA_MISO 19
#define LORA_MOSI 23
#define LORA_SS   5
#define LORA_RST  14
#define LORA_DIO0 26

uint16_t crc16(const uint8_t *d, size_t n) {
  uint16_t c = 0xFFFF;
  while (n--) {
    c ^= (uint16_t)(*d++) << 8;
    for (int i = 0; i < 8; i++) c = (c & 0x8000) ? (c << 1) ^ 0x1021 : (c << 1);
  }
  return c;
}

void setup() {
  Serial.begin(115200);
  SPI.begin(LORA_SCK, LORA_MISO, LORA_MOSI, LORA_SS);
  LoRa.setPins(LORA_SS, LORA_RST, LORA_DIO0);
  if (!LoRa.begin(LORA_FREQ)) { Serial.println("ERR,LoRa init failed"); while (1) delay(1000); }
  LoRa.setSpreadingFactor(LORA_SF);
  LoRa.setSignalBandwidth(LORA_BW);
  LoRa.setCodingRate4(5);
  LoRa.enableCrc();
  Serial.println("INFO,ground station ready");
}

void loop() {
  int sz = LoRa.parsePacket();
  if (sz < 9) return;
  uint8_t buf[256];
  int n = 0;
  while (LoRa.available() && n < 256) buf[n++] = LoRa.read();
  if (n < 9) return;
  uint16_t rx = (buf[n - 2] << 8) | buf[n - 1];
  if (crc16(buf, n - 2) != rx) { Serial.println("ERR,crc"); return; }
  Serial.print("PKT,");
  for (int i = 0; i < n; i++) { if (buf[i] < 16) Serial.print('0'); Serial.print(buf[i], HEX); }
  Serial.print(',');
  Serial.print(LoRa.packetRssi());
  Serial.print(',');
  Serial.println(LoRa.packetSnr());
}
