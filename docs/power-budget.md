# Power Budget

Values below are **typical datasheet-level estimates. Replace with your INA219 measurements.**

| Load | Mode | Current (mA) | Notes |
|---|---|---|---|
| ESP32-CAM | capture + processing | ~150-200 | camera on |
| SX1278 | TX 17 dBm | ~90-120 | during packets only |
| ESP32-CAM | deep sleep | ~6-10 | AI-Thinker board overhead |
| ESP32 DevKit tracker | active | ~50-80 | WiFi/BT off |
| Servos | idle / moving | ~10 / 150-500 | move rarely |
| Sensors (INA219, BME280, MPU6050) | active | ~5 | |

## Battery
18650 nominal ~2000-3000 mAh at 3.7 V. Boost efficiency ~85%.

## Duty-cycle formula
`I_avg = (I_active * t_active + I_sleep * t_sleep) / (t_active + t_sleep)`

Fill in measured values:

| Cycle time | t_active (s) | I_avg (mA) | Runtime without sun (h) |
|---|---|---|---|
| 60 s | TBD | TBD | TBD |
| 300 s | TBD | TBD | TBD |

## Solar
Panel: TBD V / TBD mA. Measure charge current at noon vs. tracker fixed vs. tracking on.
