#!/usr/bin/env python3
"""Export production-ready RS-274X Gerber and Excellon drill files for the satellite carrier board.

Outputs to: hardware/gerbers/ and hardware/gerbers.zip
Compatible with JLCPCB, PCBWay, and all standard PCB manufacturers.
"""
import os, sys, math, zipfile

# Import parameters and routing from generate_kicad
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from generate_kicad import (
    BW, BH, ORG, PARTS, FPS, ALLPADS, HOLES, KEEPOUT,
    TRK, PWR_TRK, VIA_D, VIA_DRILL, route_all, route_with_retries
)

GERBER_DIR = os.path.join(HERE, "..", "gerbers")
ZIP_PATH = os.path.join(HERE, "..", "gerbers.zip")
os.makedirs(GERBER_DIR, exist_ok=True)

def g_coord(v):
    # 4.6 metric coordinates (in micrometers)
    return str(int(round(v * 1000000)))

class GerberWriter:
    def __init__(self, name, layer_desc):
        self.name = name
        self.apertures = {}   # (shape, d1, d2) -> ap_id (starts at 10)
        self.next_ap = 10
        self.commands = []
        self.current_ap = None
        self.layer_desc = layer_desc

    def get_ap(self, shape, d1, d2=0):
        key = (shape, round(d1, 4), round(d2, 4))
        if key not in self.apertures:
            self.apertures[key] = self.next_ap
            self.next_ap += 1
        return self.apertures[key]

    def select_ap(self, ap_id):
        if self.current_ap != ap_id:
            self.commands.append(f"D{ap_id}*")
            self.current_ap = ap_id

    def flash(self, shape, x, y, d1, d2=0):
        ap = self.get_ap(shape, d1, d2)
        self.select_ap(ap)
        self.commands.append(f"X{g_coord(x)}Y{g_coord(y)}D03*")

    def draw_line(self, x1, y1, x2, y2, width):
        ap = self.get_ap("C", width)
        self.select_ap(ap)
        self.commands.append(f"X{g_coord(x1)}Y{g_coord(y1)}D02*")
        self.commands.append(f"X{g_coord(x2)}Y{g_coord(y2)}D01*")

    def draw_rect_outline(self, x1, y1, x2, y2, width):
        self.draw_line(x1, y1, x2, y1, width)
        self.draw_line(x2, y1, x2, y2, width)
        self.draw_line(x2, y2, x1, y2, width)
        self.draw_line(x1, y2, x1, y1, width)

    def write(self, filepath):
        lines = [
            "G04 Gerber RS-274X*",
            f"G04 Layer: {self.layer_desc}*",
            "%FSLAX46Y46*%",
            "%MOMM*%",
            "%LPD*%",
            "G01*",
        ]
        # Write aperture definitions
        for (shape, d1, d2), ap_id in sorted(self.apertures.items(), key=lambda x: x[1]):
            if shape == "C":
                lines.append(f"%ADD{ap_id}C,{d1:.4f}*%")
            elif shape == "R":
                lines.append(f"%ADD{ap_id}R,{d1:.4f}X{d2:.4f}*%")
            elif shape == "O":
                lines.append(f"%ADD{ap_id}O,{d1:.4f}X{d2:.4f}*%")
        lines.extend(self.commands)
        lines.append("M02*")
        with open(filepath, "w") as fh:
            fh.write("\n".join(lines) + "\n")


def export_drill(filepath, pth_list, npth_list):
    # Group holes by drill diameter
    tools = {}
    for x, y, d in pth_list:
        tools.setdefault(round(d, 3), []).append((x, y))
    for x, y, d in npth_list:
        tools.setdefault(round(d, 3), []).append((x, y))

    lines = [
        "M48",
        "; DRILL file for satellite carrier board",
        "METRIC,LZ",
    ]
    t_map = {}
    for idx, d in enumerate(sorted(tools.keys()), start=1):
        t_id = f"T{idx:02d}"
        t_map[d] = t_id
        lines.append(f"{t_id}C{d:.3f}")
    lines.append("%")
    lines.append("G90")
    lines.append("G05")

    for d in sorted(tools.keys()):
        lines.append(t_map[d])
        for x, y in tools[d]:
            lines.append(f"X{x:.3f}Y{y:.3f}")
    lines.append("M30")

    with open(filepath, "w") as fh:
        fh.write("\n".join(lines) + "\n")


def generate_all_gerbers():
    print("Routing PCB for Gerber export...")
    res = route_with_retries(tries=4)

    f_cu = GerberWriter("F_Cu", "Top Copper")
    b_cu = GerberWriter("B_Cu", "Bottom Copper")
    f_mask = GerberWriter("F_Mask", "Top Solder Mask")
    b_mask = GerberWriter("B_Mask", "Bottom Solder Mask")
    f_silk = GerberWriter("F_Silk", "Top Silkscreen")
    edge = GerberWriter("Edge_Cuts", "Board Outline")

    # 1. Edge Cuts (90 x 86 mm board outline)
    edge.draw_rect_outline(0, 0, BW, BH, 0.1)

    # 2. Board outline on Silkscreen + Text line
    f_silk.draw_line(2, 2.6, 88, 2.6, 0.15)
    f_silk.draw_line(45, 1.2, 45, 2.4, 0.2) # Arrow indicator

    # Component silkscreen rectangles
    for p in PARTS:
        fp = FPS[p["fp"]]
        px, py = p["pos"]
        for (x1, y1, x2, y2) in fp["silk"]:
            f_silk.draw_rect_outline(px + x1, py + y1, px + x2, py + y2, 0.12)

    # 3. Pads and Masks
    pth_drills = []
    npth_drills = []

    for a in ALLPADS:
        pad = a["pad"]
        x, y = a["x"], a["y"]
        w, h = pad["size"]
        shape = pad["shape"]
        kind = pad["kind"]
        mask_exp = 0.1   # Standard 0.1mm solder mask expansion

        if kind == "thru":
            pth_drills.append((x, y, pad["drill"]))
            # Copper on both top and bottom
            if shape == "rect":
                f_cu.flash("R", x, y, w, h)
                b_cu.flash("R", x, y, w, h)
                f_mask.flash("R", x, y, w + mask_exp * 2, h + mask_exp * 2)
                b_mask.flash("R", x, y, w + mask_exp * 2, h + mask_exp * 2)
            else:
                f_cu.flash("C", x, y, w)
                b_cu.flash("C", x, y, w)
                f_mask.flash("C", x, y, w + mask_exp * 2)
                b_mask.flash("C", x, y, w + mask_exp * 2)

        elif kind == "smd":
            # Top layer SMD
            if shape == "circle":
                f_cu.flash("C", x, y, w)
                f_mask.flash("C", x, y, w + mask_exp * 2)
            else:
                f_cu.flash("R", x, y, w, h)
                f_mask.flash("R", x, y, w + mask_exp * 2, h + mask_exp * 2)

        elif kind == "npth":
            npth_drills.append((x, y, pad["drill"]))

    # M3 Mounting holes
    for hx, hy in HOLES:
        npth_drills.append((hx, hy, 3.2))

    # 4. Traces and Vias
    for net, r in res.items():
        for (layer_idx, p0, p1, width) in r["segs"]:
            writer = f_cu if layer_idx == 0 else b_cu
            writer.draw_line(p0[0], p0[1], p1[0], p1[1], width)

        for v in r["vias"]:
            # Via copper rings on both layers
            f_cu.flash("C", v[0], v[1], VIA_D)
            b_cu.flash("C", v[0], v[1], VIA_D)
            pth_drills.append((v[0], v[1], VIA_DRILL))

    # Write files
    outputs = {
        "satellite-F_Cu.gbr": f_cu,
        "satellite-B_Cu.gbr": b_cu,
        "satellite-F_Mask.gbr": f_mask,
        "satellite-B_Mask.gbr": b_mask,
        "satellite-F_Silkscreen.gbr": f_silk,
        "satellite-Edge_Cuts.gbr": edge,
    }

    files_written = []
    for fname, writer in outputs.items():
        p = os.path.join(GERBER_DIR, fname)
        writer.write(p)
        files_written.append(p)

    drl_path = os.path.join(GERBER_DIR, "satellite.drl")
    export_drill(drl_path, pth_drills, npth_drills)
    files_written.append(drl_path)

    # Create ZIP file for easy upload to JLCPCB / PCBWay
    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in files_written:
            zf.write(f, os.path.basename(f))

    print(f"Generated {len(files_written)} Gerber & drill files in {GERBER_DIR}")
    print(f"Created fabrication archive: {ZIP_PATH}")
    return files_written, ZIP_PATH

if __name__ == "__main__":
    generate_all_gerbers()
