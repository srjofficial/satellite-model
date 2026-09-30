# Pin Map

Board references (J1, J2...) match `hardware/kicad/`. Full connection list: `netlist.csv` (generated from the same table as the schematic and PCB).

## ESP32-CAM (AI-Thinker), J1 - camera node
| Signal | GPIO | Connects to |
|---|---|---|
| LoRa SCK | 14 | SX1278 SCK |
| LoRa MISO | 12 | SX1278 MISO |
| LoRa MOSI | 13 | SX1278 MOSI |
| LoRa NSS | 15 | SX1278 NSS |
| LoRa RST | 2 | SX1278 RESET |
| LoRa DIO0 | not used | TX-only firmware |
| Telemetry RX (UART0) | 3 | Tracker GPIO17 (disconnect when flashing) |
| Flash jumper | 0 | J5 (short IO0 to GND only while flashing) |
| 5V / GND | - | Boost output / GND |
| 3V3 for LoRa | - | Dedicated 3.3 V LDO (J13); the board's own 3V3 pin is left unconnected |

## ESP32 DevKit, J2 - tracker
| Signal | GPIO |
|---|---|
| Pan servo (J16) | 18 |
| Tilt servo (J17) | 19 |
| LDR TL / TR / BL / BR (J18-J21) | 34 / 35 / 32 / 33 |
| I2C SDA / SCL | 21 / 22 |
| UART2 TX (to CAM RX) | 17 |

I2C devices: INA219 solar (J7) 0x40, INA219 battery (J9) 0x41 (solder A0), BME280 (J14) 0x76, MPU6050 (J15) 0x68.

LDR wiring: 3.3 V -> LDR (J18-J21) -> ADC pin -> 10 kOhm (R1-R4) -> GND.

## Power path
Solar (J6) -> INA219 (J7) -> TP4056 IN -> TP4056 B+ -> INA219 (J9) -> 18650 (J10). Load takes TP4056 OUT+ -> switch (J11) -> 5 V boost (J12) -> 5 V rail -> 3.3 V LDO (J13).

TP4056 header (J8) pin order matches standard protected module pads:
1: IN+, 2: IN-, 3: OUT+, 4: B+, 5: B-, 6: OUT-.

## SX1278 Ra-02, J3 and ground station
Note for J3 on carrier board: Verify your Ra-02 breakout module pinout against J3 before soldering (bare modules use 2.0 mm pitch; check pin assignments).
Ground-station ESP32 DevKit wiring (separate, not on this board):

| Signal | GPIO |
|---|---|
| SCK / MISO / MOSI | 18 / 19 / 23 |
| NSS / RST / DIO0 | 5 / 14 / 26 |
