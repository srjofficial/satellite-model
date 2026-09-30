# 🚀 LinkedIn Post Templates

Here are ready-to-publish post templates crafted for maximum engagement, showcasing both hardware engineering and embedded software skills.

---

## 🌟 Option 1: Engineering Story & Technical Deep Dive (Recommended)

Can you transmit images from a satellite using only long-range radio (LoRa)? 🛰️📡

I recently engineered a functional **1U CubeSat Satellite Model (100 mm cube)** from scratch—combining embedded systems, custom PCB design, solar tracking, and a long-range downlink.

Here’s how the subsystems work together:

☀️ **Dual-Axis Solar Tracker:**
A 4-quadrant LDR contrast bridge and ESP32 DevKit compute sunlight differentials to steer dual micro-servos across pan (10°–170°) and tilt (20°–160°) angles with software deadbanding.

📸 **Payload & LoRa Image Downlink:**
LoRa runs at low bitrates (~5 kbps at SF7/125kHz), making live video impossible. Instead, I designed a chunked downlink protocol: an AI-Thinker ESP32-CAM captures QQVGA (160x120) JPEG stills, slices them into 200-byte packets protected by CRC-16/CCITT-FALSE checksums, and transmits them over a 433 MHz SX1278 transceiver.

⚡ **Electrical Power Subsystem (EPS):**
A single 18650 Li-ion cell charged via TP4056 + DW01 protection, stepped up to 5V (MT3608) and 3.3V (AMS1117). Real-time solar and battery power telemetry are monitored using dual INA219 current/voltage sensors, while the camera node duty-cycles into deep sleep to maximize battery life.

📊 **Sensors & Ground Station:**
Monitors attitude via MPU6050 (pitch/roll) and environment via BME280 (temperature, atmospheric pressure, relative humidity). A dedicated ground station receiver forwards verified packets over USB serial to a custom Python desktop application that logs telemetry to CSV and automatically reassembles incoming JPEG images.

🛠️ **Hardware & CAD:**
- Designed a custom 90×86 mm 2-layer carrier PCB in KiCad 8.0 with dedicated ground pours and antenna keep-outs.
- Modeled a parametric 1U enclosure in OpenSCAD with an interactive WebGL 3D viewer built with Three.js.

Huge thanks to the open-source hardware community for making space technology concepts accessible for hands-on learning.

🔗 Full source code, schematics, and CAD files on GitHub:
https://github.com/srjofficial/satellite-model

#EmbeddedSystems #CubeSat #ESP32 #LoRa #PCBDesign #HardwareEngineering #OpenSource #IoT #KiCad #Arduino #SpaceTech

---

## ⚡ Option 2: Short & Punchy Portfolio Showcase

Thrilled to share my latest hardware & firmware project: a functional **1U CubeSat Satellite Working Model**! 🛰️⚡

Key features:
✅ Autonomous dual-axis solar tracking (4-quadrant LDR + dual servos)
✅ ESP32-CAM payload transmitting compressed JPEGs over SX1278 LoRa (433 MHz)
✅ CRC-16 protected packet protocol with automated Python image reassembly
✅ Comprehensive telemetry: Dual INA219 (V/I), BME280 (P/T/H), MPU6050 (attitude)
✅ Custom 2-layer KiCad 8 carrier PCB + parametric OpenSCAD 3D chassis

One of the best engineering lessons on this build was architecting around bandwidth constraints—turning a low-throughput LoRa radio into a reliable image downlink using custom chunking and CRC validation.

Check out the full repository (code, CAD, and schematics):
👉 https://github.com/srjofficial/satellite-model

#IoT #Embedded #ESP32 #CubeSat #Electronics #AerospaceEngineering #Robotics #Hardware
