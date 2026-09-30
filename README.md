# 🛰️ CubeSat-Style 1U Satellite Working Model

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![KiCad: 8.0](https://img.shields.io/badge/KiCad-8.0-314cb0.svg?logo=kicad)](hardware/kicad/)
[![Hardware: ESP32](https://img.shields.io/badge/Hardware-ESP32%20%7C%20ESP32--CAM-red.svg?logo=espressif)](hardware/)
[![Radio: LoRa SX1278](https://img.shields.io/badge/Radio-LoRa%20433%20MHz-green.svg)](docs/architecture.md)
[![CAD: OpenSCAD](https://img.shields.io/badge/CAD-OpenSCAD%20Parametric-yellow.svg)](cad/)
[![Python: 3.8+](https://img.shields.io/badge/Python-3.8%2B-blue.svg?logo=python)](ground-station-ui/)

A comprehensive, fully open-source **1U CubeSat educational demonstrator (100 mm cube)** featuring autonomous dual-axis solar tracking, an ESP32-CAM imaging payload, environmental & electrical telemetry, and long-range LoRa packet downlink with automated ground station reassembly.

---

## 📌 Interactive 3D Model Preview

Experience the 3D model right in your web browser without installing any CAD software:
- 🌐 **Launch Local 3D Viewer:** Open [`cad/view_model.html`](cad/view_model.html) in any browser (or double-click it in Windows) for full Orbit controls, real-time Pan/Tilt tracking simulation, and an interactive **Exploded View**!

```powershell
Start-Process "cad\view_model.html"
```

---

## 🚀 Key Features

* **☀️ Autonomous Dual-Axis Solar Tracking:** 4-quadrant LDR contrast bridge driving two SG90/MG90S servos across pan (10°–170°) and tilt (20°–160°) axes with software deadband and smooth 1° increments.
* **📸 Chunked LoRa Imaging Payload:** AI-Thinker ESP32-CAM captures QQVGA (160×120) JPEG stills, slices them into 200-byte packets protected by CRC-16/CCITT-FALSE checksums, and transmits over SX1278 LoRa.
* **⚡ Comprehensive Telemetry Suite:** Dual INA219 sensors (solar generation V/mA and battery charge/discharge V/mA), Bosch BME280 (temperature, atmospheric pressure, relative humidity), and MPU6050 6-DOF IMU (real-time pitch/roll attitude).
* **🔋 Power Management & Duty Cycling:** Single 18650 Li-ion battery charged via TP4056 with DW01 low-voltage protection, 5V boost converter, dedicated 3.3V LDO, and deep-sleep duty cycling on the camera payload.
* **📡 Ground Station & Python Reassembly:** ESP32 + SX1278 receiver firmware that validates hardware & software CRC-16 checksums, paired with a Python application that reconstructs JPEG images and logs synchronized telemetry to CSV.
* **🛠️ Parametric CAD & Carrier PCB:** Parametric OpenSCAD design (`cad/satellite.scad`) matched to a custom 90×86 mm 2-layer KiCad carrier PCB (`hardware/kicad/`) with ground pours, M3 standoffs, and antenna keep-out zones.

---

## 🏗️ System Architecture

```mermaid
flowchart TD
  subgraph EPS["Electrical Power Subsystem (EPS)"]
    SP["☀️ Solar Panel (<= 6V)"] --> J7["INA219 #1 (Solar V & mA)"]
    J7 --> CH["TP4056 Charger + DW01 Protection"]
    CH <--> J9["INA219 #2 (Battery V & +/-mA)"]
    J9 <--> BAT["🔋 18650 Li-ion Cell (3.7V)"]
    CH --> SW["Power Switch"]
    SW --> BST["⚡ 5V Boost Converter"]
    BST --> RAIL5["+5V Power Rail"]
    RAIL5 --> LDO["AMS1117-3.3 LDO"]
    LDO --> RAIL3["+3.3V Power Rail"]
  end

  subgraph OAS["OBC & Attitude Subsystem (Tracker)"]
    RAIL5 --> TRK["ESP32 DevKit 30-Pin"]
    LDR["4x LDR Quadrant Bridge"] --> TRK
    BME["BME280 (Temp/Press/Hum)"] -->|I2C 0x76| TRK
    MPU["MPU6050 (Pitch/Roll)"] -->|I2C 0x68| TRK
    J7 -->|I2C 0x40| TRK
    J9 -->|I2C 0x41| TRK
    TRK -->|PWM GPIO 18| SRV1["Pan Servo (10°-170°)"]
    TRK -->|PWM GPIO 19| SRV2["Tilt Servo (20°-160°)"]
  end

  subgraph PAYLOAD["Camera Payload & Communications"]
    RAIL5 --> CAM["AI-Thinker ESP32-CAM"]
    RAIL3 --> LORA["SX1278 LoRa Module (433 MHz)"]
    TRK -->|UART2 115200 (GPIO 17 -> GPIO 3)| CAM
    CAM -->|HSPI: SCK 14, MISO 12, MOSI 13, NSS 15| LORA
  end

  subgraph GROUND["Ground Segment"]
    LORA -.->|"LoRa RF 433 MHz (SF7, BW 125kHz)"| GS_RF["Ground SX1278"]
    GS_RF --> GS_MCU["Ground ESP32 DevKit"]
    GS_MCU -->|"USB Serial (PKT,<hex>,<rssi>,<snr>)"| PY["Python Ground Station App"]
    PY --> CSV["📊 telemetry.csv"]
    PY --> JPG["🖼️ Reassembled JPEGs"]
  end
```

---

## 📦 Downlink Protocol & Packet Format

Telemetry and image chunks are packed into byte frames protected by **CRC-16/CCITT-FALSE** (`poly=0x1021`, `init=0xFFFF`):

| Offset (Bytes) | Field | Description |
|:---:|:---|:---|
| `0` | **Type** | `0x10` = Image Chunk, `0x20` = Telemetry |
| `1` | **Image ID** | Sequential image session ID (0–255, wraps) |
| `2..3` | **Sequence No** | 16-bit big-endian chunk index (0-based) |
| `4..5` | **Total Packets** | 16-bit big-endian total chunk count for image |
| `6` | **Length ($N$)** | Payload length ($\le 200$ bytes) |
| `7 .. 6+N` | **Payload** | Raw JPEG chunk or ASCII CSV telemetry string |
| `7+N .. 8+N` | **CRC-16** | CRC-16/CCITT calculated over bytes `0` through `6+N` |

### Telemetry String Structure
Transmitted over UART from the Tracker MCU to the Camera payload once per second:
```csv
T,solarV,solar_mA,battV,batt_mA,tempC,pressHPa,humPct,pitch,roll,pan,tilt
```

---

## 🗂️ Repository Structure

```
satellite-model/
├── cad/
│   ├── satellite.scad          # Parametric OpenSCAD 1U cube model
│   ├── view_model.html         # Interactive WebGL 3D model viewer
│   └── README.md               # 3D export instructions (STL/STEP)
├── firmware/
│   ├── esp32-cam-node/         # Camera payload, packetizer, LoRa TX, sleep
│   ├── solar-tracker/          # 4-quadrant LDR tracking, I2C sensors, servos
│   └── ground-station/         # ESP32 + LoRa receiver with CRC verification
├── ground-station-ui/
│   ├── ground_station.py       # Python image reassembly & CSV telemetry logger
│   └── requirements.txt        # Python dependencies (pyserial)
├── hardware/
│   ├── bom.csv                 # Detailed Bill of Materials
│   ├── netlist.csv             # Complete pin-to-pin electrical netlist
│   ├── pinmap.md               # Pin assignment documentation
│   └── kicad/
│       ├── generate_kicad.py   # Algorithmic router & KiCad project generator
│       ├── satellite.kicad_sch # Carrier board schematic
│       ├── satellite.kicad_pcb # Routed 2-layer PCB (90x86 mm)
│       ├── satellite.kicad_pro # KiCad 8 project configuration
│       ├── satellite.pretty/   # Custom footprints
│       └── pcb-preview.png     # Rendered PCB preview
└── docs/
    ├── architecture.md         # Subsystem dataflow & packet specification
    ├── power-budget.md         # Power consumption estimates & duty cycle formula
    ├── test-results.md         # Test result template
    └── linkedin-post.md        # Summary post template
```

---

## 🔧 Bill of Materials (BOM)

| Ref | Component | Description | Qty |
|---|---|---|:---:|
| **U1 / J1** | AI-Thinker ESP32-CAM | Camera payload node (OV2640) | 1 |
| **U2 / J2** | ESP32 DevKit (30-pin) | Solar tracker & telemetry aggregator | 1 |
| **U3 / J3** | SX1278 Ra-02 (433 MHz) | LoRa transceiver module (satellite node) | 1 |
| **U4** | SX1278 Ra-02 + ESP32 | Ground station receiver node | 1 |
| **SEN1 / J7** | INA219 Breakout | Solar current & voltage monitor (`0x40`) | 1 |
| **SEN2 / J9** | INA219 Breakout | Battery current & voltage monitor (`0x41`, solder A0) | 1 |
| **SEN3 / J14**| BME280 Breakout | Temperature, pressure, humidity (`0x76`) | 1 |
| **SEN4 / J15**| MPU6050 Breakout | 6-DOF Gyro & Accelerometer (`0x68`) | 1 |
| **ACT1, ACT2**| SG90 or MG90S | Pan & Tilt servos | 2 |
| **PWR1 / J8** | TP4056 Module | Li-ion charger with DW01 protection | 1 |
| **PWR2 / J12**| MT3608 Boost Module | 3.7V to 5.0V step-up DC-DC converter | 1 |
| **PWR3 / J13**| AMS1117-3.3 Module | 5.0V to 3.3V dedicated LDO | 1 |
| **BAT / J10** | 18650 Li-ion Cell | 3.7V nominal, 2000–3000 mAh + holder | 1 |
| **PV / J6**   | Mini Solar Panel | $\le 6\text{ V}$ open circuit (50–150 mA) | 1 |
| **LDR1–4**    | GL5528 LDR + 10k 0805 | Quadrant light detection dividers | 4 |
| **C1, C2**    | 470 µF 10V Radial | 5V rail bulk capacitors for servo surge absorption | 2 |

---

## ⚡ Setup & Flashing Instructions

### 1. Arduino IDE Setup
Install the **ESP32 Board Package** in Arduino IDE and install the following libraries via the Library Manager:
* `LoRa` (by Sandeep Mistry)
* `ESP32Servo` (by Kevin Harrington)
* `Adafruit INA219`
* `Adafruit BME280 Library`
* `Adafruit MPU6050`
* `Adafruit Unified Sensor`

### 2. Flashing the Tracker Node
1. Open [`firmware/solar-tracker/solar-tracker.ino`](firmware/solar-tracker/solar-tracker.ino).
2. Board: **ESP32 Dev Module** (30-pin DevKit).
3. Connect USB and click **Upload**.

### 3. Flashing the ESP32-CAM Node
> ⚠️ **IMPORTANT:** Disconnect the tracker telemetry line (`ESP32-CAM RX / GPIO 3`) and short `GPIO 0` to `GND` before powering on to enter flashing mode.
1. Open [`firmware/esp32-cam-node/esp32-cam-node.ino`](firmware/esp32-cam-node/esp32-cam-node.ino).
2. Board: **AI Thinker ESP32-CAM**.
3. Upload using an external USB-to-UART adapter (5V, GND, U0TXD, U0RXD).
4. Remove the `GPIO 0` to `GND` jumper and reconnect the telemetry wire after flashing.

### 4. Flashing the Ground Station
1. Open [`firmware/ground-station/ground-station.ino`](firmware/ground-station/ground-station.ino).
2. Connect the ground station ESP32 and click **Upload**.

### 5. Running the Ground Station App
```bash
# Navigate to the ground station directory
cd ground-station-ui

# Install dependencies
pip install -r requirements.txt

# Run the receiver (replace COM5 with your port, or /dev/ttyUSB0 on Linux/macOS)
python ground_station.py --port COM5
```
* **Telemetries:** Appended in real-time to `received/telemetry.csv` with timestamps, signal RSSI, and SNR.
* **Images:** Fully reassembled JPEGs saved automatically to `received/img_<id>_<timestamp>.jpg`.

---

## 📊 Power Budget & Battery Life

| Subsystem / Component | State | Current @ 5V / 3.3V |
|---|---|:---:|
| **ESP32 DevKit (Tracker)** | Active (Tracking & Reading Sensors) | ~50–70 mA |
| **Dual Servos (SG90/MG90S)**| Moving / Idle | ~150–500 mA (peak) / ~10 mA |
| **Sensors (INA219 x2, BME280, MPU6050)** | Active I2C | ~5 mA |
| **ESP32-CAM (Payload)** | Capture & LoRa TX (~5–8s burst) | ~200–280 mA |
| **ESP32-CAM (Payload)** | Deep Sleep (Duty cycle between shots) | ~6–8 mA |

* **Duty Cycle Formula:**
  $$I_{\text{avg}} = \frac{I_{\text{active}} \cdot t_{\text{active}} + I_{\text{sleep}} \cdot t_{\text{sleep}}}{t_{\text{active}} + t_{\text{sleep}}}$$
* With an average consumption of ~120 mA and a single 2500 mAh 18650 cell, expected continuous operation without sunlight is **16–20+ hours**, extended indefinitely under active solar tracking.

---

## 📜 License

This project is open-source under the [MIT License](LICENSE).
Feel free to use it for academic, research, or personal educational projects!
