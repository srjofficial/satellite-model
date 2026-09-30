# CAD

`satellite.scad` is a parametric OpenSCAD model: 100 mm hollow cube body, camera window, antenna mount, bottom plate with PCB standoffs, and a pan/tilt servo mount holding a solar panel.

Export STL:
```
openscad -D 'part="body"' -o body.stl satellite.scad
openscad -D 'part="base"' -o base.stl satellite.scad
openscad -D 'part="tracker"' -o tracker.stl satellite.scad
```
Add `.stl` (and `.step` if exported from FreeCAD) files here. Check dimensions against your real servos and panel before printing. The tracker part is a visual mount; the printable bracket needs fitting to your servo horn.
