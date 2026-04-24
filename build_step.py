"""
Export STEP files for the Clements 47 CF vendor package.

Parts produced:
  - plate_pz.step  (+z neck plate: even-parity strings' holes)
  - plate_mz.step  (-z neck plate: odd-parity strings' holes, mirror of +z)

Future additions:
  - shoulder.step
  - chamber.step
  - base.step

Authoring frame: (x, y, z) with y increasing downward (SVG convention), z out
of the string plane. The vendor's CAD may flip y to use standard y-up; flag
this in the memo.

Usage:
  python3 build_step.py
"""

import math
import re
import sys
from pathlib import Path

import cadquery as cq

sys.path.insert(0, str(Path(__file__).parent))
import build_harp as bh
import soundbox.geometry as g
import inkscape_frame as ifr


# --- Geometry parameters -------------------------------------------------
PLATE_T = 2.0            # plate thickness in z (mm)
PLATE_GAP = 12.7         # gap between the two plates in z (mm)
Z_PZ_INNER = PLATE_GAP / 2                # inner face of +z plate: z = +6.35
Z_PZ_OUTER = Z_PZ_INNER + PLATE_T         # outer face of +z plate: z = +8.35
Z_MZ_INNER = -PLATE_GAP / 2
Z_MZ_OUTER = Z_MZ_INNER - PLATE_T

D_TUNER = 16.0           # tuner gear-post hole diameter (mm)
D_CLICKY = 6.5           # clicky shaft hole diameter (mm)

NECK_SVG = Path(__file__).parent / 'erand47jc_v3_opt.svg'


# --- SVG path parsing ----------------------------------------------------
def _parse_inkscape_path_to_authoring_points(path_d, dt=0.01):
    """Parse an SVG path 'd' attribute (Inkscape frame) into a dense list of
    (x, y) samples in AUTHORING FRAME."""
    tokens = re.findall(r'[mMcClLhHvVzZ]|-?[0-9.]+', path_d)
    samples = []
    x, y = 0.0, 0.0
    sx_, sy_ = 0.0, 0.0
    cmd = ''
    i = 0

    def bez(t, p0, p1, p2, p3):
        u = 1 - t
        return (u**3*p0[0] + 3*u**2*t*p1[0] + 3*u*t**2*p2[0] + t**3*p3[0],
                u**3*p0[1] + 3*u**2*t*p1[1] + 3*u*t**2*p2[1] + t**3*p3[1])

    while i < len(tokens):
        t = tokens[i]
        if t in 'mMcClLhHvVzZ':
            cmd = t
            i += 1
            continue
        if cmd == 'm':
            x += float(tokens[i]); y += float(tokens[i+1])
            sx_, sy_ = x, y
            samples.append((x, y))
            cmd = 'l'; i += 2
        elif cmd == 'M':
            x = float(tokens[i]); y = float(tokens[i+1])
            sx_, sy_ = x, y
            samples.append((x, y))
            cmd = 'L'; i += 2
        elif cmd == 'h':
            dx = float(tokens[i])
            for k in range(1, 21):
                samples.append((x + dx*k/20, y))
            x += dx; i += 1
        elif cmd == 'l':
            dx, dy = float(tokens[i]), float(tokens[i+1])
            for k in range(1, 21):
                samples.append((x + dx*k/20, y + dy*k/20))
            x += dx; y += dy; i += 2
        elif cmd == 'L':
            nx, ny = float(tokens[i]), float(tokens[i+1])
            for k in range(1, 21):
                samples.append((x + (nx-x)*k/20, y + (ny-y)*k/20))
            x, y = nx, ny; i += 2
        elif cmd == 'c':
            p0 = (x, y)
            p1 = (x + float(tokens[i]), y + float(tokens[i+1]))
            p2 = (x + float(tokens[i+2]), y + float(tokens[i+3]))
            p3 = (x + float(tokens[i+4]), y + float(tokens[i+5]))
            for k in range(1, int(1/dt) + 1):
                samples.append(bez(k * dt, p0, p1, p2, p3))
            x, y = p3; i += 6
        elif cmd == 'C':
            p0 = (x, y)
            p1 = (float(tokens[i]), float(tokens[i+1]))
            p2 = (float(tokens[i+2]), float(tokens[i+3]))
            p3 = (float(tokens[i+4]), float(tokens[i+5]))
            for k in range(1, int(1/dt) + 1):
                samples.append(bez(k * dt, p0, p1, p2, p3))
            x, y = p3; i += 6
        elif cmd in 'zZ':
            x, y = sx_, sy_; i += 1
        else:
            i += 1
    return samples


def get_plate_outline_authoring():
    """Return list of (x, y) points in authoring frame tracing the plate outline."""
    if not NECK_SVG.exists():
        raise FileNotFoundError(f"{NECK_SVG} not found; run optimize_v2.py first")
    content = NECK_SVG.read_text()
    # Brown path
    paths = re.findall(r'<path[\s\S]*?/>', content)
    target = None
    for p in paths:
        if '#8b4513' in p or '#8B4513' in p:
            target = p
            break
    if target is None:
        raise RuntimeError("No brown (#8B4513) path in v3 SVG")
    d_match = re.search(r'd="([^"]+)"', target)
    if not d_match:
        raise RuntimeError("No d= attribute on brown path")
    path_d = d_match.group(1)
    # v3 opt is in Inkscape frame — convert samples
    samples_ink = _parse_inkscape_path_to_authoring_points(path_d)
    samples_auth = [ifr.to_authoring(p) for p in samples_ink]
    return samples_auth


# --- Hole collection -----------------------------------------------------
def get_hole_positions():
    """Return list of dicts: {string_num, note, kind, plate, xy, diameter}.
    plate is '+z' (even string) or '-z' (odd string) per HANDOFF.md:50."""
    strings = bh.build_strings()
    holes = []
    for i, s in enumerate(strings, start=1):
        plate = '+z' if (i % 2 == 0) else '-z'
        if s.get('has_flat_buffer'):
            holes.append({
                'string_num': i, 'note': s['note'], 'kind': 'tuner',
                'plate': plate, 'xy': s['flat_buffer'], 'diameter': D_TUNER,
            })
        if s.get('has_nat_buffer'):
            holes.append({
                'string_num': i, 'note': s['note'], 'kind': 'nat',
                'plate': plate, 'xy': s['nat_buffer'], 'diameter': D_CLICKY,
            })
        if s.get('has_sharp_buffer'):
            holes.append({
                'string_num': i, 'note': s['note'], 'kind': 'sharp',
                'plate': plate, 'xy': s['sharp_buffer'], 'diameter': D_CLICKY,
            })
    return holes


# --- Build plate ---------------------------------------------------------
def build_plate(plate_side, outline, holes):
    """Build a single plate solid. plate_side is '+z' or '-z'."""
    # z-extent
    if plate_side == '+z':
        z_bot, z_top = Z_PZ_INNER, Z_PZ_OUTER
    else:
        z_bot, z_top = Z_MZ_OUTER, Z_MZ_INNER  # outer is more negative

    # Build outline as a closed wire via polyline
    # cadquery expects points as 2D tuples; use authoring (x, y) as (x, y) in CAD
    # Strip duplicate consecutive points (cadquery dislikes them)
    clean = []
    prev = None
    for pt in outline:
        if prev is None or (abs(pt[0] - prev[0]) > 0.01 or abs(pt[1] - prev[1]) > 0.01):
            clean.append(pt)
            prev = pt

    plate = (
        cq.Workplane("XY", origin=(0, 0, z_bot))
        .polyline(clean)
        .close()
        .extrude(z_top - z_bot)
    )

    # Cut holes for this side
    side_holes = [h for h in holes if h['plate'] == plate_side]
    for h in side_holes:
        x, y = h['xy']
        plate = (
            plate.faces(">Z" if plate_side == '+z' else "<Z")
            .workplane(origin=(x, y, (z_bot + z_top) / 2))
            .hole(h['diameter'])
        )

    return plate, len(side_holes)


def main():
    print("Building neck plates...")
    print(f"  Outline source: {NECK_SVG.name}")
    outline = get_plate_outline_authoring()
    print(f"  Outline: {len(outline)} sample points")
    holes = get_hole_positions()
    print(f"  Holes total: {len(holes)}")

    for side, fname in [('+z', 'plate_pz.step'), ('-z', 'plate_mz.step')]:
        plate, n_holes = build_plate(side, outline, holes)
        out_path = Path(__file__).parent / fname
        plate.val().exportStep(str(out_path))
        print(f"  Wrote {fname} ({n_holes} holes, plate at z ∈ "
              f"[{Z_PZ_INNER if side=='+z' else Z_MZ_OUTER:.2f}, "
              f"{Z_PZ_OUTER if side=='+z' else Z_MZ_INNER:.2f}])")

    print("Done.")


if __name__ == '__main__':
    main()
