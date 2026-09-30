#!/usr/bin/env python3
"""Reassemble LoRa image chunks and log telemetry from the ground-station ESP32."""
import argparse, csv, os, time
import serial

HEADER = ["time", "solarV", "solar_mA", "battV", "batt_mA", "tempC", "pressHPa",
          "humPct", "pitch", "roll", "pan", "tilt", "rssi", "snr"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", required=True)
    ap.add_argument("--baud", type=int, default=115200)
    ap.add_argument("--out", default="received")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    csv_path = os.path.join(args.out, "telemetry.csv")
    new = not os.path.exists(csv_path)
    f = open(csv_path, "a", newline="")
    w = csv.writer(f)
    if new:
        w.writerow(HEADER)

    images = {}  # id -> {"total": n, "chunks": {seq: bytes}, "updated": timestamp}
    ser = serial.Serial(args.port, args.baud, timeout=1)
    print("Listening on", args.port)
    try:
        while True:
            # Purge incomplete images older than 120 seconds
            now = time.time()
            stale_ids = [k for k, v in images.items() if now - v.get("updated", now) > 120]
            for k in stale_ids:
                print(f"Warning: Discarding incomplete image {k} after timeout")
                del images[k]

            line = ser.readline().decode(errors="ignore").strip()
            if not line:
                continue
            if not line.startswith("PKT,"):
                print(line)
                continue

            try:
                parts = line.split(",")
                if len(parts) != 4:
                    print("Malformed PKT line:", line)
                    continue
                _, hexdata, rssi, snr = parts
                d = bytes.fromhex(hexdata)
                if len(d) < 7:
                    print("Packet truncated (header < 7 bytes):", hexdata)
                    continue
                ptype, iid = d[0], d[1]
                seq = (d[2] << 8) | d[3]
                total = (d[4] << 8) | d[5]
                n = d[6]
                if len(d) < 7 + n:
                    print(f"Packet payload shorter than length field ({len(d) - 7} < {n})")
                    continue
                payload = d[7:7 + n]

                if ptype == 0x20:
                    fields = payload.decode(errors="ignore").strip().split(",")
                    if fields and fields[0] == "T":
                        telem_values = fields[1:]
                        w.writerow([time.strftime("%Y-%m-%d %H:%M:%S")] + telem_values + [rssi, snr])
                        f.flush()
                        print("telemetry:", telem_values)
                    else:
                        print("Unexpected telemetry payload:", payload)
                elif ptype == 0x10:
                    if total == 0 or seq >= total:
                        print(f"Invalid chunk sequence {seq}/{total} for image {iid}")
                        continue

                    # If this iid already exists with different total, reset it (new image session)
                    if iid in images and images[iid]["total"] != total:
                        print(f"Image {iid} total changed from {images[iid]['total']} to {total}, resetting")
                        del images[iid]

                    img = images.setdefault(iid, {"total": total, "chunks": {}, "updated": now})
                    img["chunks"][seq] = payload
                    img["updated"] = now
                    print(f"image {iid}: {len(img['chunks'])}/{total} (RSSI {rssi} dBm)")

                    # Only assemble when total unique chunks match and all indices 0..total-1 exist
                    if len(img["chunks"]) == img["total"] and all(i in img["chunks"] for i in range(img["total"])):
                        data = b"".join(img["chunks"][i] for i in range(img["total"]))
                        name = os.path.join(args.out, f"img_{iid:03d}_{int(time.time())}.jpg")
                        with open(name, "wb") as out:
                            out.write(data)
                        print("saved", name)
                        del images[iid]
            except Exception as e:
                print("Error processing packet:", e)
                continue
    except KeyboardInterrupt:
        print("\nStopping ground station...")
    finally:
        f.close()
        ser.close()


if __name__ == "__main__":
    main()
