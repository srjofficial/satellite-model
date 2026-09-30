# KiCad project (carrier board, rev A)

Open `satellite.kicad_pro` in **KiCad 8 or newer**.

| File | Contents |
|---|---|
| `satellite.kicad_sch` | Schematic: every module as a header symbol, nets joined by labels |
| `satellite.kicad_pcb` | 90 x 86 mm 2-layer board, placed and routed, GND pour on both layers, antenna keep-out |
| `satellite.pretty/` | Footprints (headers, module sockets, 0805, radial cap, test point, M3 hole) |
| `generate_kicad.py` | Regenerates everything above and `../netlist.csv` (`python3 generate_kicad.py`) |
| `pcb-preview.png` | Picture of the routed board |

## How the board works
Nothing is soldered directly to the board except headers and small passives. Modules (ESP32-CAM, ESP32 DevKit, Ra-02 LoRa, TP4056, boost, LDO, INA219 x2, BME280, MPU6050) plug into or wire to headers. Servos, LDRs, solar panel, battery holder and switch connect through 2-3 pin headers.

Mounting holes: M3 at 80 x 76 mm spacing (matches `cad/satellite.scad`). The top edge (y = 0) is the camera edge.

## First steps in KiCad
1. Open the PCB, press **B** to fill zones, then run **Inspect > Design Rules Checker**.
2. Open the schematic, run **Inspect > Electrical Rules Checker**. Expect warnings about passive pins; every pin is typed "passive" on purpose.
3. **Tools > Update PCB from Schematic** should report no changes.
4. Check the 3D viewer, then **File > Fabrication Outputs > Gerbers/Drill** and save to `gerbers/`.

## What was and was not checked
Checked by script: file syntax (balanced S-expressions), every schematic label sits on a pin, all 24 signal/power nets routed, minimum copper clearance 0.216 mm against a 0.2 mm rule, nothing inside the antenna keep-out or near the edge.

**Not checked:** I could not open these files in KiCad itself. Expect small load or DRC surprises. Fix them in KiCad rather than re-running the script if you have already edited the board.

## Verify before ordering a board
- **Module pinouts vary by clone.** Compare the ESP32-CAM, DevKit, Ra-02, INA219 and TP4056 pin order and row spacing against your actual modules. Row spacing is set in `generate_kicad.py` (`ROW_CAM`, `ROW_DEV`); edit and re-run.
- Servo and boost traces are 0.8 mm; signals 0.4 mm. Servo stall current can exceed what one 18650 through a boost converter delivers. Keep the 470 uF capacitors.
- The battery path goes through INA219 #2 (0.1 ohm shunt), so peak load current drops roughly 0.1 V per amp.
- GPIO12 (LoRa MISO) is an ESP32 boot-strap pin and GPIO2 (LoRa RESET) must be low or floating to flash; unplug the LoRa module if flashing fails.
- Label the board "untested design" until built and tested.
