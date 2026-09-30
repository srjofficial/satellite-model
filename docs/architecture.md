# Architecture

## Subsystems
1. **Power (EPS):** Solar panel -> TP4056 (protected) -> 18650 -> 5 V boost -> both ESP32 boards. Dedicated 3.3 V LDO for LoRa + I2C sensors.
2. **Attitude/solar tracking:** 4-quadrant LDR bridge read by ESP32 ADC. Top/bottom difference drives tilt servo, left/right difference drives pan servo (1 degree steps, deadband).
3. **Payload:** ESP32-CAM captures QQVGA JPEG on a timer.
4. **Comms:** SX1278 LoRa (SF7, BW 125 kHz, CR 4/5). Packets carry CRC-16/CCITT.
5. **Ground segment:** ESP32 + SX1278 forwards verified packets over USB serial; Python reassembles.

## Data flow
Tracker (1 Hz) --UART text--> CAM node. CAM wakes from deep sleep every `SLEEP_SECONDS`, grabs the latest telemetry line, captures an image, transmits telemetry packet + image chunks, sleeps.

## Packet format (big-endian)
| Bytes | Field |
|---|---|
| 1 | type: `0x10` image data, `0x20` telemetry |
| 1 | image id (wraps at 255) |
| 2 | sequence number (0-based) |
| 2 | total packets |
| 1 | payload length |
| N | payload (<= 200 B) |
| 2 | CRC-16/CCITT-FALSE over all previous bytes |

## Telemetry line
`T,solarV,solarmA,battV,battmA,tempC,pressHPa,humPct,pitch,roll,pan,tilt`

## Block diagram
Export the Mermaid diagram in the README to `docs/block-diagram.png` (mermaid.live) and commit it.
