# Proteus Design Suite Guide

## Why is `.pdsprj` not directly included?
A `.pdsprj` file is a **proprietary, compiled binary archive** created by Labcenter Electronics Proteus. Inside the `.pdsprj` container are closed-source compiled database files (`ROOT.DSN` for ISIS and `LAYOUT.LYT` for ARES) that can **only be created natively by the Proteus software engine itself**. Any third-party file manually named `.pdsprj` will produce a "Corrupt or invalid project file" error in Proteus.

---

## How to use this project in Proteus

### 1. View the PCB in Proteus Gerber Viewer
Proteus has a built-in Gerber & Excellon viewer:
1. Open **Proteus**.
2. Click **Gerber Viewer** on the startup page (or go to `Output` > `Gerber/Excellon Output` > `Launch Gerber Viewer`).
3. Click `File` > `Open Gerber` and select the files from `hardware/gerbers/` (or extract `hardware/gerbers.zip`).
4. Proteus will render all copper layers, solder masks, silkscreen, and drill holes.

### 2. Import Netlist into Proteus ARES (PCB Layout)
If you want to route or modify the carrier board in Proteus ARES:
1. In Proteus, open **ARES PCB Layout**.
2. Go to `Tools` > `Netlist Compiler` (or `File` > `Import Netlist`).
3. Select `satellite_tango.net` (standard Tango netlist format provided in this directory).
4. Assign footprints for the module headers (`J1` to `J21`, passives `R1-R4`, `C1-C4`).
5. Proteus will load all 24 connected electrical nets.

### 3. Simulating the Circuit in Proteus ISIS
To simulate the CubeSat subsystems in Proteus ISIS:
* **Microcontroller:** Place an `ESP32-WROOM-32` or `Arduino Uno/Nano` (available in the Proteus component library).
* **Solar Tracker:** Place 4 `TORCH_LDR` components in a bridge with four `10k` resistors to analog ADC pins (`IO34, IO35, IO32, IO33`), and connect two `MOTOR-SERVO` components to PWM pins `IO18` and `IO19`.
* **Firmware:** Load the compiled `.hex` or `.bin` from Arduino IDE (`firmware/solar-tracker/`) into the microcontroller properties.
