"""generate_schedules.py -- emit force_schedule.csv and hole_schedule.csv.

CF vendor handoff schedules. Re-run after editing strings.py or
build_harp.SKIPPED_BUFFERS to regenerate both CSVs.

force_schedule.csv: 47 rows, one per string. Linear-interpolated tension
from 52.693 lb (string 1, C1, bass) to 10.976 lb (string 47, G7, treble).

hole_schedule.csv: 141 rows, three per string (tuner / nat / sharp).
Tuner = 16 mm at flat_buffer; nat clicky = 6.5 mm at nat_buffer;
sharp clicky = 6.5 mm at sharp_buffer. EVEN strings -> +z plate,
ODD strings -> -z plate (per HANDOFF.md "hole alternation by string
parity"). Skipped buffers (per build_harp.SKIPPED_BUFFERS) are emitted
with skipped=true.
"""
import csv
import math
import os

from strings import STRINGS
import build_harp as bh


HERE = os.path.dirname(os.path.abspath(__file__))
FORCE_CSV = os.path.join(HERE, "force_schedule.csv")
HOLE_CSV = os.path.join(HERE, "hole_schedule.csv")

LB_PER_N = 4.44822
T_BASS_LB = 52.693   # string 1 (C1)
T_TREBLE_LB = 10.976  # string 47 (G7)
N_STRINGS = len(STRINGS)
assert N_STRINGS == 47


def tension_lb(i_one_indexed: int) -> float:
    """Linear interp across the 47 strings. i=1 -> bass, i=47 -> treble."""
    t = (i_one_indexed - 1) / (N_STRINGS - 1)  # 0 at bass, 1 at treble
    return T_BASS_LB + (T_TREBLE_LB - T_BASS_LB) * t


def unit(dx: float, dy: float):
    n = math.hypot(dx, dy)
    if n == 0.0:
        return (0.0, 0.0)
    return (dx / n, dy / n)


def write_force_schedule():
    rows = []
    for idx, s in enumerate(STRINGS, start=1):
        pin_x, pin_y = s.pin_x, s.pin_y
        grom_x, grom_y = s.pin_x, s.grommet_y  # straight-line; same x
        t_lb = tension_lb(idx)
        t_n = t_lb * LB_PER_N
        ux, uy = unit(pin_x - grom_x, pin_y - grom_y)
        fx, fy = t_n * ux, t_n * uy
        rows.append({
            "string_num": idx,
            "note": s.note,
            "pin_x": f"{pin_x:.6f}",
            "pin_y": f"{pin_y:.6f}",
            "grommet_x": f"{grom_x:.6f}",
            "grommet_y": f"{grom_y:.6f}",
            "diameter_in": f"{s.diameter:.6f}",
            "tension_lb": f"{t_lb:.6f}",
            "tension_N": f"{t_n:.6f}",
            "pull_dx": f"{ux:.9f}",
            "pull_dy": f"{uy:.9f}",
            "force_x": f"{fx:.6f}",
            "force_y": f"{fy:.6f}",
        })

    fieldnames = [
        "string_num", "note",
        "pin_x", "pin_y",
        "grommet_x", "grommet_y",
        "diameter_in",
        "tension_lb", "tension_N",
        "pull_dx", "pull_dy",
        "force_x", "force_y",
    ]
    with open(FORCE_CSV, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    return len(rows)


def write_hole_schedule():
    strings = bh.build_strings()
    assert len(strings) == 47

    rows = []
    fieldnames = [
        "string_num", "note", "hole_type",
        "diameter_mm", "plate",
        "hole_x", "hole_y",
        "skipped",
        "fiber_hint_dx", "fiber_hint_dy",
    ]

    for s, spec in zip(strings, STRINGS):
        idx = s["i"]
        note = s["note"]
        # Parity: EVEN -> +z (right), ODD -> -z (left).
        plate = "+z" if (idx % 2 == 0) else "-z"

        # String tangent unit vector: from grommet toward pin (same x, so
        # pull_dx == 0 and pull_dy == sign(pin_y - grommet_y) == -1 since
        # pin_y < grommet_y in SVG-down frame).
        gx, gy = s["grom"]
        px, py = s["pin"]
        ux, uy = unit(px - gx, py - gy)

        # Tuner at flat_buffer (16 mm). Skipped if (i, "flat") in SKIPPED
        # OR has_flat_buffer is False. Both are equivalent here because
        # has_flat_buffer mirrors SKIPPED_BUFFERS for the "flat" key.
        fb = s["flat_buffer"]
        skipped_flat = (not s["has_flat_buffer"]) or \
            ((idx, "flat") in bh.SKIPPED_BUFFERS)
        rows.append({
            "string_num": idx,
            "note": note,
            "hole_type": "tuner",
            "diameter_mm": "16",
            "plate": plate,
            "hole_x": f"{fb[0]:.6f}",
            "hole_y": f"{fb[1]:.6f}",
            "skipped": "true" if skipped_flat else "false",
            "fiber_hint_dx": f"{ux:.9f}",
            "fiber_hint_dy": f"{uy:.9f}",
        })

        # Nat clicky at nat_buffer (6.5 mm). Skipped only if
        # has_nat_buffer is False (no "nat" entries in SKIPPED_BUFFERS in
        # current design, but mirror the flag for safety).
        nb = s["nat_buffer"]
        skipped_nat = (not s["has_nat_buffer"]) or \
            ((idx, "nat") in bh.SKIPPED_BUFFERS)
        rows.append({
            "string_num": idx,
            "note": note,
            "hole_type": "nat",
            "diameter_mm": "6.5",
            "plate": plate,
            "hole_x": f"{nb[0]:.6f}",
            "hole_y": f"{nb[1]:.6f}",
            "skipped": "true" if skipped_nat else "false",
            "fiber_hint_dx": f"{ux:.9f}",
            "fiber_hint_dy": f"{uy:.9f}",
        })

        # Sharp clicky at sharp_buffer (6.5 mm).
        sb = s["sharp_buffer"]
        skipped_sharp = (not s["has_sharp_buffer"]) or \
            ((idx, "sharp") in bh.SKIPPED_BUFFERS)
        rows.append({
            "string_num": idx,
            "note": note,
            "hole_type": "sharp",
            "diameter_mm": "6.5",
            "plate": plate,
            "hole_x": f"{sb[0]:.6f}",
            "hole_y": f"{sb[1]:.6f}",
            "skipped": "true" if skipped_sharp else "false",
            "fiber_hint_dx": f"{ux:.9f}",
            "fiber_hint_dy": f"{uy:.9f}",
        })

    with open(HOLE_CSV, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    return len(rows)


if __name__ == "__main__":
    nf = write_force_schedule()
    nh = write_hole_schedule()
    print(f"Wrote {FORCE_CSV} ({nf} rows)")
    print(f"Wrote {HOLE_CSV}  ({nh} rows)")
    n_skipped = 0
    with open(HOLE_CSV, encoding="utf-8") as fh:
        r = csv.DictReader(fh)
        for row in r:
            if row["skipped"] == "true":
                n_skipped += 1
    print(f"  hole_schedule skipped rows: {n_skipped}")
