# LinkedIn Post Template

Built a CubeSat-style satellite working model as my final degree project.

- Dual-axis solar tracking (4x LDR + 2 servos)
- ESP32-CAM payload sending compressed images over LoRa with CRC-checked packets
- Telemetry: power (INA219), environment (BME280), attitude (MPU6050)
- Deep-sleep duty cycling on a single 18650 + solar panel
- Custom 3D-printed frame (OpenSCAD) and PCB design (KiCad)

Lesson learned: LoRa can't stream video, so I redesigned the link around small JPEG stills + telemetry.

Code, CAD and hardware files: <GitHub link>

#ESP32 #LoRa #Embedded #IoT #CubeSat #KiCad #OpenSCAD
