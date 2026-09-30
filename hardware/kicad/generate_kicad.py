#!/usr/bin/env python3
"""Generate the KiCad 8 project for the satellite carrier board.

Outputs (next to this script): satellite.kicad_pro, satellite.kicad_sch,
satellite.kicad_pcb, satellite.pretty/*.kicad_mod, fp-lib-table,
../netlist.csv, pcb-preview.png

Single source of truth = the PARTS table below. Edit it and re-run:
    python3 generate_kicad.py
"""
import os, sys, uuid, heapq, math, csv
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
G = 0.508                    # routing grid (0.02 in)
ORG = (100.0, 100.0)         # board origin on the KiCad page
BW, BH = 90.0, 86.0          # board size, mm
ROW_CAM = 22.86              # ESP32-CAM pin-row spacing
ROW_DEV = 22.86              # DevKit pin-row spacing (use 25.4 if yours is wider, then re-run)
CLR, TRK, PWR_TRK = 0.2, 0.4, 0.8
VIA_D, VIA_DRILL = 0.8, 0.4

_ns = uuid.UUID("6f1c2a52-7d0e-4b39-9a55-3c6e0d8f1a10")
_cnt = [0]
def uid():
    _cnt[0] += 1
    return str(uuid.uuid5(_ns, str(_cnt[0])))
def q(v): return round(v / G) * G
def f(v): return ("%.4f" % v).rstrip("0").rstrip(".")

# ------------------------------------------------------------------ footprints
FPS = {}
def _reg(fp): FPS[fp["name"]] = fp; return fp["name"]

def thru(num, x, y, size=1.7, drill=1.0, rect=False):
    return dict(num=str(num), x=round(x, 4), y=round(y, 4), kind="thru",
                shape="rect" if rect else "circle", size=(size, size), drill=drill)

def fp_header(n):
    pads = [thru(i + 1, i * 2.54, 0, rect=(i == 0)) for i in range(n)]
    return _reg(dict(name=f"Header_1x{n:02d}_P2.54mm_XAxis", pads=pads,
                     silk=[(-1.27, -1.27, round((n - 1) * 2.54 + 1.27, 3), 1.27)],
                     ref_at=(0, -2.8), attr="through_hole",
                     desc=f"1x{n} 2.54 mm pin header/socket, pins along +X"))

def fp_two_row(name, n, pitch, row, size, drill, silk, desc, reverse_right=False):
    pads = [thru(i + 1, 0, i * pitch, size, drill, rect=(i == 0)) for i in range(n)]
    for i in range(n):
        y = (n - 1 - i) * pitch if reverse_right else i * pitch
        pads.append(thru(n + 1 + i, row, y, size, drill))
    return _reg(dict(name=name, pads=pads, silk=[silk], ref_at=(row / 2, silk[1] - 1.5),
                     attr="through_hole", desc=desc))

FP_CAM = fp_two_row(f"ESP32-CAM_Socket_2x08_Row{ROW_CAM}mm", 8, 2.54, ROW_CAM, 1.7, 1.0,
                    (ROW_CAM / 2 - 13.5, -22.7, ROW_CAM / 2 + 13.5, 18.1),
                    "AI-Thinker ESP32-CAM on two 1x8 sockets; camera toward -Y")
FP_DEV = fp_two_row(f"ESP32_DevKit_30pin_Socket_Row{ROW_DEV}mm", 15, 2.54, ROW_DEV, 1.7, 1.0,
                    (ROW_DEV / 2 - 12.7, -8.0, ROW_DEV / 2 + 12.7, 43.6),
                    "ESP32 DevKit 30-pin on two 1x15 sockets")
FP_LORA = fp_two_row("SX1278_RA-02_2x08_P2.00mm_Row16mm", 8, 2.0, 16.0, 1.5, 0.8,
                     (-1.0, -1.0, 17.0, 15.0),
                     "Ra-02 SX1278 module (or 2.0 mm adapter); pin 9 (ANT) bottom right",
                     reverse_right=True)
FP_TP = _reg(dict(name="TestPoint_Pad_D2.0mm", pads=[dict(num="1", x=0.0, y=0.0, kind="smd",
                  shape="circle", size=(2.0, 2.0))], silk=[], ref_at=(0, -2.0), attr="smd", desc="Test point"))
FP_R = _reg(dict(name="R_0805", pads=[dict(num="1", x=-0.95, y=0.0, kind="smd", shape="roundrect", size=(1.0, 1.3)),
                  dict(num="2", x=0.95, y=0.0, kind="smd", shape="roundrect", size=(1.0, 1.3))],
                 silk=[(-1.7, -0.9, 1.7, 0.9)], ref_at=(0, -1.8), attr="smd", desc="0805 resistor"))
FP_C = _reg(dict(name="C_0805", pads=FPS[FP_R]["pads"], silk=[(-1.7, -0.9, 1.7, 0.9)],
                 ref_at=(0, -1.8), attr="smd", desc="0805 capacitor"))
FP_CP = _reg(dict(name="CP_Radial_D8.0mm_P3.50mm", pads=[thru(1, 0, 0, 1.6, 0.8, rect=True), thru(2, 3.5, 0, 1.6, 0.8)],
                  silk=[(-2.5, -4.2, 6.0, 4.2)], ref_at=(1.75, -5.2), attr="through_hole",
                  desc="Radial electrolytic, 8 mm"))
FP_HOLE = _reg(dict(name="MountingHole_3.2mm_M3", pads=[dict(num="", x=0.0, y=0.0, kind="npth",
                  shape="circle", size=(3.2, 3.2), drill=3.2)], silk=[], ref_at=(0, -3.0),
                  attr="board_only", desc="M3 mounting hole"))

# ------------------------------------------------------------------ parts
PARTS = []
def part(ref, value, fp, pins, x, y, sym=None, right_rev=False):
    """pins: list of (pin_name, net_or_None) in pad order."""
    PARTS.append(dict(ref=ref, value=value, fp=fp, pins=pins, pos=(q(x), q(y)),
                      sym=sym or ref, right_rev=right_rev))

def hdr(ref, value, pins, x, y):
    part(ref, value, fp_header(len(pins)), pins, x, y)

N = None
part("J1", "ESP32-CAM", FP_CAM, [
    ("5V", "+5V"), ("GND", "GND"), ("IO12", "LORA_MISO"), ("IO13", "LORA_MOSI"),
    ("IO15", "LORA_NSS"), ("IO14", "LORA_SCK"), ("IO2", "LORA_RST"), ("IO4", N),
    ("3V3", N), ("IO16", N), ("IO0", "CAM_IO0"), ("GND", "GND"),
    ("VCC", N), ("U0R", "UART_TELEM"), ("U0T", N), ("GND", "GND")], 8.0, 29.0)
part("J2", "ESP32 DevKit 30p", FP_DEV, [
    ("EN", N), ("VP", N), ("VN", N), ("IO34", "LDR_TL"), ("IO35", "LDR_TR"), ("IO32", "LDR_BL"),
    ("IO33", "LDR_BR"), ("IO25", N), ("IO26", N), ("IO27", N), ("IO14", N), ("IO12", N),
    ("IO13", N), ("GND", "GND"), ("VIN", "+5V"),
    ("IO23", N), ("IO22", "I2C_SCL"), ("TX0", N), ("RX0", N), ("IO21", "I2C_SDA"),
    ("IO19", "SERVO_TILT"), ("IO18", "SERVO_PAN"), ("IO5", N), ("IO17_TX2", "UART_TELEM"),
    ("IO16_RX2", N), ("IO4", N), ("IO2", N), ("IO15", N), ("GND", "GND"), ("3V3", N)], 38.0, 10.0)
part("J3", "SX1278 Ra-02", FP_LORA, [
    ("GND", "GND"), ("MISO", "LORA_MISO"), ("MOSI", "LORA_MOSI"), ("SCK", "LORA_SCK"),
    ("NSS", "LORA_NSS"), ("RESET", "LORA_RST"), ("DIO5", N), ("GND", "GND"),
    ("ANT", "LORA_ANT"), ("GND", "GND"), ("DIO3", N), ("DIO4", N),
    ("3V3", "+3V3"), ("DIO0", N), ("DIO1", N), ("DIO2", N)], 68.0, 8.0, right_rev=True)
hdr("J4", "LoRa antenna", [("ANT", "LORA_ANT"), ("GND", "GND")], 85.0, 30.0)
hdr("J5", "Flash jumper (IO0-GND)", [("IO0", "CAM_IO0"), ("GND", "GND")], 70.0, 69.0)
hdr("J6", "Solar panel", [("PV+", "SOLAR_IN"), ("PV-", "GND")], 58.0, 69.0)
hdr("J7", "INA219 solar", [("VCC", "+3V3"), ("GND", "GND"), ("SCL", "I2C_SCL"), ("SDA", "I2C_SDA"),
                           ("VIN+", "SOLAR_IN"), ("VIN-", "SOLAR_OUT")], 34.0, 61.0)
hdr("J8", "TP4056 module", [("IN+", "SOLAR_OUT"), ("IN-", "GND"), ("OUT+", "TP_BP"), ("B+", "TP_BP"),
                            ("B-", "BAT_NEG"), ("OUT-", "GND")], 6.0, 69.0)
hdr("J9", "INA219 battery", [("VCC", "+3V3"), ("GND", "GND"), ("SCL", "I2C_SCL"), ("SDA", "I2C_SDA"),
                             ("VIN+", "TP_BP"), ("VIN-", "BAT_POS")], 52.0, 61.0)
hdr("J10", "18650 holder", [("BAT+", "BAT_POS"), ("BAT-", "BAT_NEG")], 64.0, 69.0)
hdr("J11", "Power switch", [("IN", "TP_BP"), ("OUT", "VBAT_SW")], 52.0, 69.0)
hdr("J12", "5V boost", [("VIN+", "VBAT_SW"), ("VIN-", "GND"), ("VOUT+", "+5V"), ("VOUT-", "GND")], 78.0, 61.0)
hdr("J13", "3.3V LDO", [("VIN", "+5V"), ("GND", "GND"), ("VOUT", "+3V3")], 70.0, 61.0)
hdr("J14", "BME280", [("VCC", "+3V3"), ("GND", "GND"), ("SCL", "I2C_SCL"), ("SDA", "I2C_SDA")], 6.0, 61.0)
hdr("J15", "MPU6050", [("VCC", "+3V3"), ("GND", "GND"), ("SCL", "I2C_SCL"), ("SDA", "I2C_SDA")], 20.0, 61.0)
hdr("J16", "Pan servo", [("GND", "GND"), ("V+", "+5V"), ("SIG", "SERVO_PAN")], 30.0, 69.0)
hdr("J17", "Tilt servo", [("GND", "GND"), ("V+", "+5V"), ("SIG", "SERVO_TILT")], 40.0, 69.0)
for i, (nm, nt) in enumerate([("TL", "LDR_TL"), ("TR", "LDR_TR"), ("BL", "LDR_BL"), ("BR", "LDR_BR")]):
    hdr(f"J{18+i}", f"LDR {nm}", [("3V3", "+3V3"), ("SIG", nt)], 12.0 + 8.0 * i, 77.0)
    part(f"R{1+i}", "10k", FP_R, [("1", nt), ("2", "GND")], 41.0 + 5.0 * i, 53.0, sym="R")
part("C1", "470uF", FP_CP, [("+", "+5V"), ("-", "GND")], 6.0, 53.0, sym="C")
part("C2", "470uF", FP_CP, [("+", "+5V"), ("-", "GND")], 17.0, 53.0, sym="C")
part("C3", "10uF", FP_C, [("1", "+3V3"), ("2", "GND")], 29.0, 53.0, sym="C")
part("C4", "100nF", FP_C, [("1", "+3V3"), ("2", "GND")], 34.0, 53.0, sym="C")
for i, (nt, lab) in enumerate([("+5V", "5V"), ("+3V3", "3V3"), ("TP_BP", "VBAT"), ("GND", "GND")]):
    part(f"TP{1+i}", f"TP {lab}", FP_TP, [("1", nt)], 62.0 + 5.0 * i, 53.0, sym="TP")
HOLES = [(5.0, 5.0), (85.0, 5.0), (5.0, 81.0), (85.0, 81.0)]
for i, (hx, hy) in enumerate(HOLES):
    PARTS.append(dict(ref=f"H{1+i}", value="M3", fp=FP_HOLE, pins=[("", None)], pos=(hx, hy),
                      sym=None, right_rev=False, board_only=True))
KEEPOUT = (66.0, 34.0, 90.0, 52.0)   # x1,y1,x2,y2 : LoRa antenna keep-out (no copper)

# nets
NETS = []
for p in PARTS:
    for _, n in p["pins"]:
        if n and n not in NETS: NETS.append(n)
NETS.remove("GND"); NETS.insert(0, "GND")
NETID = {n: i + 1 for i, n in enumerate(NETS)}
POWER_NETS = {"+5V", "+3V3", "TP_BP", "VBAT_SW", "BAT_POS", "BAT_NEG", "SOLAR_IN", "SOLAR_OUT"}

def pad_abs(p):
    fp = FPS[p["fp"]]; out = []
    for i, pad in enumerate(fp["pads"]):
        name, net = p["pins"][i]
        out.append(dict(ref=p["ref"], num=pad["num"], pname=name, net=net,
                        x=p["pos"][0] + pad["x"], y=p["pos"][1] + pad["y"], pad=pad))
    return out
ALLPADS = [a for p in PARTS for a in pad_abs(p)]

def pad_radius(pad):
    w, h = pad["size"]
    if pad["shape"] == "rect": return math.hypot(w, h) / 2
    if pad["shape"] == "roundrect": return math.hypot(w, h) / 2
    return max(w, h) / 2
def pad_layers(pad): return (0, 1) if pad["kind"] in ("thru", "npth") else (0,)

# ------------------------------------------------------------------ router
NX, NY = int(round(BW / G)) + 1, int(round(BH / G)) + 1
_disc = {}
def disc(r):
    k = round(r, 3)
    if k not in _disc:
        rc = int(math.ceil(r / G)) + 1
        d = [(dx, dy) for dx in range(-rc, rc + 1) for dy in range(-rc, rc + 1) if math.hypot(dx, dy) * G < r]
        _disc[k] = (np.array([a for a, _ in d]), np.array([b for _, b in d]))
    return _disc[k]
def stamp(arr, l, cx, cy, r, val=True):
    dx, dy = disc(r)
    xs, ys = cx + dx, cy + dy
    ok = (xs >= 0) & (xs < NX) & (ys >= 0) & (ys < NY)
    arr[l, xs[ok], ys[ok]] = val
def cell(x, y): return int(round(x / G)), int(round(y / G))

def static_base():
    base = np.zeros((2, NX, NY), bool)
    X = (np.arange(NX) * G)[:, None]; Y = (np.arange(NY) * G)[None, :]
    edge = (X < 1.0) | (X > BW - 1.0) | (Y < 1.0) | (Y > BH - 1.0)
    base[0] |= edge; base[1] |= edge
    for hx, hy in HOLES:
        m = (X - hx) ** 2 + (Y - hy) ** 2 < 3.0 ** 2
        base[0] |= m; base[1] |= m
    k = KEEPOUT
    m = (X >= k[0] - 0.8) & (X <= k[2]) & (Y >= k[1] - 0.8) & (Y <= k[3] + 0.8)
    base[0] |= m; base[1] |= m
    return base

def route_all(verbose=True, first=()):
    base = static_base()
    owner = -np.ones((2, NX, NY), np.int32)
    result = {}          # net -> dict(segs=[(layer,(x1,y1),(x2,y2))], vias=[(x,y)], failed=int)
    nets = [n for n in NETS if n != "GND"]
    bynet = {n: [a for a in ALLPADS if a["net"] == n] for n in nets}
    def hpwl(n):
        xs = [a["x"] for a in bynet[n]]; ys = [a["y"] for a in bynet[n]]
        return (max(xs) - min(xs)) + (max(ys) - min(ys))
    order = sorted([n for n in nets if n in POWER_NETS], key=lambda n: -len(bynet[n])) + \
            sorted([n for n in nets if n not in POWER_NETS], key=hpwl)
    order = [n for n in first if n in order] + [n for n in order if n not in first]
    for n in order:
        nid = NETID[n]; pads = bynet[n]
        width = PWR_TRK if n in POWER_NETS else TRK
        blk = base.copy()
        for a in ALLPADS:
            if a["net"] == n: continue
            R = pad_radius(a["pad"]) + CLR + PWR_TRK / 2 + (0.3 if a["pad"]["kind"] == "smd" else 0.0)
            cx, cy = cell(a["x"], a["y"])
            for l in pad_layers(a["pad"]): stamp(blk, l, cx, cy, R)
        free = (~blk) & ((owner == -1) | (owner == nid))
        pcell = {}
        for a in pads:
            cx, cy = cell(a["x"], a["y"])
            pcell[(cx, cy)] = a
            for l in pad_layers(a["pad"]): free[l, cx, cy] = True
        tree = np.zeros((2, NX, NY), bool)
        segs, vias, failed = [], [], 0
        first = pads[0]; cx, cy = cell(first["x"], first["y"])
        for l in pad_layers(first["pad"]): tree[l, cx, cy] = True
        conn = [first]; rest = pads[1:]
        while rest:
            # pick nearest unconnected pad to the tree pads
            best = min(rest, key=lambda a: min(abs(a["x"] - b["x"]) + abs(a["y"] - b["y"]) for b in conn))
            rest.remove(best)
            sx, sy = cell(best["x"], best["y"])
            starts = [(l * NX + sx) * NY + sy for l in pad_layers(best["pad"])]
            freef = free.ravel().tolist(); treef = tree.ravel().tolist()
            dist = {}; prev = {}; heap = []
            for s in starts: dist[s] = 0.0; heap.append((0.0, s))
            heapq.heapify(heap); goal = None; sset = set(starts)
            while heap:
                d, u = heapq.heappop(heap)
                if d > dist.get(u, 1e18): continue
                if treef[u] and u not in sset: goal = u; break
                y = u % NY; t = u // NY; x = t % NX; l = t // NX
                hc, vc = (1.0, 2.0) if l == 0 else (2.0, 1.0)
                cand = []
                if x > 0: cand.append((u - NY, hc))
                if x < NX - 1: cand.append((u + NY, hc))
                if y > 0: cand.append((u - 1, vc))
                if y < NY - 1: cand.append((u + 1, vc))
                cand.append((u + NX * NY if l == 0 else u - NX * NY, 20.0))
                for v, c in cand:
                    if not freef[v]: continue
                    nd = d + c
                    if nd < dist.get(v, 1e18):
                        dist[v] = nd; prev[v] = u; heapq.heappush(heap, (nd, v))
            if goal is None:
                failed += 1
                if verbose: print(f"  FAIL {n}: {best['ref']}.{best['num']}")
                continue
            path = [goal]
            while path[-1] not in sset: path.append(prev[path[-1]])
            path.reverse()
            nodes = []
            for u in path:
                y = u % NY; t = u // NY; nodes.append((t // NX, t % NX, y))
            # stamp + tree
            for (l, x, y) in nodes:
                tree[l, x, y] = True
                sub = owner[l, max(0, x - 1):x + 2, max(0, y - 1):y + 2]
                sub[sub == -1] = nid
                free[l, max(0, x - 1):x + 2, max(0, y - 1):y + 2] &= True
            free = (~blk) & ((owner == -1) | (owner == nid))
            for a in pads:
                cx, cy = cell(a["x"], a["y"])
                for l in pad_layers(a["pad"]): free[l, cx, cy] = True
            # runs -> segments / vias
            runs = []; cur = [nodes[0]]
            for nd_ in nodes[1:]:
                if nd_[0] != cur[-1][0]:
                    runs.append(cur); vias.append((nd_[1] * G, nd_[2] * G)); cur = [nd_]
                else: cur.append(nd_)
            runs.append(cur)
            for ri, run in enumerate(runs):
                pts = [(x * G, y * G) for (_, x, y) in run]
                if ri == 0:   # stub from actual pad centre
                    if abs(pts[0][0] - best["x"]) > 1e-6 or abs(pts[0][1] - best["y"]) > 1e-6:
                        pts.insert(0, (best["x"], best["y"]))
                if ri == len(runs) - 1:
                    gx, gy = nodes[-1][1], nodes[-1][2]
                    if (gx, gy) in pcell:
                        a = pcell[(gx, gy)]
                        if abs(pts[-1][0] - a["x"]) > 1e-6 or abs(pts[-1][1] - a["y"]) > 1e-6:
                            pts.append((a["x"], a["y"]))
                # compress collinear
                out = [pts[0]]
                for i in range(1, len(pts) - 1):
                    a0, b0, c0 = out[-1], pts[i], pts[i + 1]
                    if abs((b0[0] - a0[0]) * (c0[1] - b0[1]) - (b0[1] - a0[1]) * (c0[0] - b0[0])) > 1e-9: out.append(b0)
                out.append(pts[-1])
                for p0, p1 in zip(out, out[1:]):
                    if p0 != p1: segs.append((run[0][0], p0, p1, width))
            conn.append(best)
        result[n] = dict(segs=segs, vias=vias, failed=failed)
        if verbose: print(f"  routed {n:12s} pads={len(pads):2d} segs={len(segs):3d} vias={len(vias)} failed={failed}")
    return result

# ------------------------------------------------------------------ verification
def pt_seg(p, a, b):
    ax, ay = a; bx, by = b; px, py = p
    dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / L))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))
def ccw(a, b, c): return (c[1] - a[1]) * (b[0] - a[0]) > (b[1] - a[1]) * (c[0] - a[0])
def seg_seg(a, b, c, d):
    if ccw(a, c, d) != ccw(b, c, d) and ccw(a, b, c) != ccw(a, b, d): return 0.0
    return min(pt_seg(a, c, d), pt_seg(b, c, d), pt_seg(c, a, b), pt_seg(d, a, b))

def verify(res):
    objs = []   # (net, layer, kind, geom, radius)
    for a in ALLPADS:
        w, h = a["pad"]["size"]
        for l in pad_layers(a["pad"]):
            if a["pad"]["shape"] == "roundrect":
                nx_, ny_ = int(w / 0.1) + 1, int(h / 0.1) + 1
                for i in range(nx_ + 1):
                    for j in range(ny_ + 1):
                        px = a["x"] - w / 2 + w * i / nx_; py = a["y"] - h / 2 + h * j / ny_
                        if i in (0, nx_) or j in (0, ny_):
                            objs.append((a["net"], l, "c", (px, py), 0.0))
            elif a["pad"]["shape"] == "rect":
                objs.append((a["net"], l, "c", (a["x"], a["y"]), w / 2))   # true clearance to flat edges
            else:
                objs.append((a["net"], l, "c", (a["x"], a["y"]), max(w, h) / 2))
    for n, r in res.items():
        for (l, p0, p1, w) in r["segs"]: objs.append((n, l, "s", (p0, p1), w / 2))
        for v in r["vias"]:
            for l in (0, 1): objs.append((n, l, "c", v, VIA_D / 2))
    worst = 9e9; bad = []
    for i in range(len(objs)):
        ni, li, ki, gi, ri = objs[i]
        for j in range(i + 1, len(objs)):
            nj, lj, kj, gj, rj = objs[j]
            if li != lj or ni == nj and ni is not None: continue
            if ni is None and nj is None: continue
            if ki == "c" and kj == "c": d = math.hypot(gi[0] - gj[0], gi[1] - gj[1])
            elif ki == "c": d = pt_seg(gi, *gj)
            elif kj == "c": d = pt_seg(gj, *gi)
            else: d = seg_seg(gi[0], gi[1], gj[0], gj[1])
            gap = d - ri - rj
            if gap < worst: worst = gap
            if gap < CLR - 0.012: bad.append((ni, nj, li, round(gap, 3), gi, gj))
    # edge / keepout
    edge_bad = 0
    for n, r in res.items():
        for (l, p0, p1, w) in r["segs"]:
            for p in (p0, p1):
                if p[0] < 0.6 or p[0] > BW - 0.6 or p[1] < 0.6 or p[1] > BH - 0.6: edge_bad += 1
                if KEEPOUT[0] < p[0] < KEEPOUT[2] and KEEPOUT[1] < p[1] < KEEPOUT[3]: edge_bad += 1
    return worst, bad, edge_bad


def route_with_retries(tries=8):
    first = []
    best = None
    for t in range(tries):
        res = route_all(verbose=False, first=first)
        failed = [n for n, r in res.items() if r["failed"]]
        if best is None or len(failed) < best[0]: best = (len(failed), res)
        print(f"  attempt {t+1}: {len(failed)} failed nets {failed}")
        if not failed: break
        first = failed + [n for n in first if n not in failed]
    return best[1]

# ------------------------------------------------------------------ KiCad writers
def esc(s): return s.replace("\\", "\\\\").replace('"', '\\"')
EFF = '(effects (font (size 1 1) (thickness 0.15)))'

def pad_sexpr(pad, net=None, pinname=None, with_uuid=True):
    x, y = pad["x"], pad["y"]; w, h = pad["size"]
    if pad["kind"] == "thru":
        s = (f'(pad "{pad["num"]}" thru_hole {pad["shape"]} (at {f(x)} {f(y)}) (size {f(w)} {f(h)}) '
             f'(drill {f(pad["drill"])}) (layers "*.Cu" "*.Mask") (remove_unused_layers no)')
    elif pad["kind"] == "smd":
        if pad["shape"] == "circle":
            s = f'(pad "{pad["num"]}" smd circle (at {f(x)} {f(y)}) (size {f(w)} {f(h)}) (layers "F.Cu" "F.Paste" "F.Mask")'
        else:
            s = (f'(pad "{pad["num"]}" smd roundrect (at {f(x)} {f(y)}) (size {f(w)} {f(h)}) '
                 f'(layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio 0.25)')
    else:
        s = (f'(pad "{pad["num"]}" np_thru_hole circle (at {f(x)} {f(y)}) (size {f(w)} {f(h)}) '
             f'(drill {f(pad["drill"])}) (layers "*.Cu" "*.Mask")')
    if net:
        s += f' (net {NETID[net]} "{esc(net)}")'
    if pinname: s += f' (pinfunction "{esc(pinname)}")'
    if with_uuid: s += f' (uuid "{uid()}")'
    return s + ")"

def fp_body(fp, ref, value, pins=None, inst=False):
    L = []
    L.append(f'    (property "Reference" "{esc(ref)}" (at {f(fp["ref_at"][0])} {f(fp["ref_at"][1])} 0) (layer "F.SilkS") '
             + (f'(uuid "{uid()}") ' if inst else '') + EFF + ')')
    L.append(f'    (property "Value" "{esc(value)}" (at {f(fp["ref_at"][0])} {f(fp["ref_at"][1] + (fp["silk"][0][3] - fp["silk"][0][1] + 3 if fp["silk"] else 4))} 0) (layer "F.Fab") '
             + (f'(uuid "{uid()}") ' if inst else '') + EFF + ')')
    L.append(f'    (attr {fp["attr"] if fp["attr"] != "board_only" else "board_only exclude_from_pos_files exclude_from_bom"})')
    for (x1, y1, x2, y2) in fp["silk"]:
        L.append(f'    (fp_rect (start {f(x1)} {f(y1)}) (end {f(x2)} {f(y2)}) (stroke (width 0.12) (type solid)) (fill none) (layer "F.SilkS")'
                 + (f' (uuid "{uid()}")' if inst else '') + ')')
    for i, pad in enumerate(fp["pads"]):
        net = pins[i][1] if pins else None
        pn = pins[i][0] if pins else None
        L.append("    " + pad_sexpr(pad, net, pn, with_uuid=inst))
    return "\n".join(L)

def write_pretty():
    d = os.path.join(HERE, "satellite.pretty"); os.makedirs(d, exist_ok=True)
    for name, fp in FPS.items():
        txt = (f'(footprint "{name}"\n    (version 20240108)\n    (generator "pcbnew")\n    (generator_version "8.0")\n'
               f'    (layer "F.Cu")\n    (descr "{esc(fp["desc"])}")\n' + fp_body(fp, "REF**", name) + "\n)\n")
        open(os.path.join(d, name + ".kicad_mod"), "w").write(txt)
    open(os.path.join(HERE, "fp-lib-table"), "w").write(
        '(fp_lib_table\n  (version 7)\n  (lib (name "satellite")(type "KiCad")(uri "${KIPRJMOD}/satellite.pretty")(options "")(descr "Satellite carrier footprints"))\n)\n')
    open(os.path.join(HERE, "satellite.kicad_pro"), "w").write(
        '{\n  "meta": {\n    "filename": "satellite.kicad_pro",\n    "version": 1\n  }\n}\n')

def write_pcb(res):
    ox, oy = ORG
    L = ['(kicad_pcb', '  (version 20240108)', '  (generator "pcbnew")', '  (generator_version "8.0")',
         '  (general (thickness 1.6) (legacy_teardrops no))', '  (paper "A4")', '  (layers']
    for n_, nm, t, alias in [(0, "F.Cu", "signal", None), (31, "B.Cu", "signal", None),
                             (32, "B.Adhes", "user", "B.Adhesive"), (33, "F.Adhes", "user", "F.Adhesive"),
                             (34, "B.Paste", "user", None), (35, "F.Paste", "user", None),
                             (36, "B.SilkS", "user", "B.Silkscreen"), (37, "F.SilkS", "user", "F.Silkscreen"),
                             (38, "B.Mask", "user", None), (39, "F.Mask", "user", None),
                             (40, "Dwgs.User", "user", "User.Drawings"), (41, "Cmts.User", "user", "User.Comments"),
                             (42, "Eco1.User", "user", "User.Eco1"), (43, "Eco2.User", "user", "User.Eco2"),
                             (44, "Edge.Cuts", "user", None), (45, "Margin", "user", None),
                             (46, "B.CrtYd", "user", "B.Courtyard"), (47, "F.CrtYd", "user", "F.Courtyard"),
                             (48, "B.Fab", "user", None), (49, "F.Fab", "user", None)]:
        L.append(f'    ({n_} "{nm}" {t}' + (f' "{alias}"' if alias else "") + ")")
    L.append("  )")
    L.append('  (setup\n    (pad_to_mask_clearance 0)\n    (allow_soldermask_bridges_in_footprints no)\n  )')
    L.append('  (net 0 "")')
    for n in NETS: L.append(f'  (net {NETID[n]} "{esc(n)}")')
    for p in PARTS:
        fp = FPS[p["fp"]]
        L.append(f'  (footprint "satellite:{p["fp"]}"\n    (layer "F.Cu")\n    (uuid "{uid()}")\n'
                 f'    (at {f(ox + p["pos"][0])} {f(oy + p["pos"][1])})\n    (descr "{esc(fp["desc"])}")\n'
                 + fp_body(fp, p["ref"], p["value"], p["pins"], inst=True) + "\n  )")
    # tracks
    for n, r in res.items():
        for (l, p0, p1, w) in r["segs"]:
            L.append(f'  (segment (start {f(ox + p0[0])} {f(oy + p0[1])}) (end {f(ox + p1[0])} {f(oy + p1[1])}) '
                     f'(width {f(w)}) (layer "{"F.Cu" if l == 0 else "B.Cu"}") (net {NETID[n]}) (uuid "{uid()}"))')
        for v in r["vias"]:
            L.append(f'  (via (at {f(ox + v[0])} {f(oy + v[1])}) (size {f(VIA_D)}) (drill {f(VIA_DRILL)}) '
                     f'(layers "F.Cu" "B.Cu") (net {NETID[n]}) (uuid "{uid()}"))')
    # outline
    L.append(f'  (gr_rect (start {f(ox)} {f(oy)}) (end {f(ox + BW)} {f(oy + BH)}) (stroke (width 0.1) (type default)) '
             f'(fill none) (layer "Edge.Cuts") (uuid "{uid()}"))')
    L.append(f'  (gr_text "SATELLITE CARRIER REV A - CAMERA EDGE ^" (at {f(ox + 45)} {f(oy + 2.6)}) (layer "F.SilkS") (uuid "{uid()}") '
             f'(effects (font (size 1.2 1.2) (thickness 0.2))))')
    # GND pours
    for layer in ("F.Cu", "B.Cu"):
        m = 0.3
        L.append(f'  (zone (net {NETID["GND"]}) (net_name "GND") (layer "{layer}") (uuid "{uid()}") (hatch edge 0.5)\n'
                 f'    (connect_pads (clearance 0.3))\n    (min_thickness 0.25) (filled_areas_thickness no)\n'
                 f'    (fill (thermal_gap 0.3) (thermal_bridge_width 0.5))\n'
                 f'    (polygon (pts (xy {f(ox+m)} {f(oy+m)}) (xy {f(ox+BW-m)} {f(oy+m)}) (xy {f(ox+BW-m)} {f(oy+BH-m)}) (xy {f(ox+m)} {f(oy+BH-m)})))\n  )')
    # antenna keep-out (no copper)
    k = KEEPOUT
    for layer in ("F.Cu", "B.Cu"):
        L.append(f'  (zone (net 0) (net_name "") (layer "{layer}") (uuid "{uid()}") (name "LoRa antenna keepout") (hatch edge 0.5)\n'
                 f'    (connect_pads (clearance 0))\n    (min_thickness 0.25) (filled_areas_thickness no)\n'
                 f'    (keepout (tracks not_allowed) (vias not_allowed) (pads allowed) (copperpour not_allowed) (footprints allowed))\n'
                 f'    (fill (thermal_gap 0.5) (thermal_bridge_width 0.5))\n'
                 f'    (polygon (pts (xy {f(ox+k[0])} {f(oy+k[1])}) (xy {f(ox+k[2])} {f(oy+k[1])}) (xy {f(ox+k[2])} {f(oy+k[3])}) (xy {f(ox+k[0])} {f(oy+k[3])})))\n  )')
    L.append(")")
    open(os.path.join(HERE, "satellite.kicad_pcb"), "w").write("\n".join(L) + "\n")

# ---- schematic
SCH_ROOT = str(uuid.uuid5(_ns, "schematic-root"))
SCH_POS = {"J1": (50.8, 63.5), "J2": (139.7, 63.5), "J3": (228.6, 63.5), "J4": (304.8, 50.8), "J5": (304.8, 88.9),
           "J6": (38.1, 139.7), "J7": (101.6, 139.7), "J8": (165.1, 139.7), "J9": (228.6, 139.7),
           "J10": (292.1, 139.7), "J11": (355.6, 139.7),
           "J12": (38.1, 203.2), "J13": (101.6, 203.2), "J14": (165.1, 203.2), "J15": (228.6, 203.2),
           "J16": (292.1, 203.2), "J17": (355.6, 203.2),
           "J18": (38.1, 254.0), "J19": (101.6, 254.0), "J20": (165.1, 254.0), "J21": (228.6, 254.0),
           "R1": (292.1, 254.0), "R2": (304.8, 254.0), "R3": (317.5, 254.0), "R4": (330.2, 254.0),
           "C1": (342.9, 254.0), "C2": (355.6, 254.0), "C3": (368.3, 254.0), "C4": (381.0, 254.0),
           "TP1": (38.1, 281.94), "TP2": (101.6, 281.94), "TP3": (165.1, 281.94), "TP4": (228.6, 281.94)}
SFONT = '(effects (font (size 1.27 1.27)))'

def lib_symbols():
    out, done = [], set()
    for p in PARTS:
        if p["sym"] is None or p["sym"] in done: continue
        done.add(p["sym"]); s = p["sym"]
        props = lambda ref, val, y: (
            f'      (property "Reference" "{ref}" (at 0 {f(y)} 0) {SFONT})\n'
            f'      (property "Value" "{esc(val)}" (at 0 {f(-y)} 0) {SFONT})\n'
            f'      (property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))\n'
            f'      (property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))\n')
        head = f'    (symbol "satellite:{s}"\n      (pin_names (offset 1.016))\n      (exclude_from_sim no) (in_bom yes) (on_board yes)\n'
        if s == "R":
            body = (props("R", "R", 6.35) + f'      (symbol "{s}_0_1" (rectangle (start -1.016 2.54) (end 1.016 -2.54) (stroke (width 0.254) (type default)) (fill (type none))))\n'
                    f'      (symbol "{s}_1_1"\n        (pin passive line (at 0 5.08 270) (length 2.54) (name "1" {SFONT}) (number "1" {SFONT}))\n'
                    f'        (pin passive line (at 0 -5.08 90) (length 2.54) (name "2" {SFONT}) (number "2" {SFONT}))\n      )\n')
        elif s == "C":
            body = (props("C", "C", 6.35) + f'      (symbol "{s}_0_1" (polyline (pts (xy -2.54 0.635) (xy 2.54 0.635)) (stroke (width 0.508) (type default)) (fill (type none)))\n'
                    f'        (polyline (pts (xy -2.54 -0.635) (xy 2.54 -0.635)) (stroke (width 0.508) (type default)) (fill (type none))))\n'
                    f'      (symbol "{s}_1_1"\n        (pin passive line (at 0 3.81 270) (length 3.175) (name "+" {SFONT}) (number "1" {SFONT}))\n'
                    f'        (pin passive line (at 0 -3.81 90) (length 3.175) (name "-" {SFONT}) (number "2" {SFONT}))\n      )\n')
        elif s == "TP":
            body = (props("TP", "TP", 3.81) + f'      (symbol "{s}_0_1" (rectangle (start -2.54 1.27) (end 2.54 -1.27) (stroke (width 0.254) (type default)) (fill (type none))))\n'
                    f'      (symbol "{s}_1_1"\n        (pin passive line (at -5.08 0 0) (length 2.54) (name "1" {SFONT}) (number "1" {SFONT}))\n      )\n')
        else:
            pins = p["pins"]; n = len(pins)
            two = p["fp"] in (FP_CAM, FP_DEV, FP_LORA)
            if two:
                nn = n // 2
                left = [(str(i + 1), pins[i][0]) for i in range(nn)]
                right = [(str(nn + 1 + i), pins[nn + i][0]) for i in range(nn)]
                if p["right_rev"]: right = right[::-1]
                w = 25.4; H = nn * 2.54
            else:
                left = [(str(i + 1), pins[i][0]) for i in range(n)]; right = []
                w = 7.62; H = n * 2.54
            ytop = H / 2
            body = props(s[0] if s[0] == "J" else "J", p["value"], ytop + 2.54) if False else props("J", p["value"], ytop + 2.54)
            body += f'      (symbol "{s}_0_1" (rectangle (start {f(-w/2)} {f(ytop)}) (end {f(w/2)} {f(-ytop)}) (stroke (width 0.254) (type default)) (fill (type background))))\n'
            body += f'      (symbol "{s}_1_1"\n'
            for k, (num, nm) in enumerate(left):
                y = ytop - 1.27 - 2.54 * k
                body += f'        (pin passive line (at {f(-w/2-2.54)} {f(y)} 0) (length 2.54) (name "{esc(nm)}" {SFONT}) (number "{num}" {SFONT}))\n'
            for k, (num, nm) in enumerate(right):
                y = ytop - 1.27 - 2.54 * k
                body += f'        (pin passive line (at {f(w/2+2.54)} {f(y)} 180) (length 2.54) (name "{esc(nm)}" {SFONT}) (number "{num}" {SFONT}))\n'
            body += "      )\n"
        out.append(head + body + "    )")
    return "\n".join(out)

def sym_pin_layout(p):
    """-> list of (pad_index, dx, dy, direction) relative to symbol origin in SCHEMATIC coords (y down)."""
    s = p["sym"]; pins = p["pins"]; n = len(pins); out = []
    if s == "R" or s == "C":
        d = 5.08 if s == "R" else 3.81
        return [(0, 0, -d, "U"), (1, 0, d, "D")]
    if s == "TP": return [(0, -5.08, 0, "L")]
    two = p["fp"] in (FP_CAM, FP_DEV, FP_LORA)
    if two:
        nn = n // 2; w = 25.4; ytop = nn * 2.54 / 2
        for i in range(nn):
            out.append((i, -w / 2 - 2.54, -(ytop - 1.27 - 2.54 * i), "L"))
        order = list(range(nn)); 
        if p["right_rev"]: order = order[::-1]
        for k, i in enumerate(order):
            out.append((nn + i, w / 2 + 2.54, -(ytop - 1.27 - 2.54 * k), "R"))
    else:
        w = 7.62; ytop = n * 2.54 / 2
        for i in range(n):
            out.append((i, -w / 2 - 2.54, -(ytop - 1.27 - 2.54 * i), "L"))
    return out

def write_sch():
    L = ['(kicad_sch', '  (version 20231120)', '  (generator "eeschema")', '  (generator_version "8.0")',
         f'  (uuid "{SCH_ROOT}")', '  (paper "A3")',
         '  (title_block (title "Satellite model - carrier board") (date "2026-09-30") (rev "A")\n'
         '    (comment 1 "Generated by generate_kicad.py - verify pinouts against your modules"))',
         '  (lib_symbols', lib_symbols(), '  )']
    L.append(f'  (text "CubeSat-style satellite model carrier board. Modules plug into headers. '
             f'Nets are connected by labels; GND is a pour on both layers." (at 25.4 15.24 0) (effects (font (size 2 2)) (justify left bottom)) (uuid "{uid()}"))')
    for p in PARTS:
        if p["sym"] is None: continue
        X, Y = SCH_POS[p["ref"]]
        s = p["sym"]
        if s in ("R", "C", "TP"): ry = -8.0 if s != "TP" else -4.5
        else:
            n = len(p["pins"]); nn = n // 2 if p["fp"] in (FP_CAM, FP_DEV, FP_LORA) else n
            ry = -(nn * 2.54 / 2 + 5.08)
        L.append(f'  (symbol (lib_id "satellite:{s}") (at {f(X)} {f(Y)} 0) (unit 1) (exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no) (uuid "{uid()}")\n'
                 f'    (property "Reference" "{p["ref"]}" (at {f(X)} {f(Y+ry)} 0) (effects (font (size 1.27 1.27))))\n'
                 f'    (property "Value" "{esc(p["value"])}" (at {f(X)} {f(Y+ry+2.54)} 0) (effects (font (size 1.27 1.27))))\n'
                 f'    (property "Footprint" "satellite:{p["fp"]}" (at {f(X)} {f(Y)} 0) (effects (font (size 1.27 1.27)) (hide yes)))\n'
                 f'    (property "Datasheet" "" (at {f(X)} {f(Y)} 0) (effects (font (size 1.27 1.27)) (hide yes)))\n'
                 + "".join(f'    (pin "{FPS[p["fp"]]["pads"][i]["num"]}" (uuid "{uid()}"))\n' for i in range(len(p["pins"])))
                 + f'    (instances (project "satellite" (path "/{SCH_ROOT}" (reference "{p["ref"]}") (unit 1))))\n  )')
        for (i, dx, dy, dr) in sym_pin_layout(p):
            net = p["pins"][i][1]
            px, py = X + dx, Y + dy
            if net is None:
                L.append(f'  (no_connect (at {f(px)} {f(py)}) (uuid "{uid()}"))'); continue
            ex, ey = {"L": (px - 2.54, py), "R": (px + 2.54, py), "U": (px, py - 2.54), "D": (px, py + 2.54)}[dr]
            ang, just = {"L": (180, "right bottom"), "R": (0, "left bottom"), "U": (90, "left bottom"), "D": (270, "left bottom")}[dr]
            L.append(f'  (wire (pts (xy {f(px)} {f(py)}) (xy {f(ex)} {f(ey)})) (stroke (width 0) (type default)) (uuid "{uid()}"))')
            L.append(f'  (label "{esc(net)}" (at {f(ex)} {f(ey)} {ang}) (effects (font (size 1.27 1.27)) (justify {just})) (uuid "{uid()}"))')
    L.append('  (sheet_instances (path "/" (page "1")))')
    L.append(")")
    open(os.path.join(HERE, "satellite.kicad_sch"), "w").write("\n".join(L) + "\n")

def write_netlist_csv():
    path = os.path.join(HERE, "..", "netlist.csv")
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["net", "pins"])
        for n in NETS:
            w.writerow([n, ", ".join(f'{a["ref"]}.{a["num"]}({a["pname"]})' for a in ALLPADS if a["net"] == n)])

def preview(res, path):
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, Rectangle
    fig, ax = plt.subplots(figsize=(9, 8.6), dpi=130)
    ax.add_patch(Rectangle((0, 0), BW, BH, fill=False, ec="gold", lw=1.5))
    k = KEEPOUT; ax.add_patch(Rectangle((k[0], k[1]), k[2] - k[0], k[3] - k[1], fill=True, fc="#ffdddd", ec="red", ls="--", lw=.8, alpha=.6))
    ax.text((k[0] + k[2]) / 2, (k[1] + k[3]) / 2, "antenna\nkeep-out", ha="center", va="center", fontsize=7, color="red")
    for p in PARTS:
        fp = FPS[p["fp"]]
        for (x1, y1, x2, y2) in fp["silk"]:
            ax.add_patch(Rectangle((p["pos"][0] + x1, p["pos"][1] + y1), x2 - x1, y2 - y1, fill=False, ec="#888", lw=.6))
        ax.text(p["pos"][0] + fp["ref_at"][0], p["pos"][1] + fp["ref_at"][1] + (0 if p["ref"][0] != "H" else 0), p["ref"], fontsize=6, ha="center", color="navy")
    for n, r in res.items():
        for (l, p0, p1, w) in r["segs"]:
            ax.plot([p0[0], p1[0]], [p0[1], p1[1]], color="#d33" if l == 0 else "#36c", lw=w * 2.6, alpha=.75, solid_capstyle="round", zorder=3 + l)
        for v in r["vias"]: ax.add_patch(Circle(v, .4, fc="#2a2", ec="k", lw=.3, zorder=8))
    for a in ALLPADS:
        ax.add_patch(Circle((a["x"], a["y"]), a["pad"]["size"][0] / 2, fc="#e8c547" if a["net"] else "#bbb", ec="k", lw=.3, zorder=9))
    ax.set_xlim(-2, BW + 2); ax.set_ylim(BH + 2, -2); ax.set_aspect("equal")
    ax.set_title("Carrier board preview: red = F.Cu, blue = B.Cu, green = vias, GND = pour (not drawn)", fontsize=8)
    fig.savefig(path, bbbox_inches="tight") if False else fig.savefig(path)

if __name__ == "__main__":
    print("routing...")
    res = route_with_retries()
    worst, bad, eb = verify(res)
    nf = sum(r["failed"] for r in res.values())
    print(f"unrouted connections: {nf}; min clearance {worst:.3f} mm; violations {len(bad)}; edge/keepout {eb}")
    write_pretty(); write_pcb(res); write_sch(); write_netlist_csv()
    preview(res, os.path.join(HERE, "pcb-preview.png"))
    print("vias:", sum(len(r["vias"]) for r in res.values()),
          "segments:", sum(len(r["segs"]) for r in res.values()))
    print("written to", HERE)
