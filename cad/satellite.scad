// CubeSat-style 1U-ish model (100 mm cube), parametric.
// Export: openscad -D 'part="body"' -o body.stl satellite.scad
// part = "assembly" | "body" | "base" | "tracker" | "panel"
part = "assembly";
$fn = 48;
S = 100;        // cube size
W = 2.5;        // wall
tilt = 35;      // panel tilt for preview

module servo() {
  color("royalblue") cube([23, 12.5, 22.5], center = true);
  color("white") translate([0, 0, 11.25]) cylinder(d = 6, h = 4);
}

module panel() { color("navy") cube([80, 60, 3], center = true); }

module body() {
  difference() {
    cube([S, S, S], center = true);
    // hollow, open bottom for assembly
    translate([0, 0, -W / 2]) cube([S - 2 * W, S - 2 * W, S - W + 0.02], center = true);
    // camera window on +Y face (offset -25.6 mm to align with PCB socket J1)
    translate([-25.6, S / 2 - W / 2, -26]) rotate([90, 0, 0]) cylinder(d = 14, h = W + 2, center = true);
    // power switch slot on -X face
    translate([-S / 2, 0, -20]) cube([W * 2 + 1, 12, 7], center = true);
    // antenna hole on top, rear
    translate([0, -35, S / 2]) cylinder(d = 6.5, h = W * 3, center = true);
    // cable hole for tracker servos (top, centre)
    translate([0, 20, S / 2]) cube([10, 10, W * 3], center = true);
  }
  // antenna mount boss
  translate([0, -35, S / 2 + 2]) difference() {
    cylinder(d = 12, h = 4);
    translate([0, 0, -1]) cylinder(d = 6.5, h = 6);
  }
}

module base() {
  difference() {
    translate([0, 0, -S / 2 - W / 2]) cube([S - 2 * W - 0.6, S - 2 * W - 0.6, W], center = true);
    for (x = [-40, 40], y = [-38, 38]) translate([x, y, -S / 2]) cylinder(d = 3.2, h = 10, center = true);
  }
  // PCB standoffs (80 x 76 mm hole pattern matches the KiCad board)
  for (x = [-40, 40], y = [-38, 38]) translate([x, y, -S / 2 + 3]) difference() {
    cylinder(d = 7, h = 6, center = true);
    cylinder(d = 2.8, h = 7, center = true);
  }
}

module tracker() {
  translate([0, 20, S / 2]) {
    translate([0, 0, 11.25]) servo();                      // pan servo
    translate([0, 0, 22.5 + 4]) {
      color("gray") cylinder(d = 24, h = 2);               // turntable
      for (x = [-18, 18]) translate([x, 0, 11]) color("gray") cube([2, 14, 20], center = true);
      translate([-25, 0, 11]) rotate([0, 90, 0]) servo();  // tilt servo
      translate([0, 0, 21]) rotate([tilt, 0, 0]) translate([0, 0, 4]) panel();
    }
  }
}

if (part == "assembly") { color("silver") body(); color("darkgray") base(); tracker(); }
else if (part == "body") body();
else if (part == "base") base();
else if (part == "tracker") tracker();
else if (part == "panel") panel();
