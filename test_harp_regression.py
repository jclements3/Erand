#!/usr/bin/env python3
"""test_harp_regression.py -- quick sanity regression for the Erand harp pipeline.

Run:
    python3 test_harp_regression.py

Prints "OK: N checks passed" on success, or a clear error and sys.exit(1)
on the first failure. No external test framework -- plain assert + print.

Checks (see CLAUDE.md for context):
    1. strings.py STRINGS list.
    2. build_harp.build_strings() and reference points.
    3. Buffer-position sanity (pin + offsets, _natural, _sharp; B4 spot-check).
    4. soundbox.geometry key scalars and tables.
    5. inkscape_frame constants and roundtrip.
    6. erand47jc_v2_opt.svg contains the brown neck path at the NBO anchor.
    7. build_views.py regenerates the five view SVGs (>1 KB each).
    8. build_harp.py writes erand47.svg with 141 R=8 buffer circles.
    9. neck_geodesic.py reports all 47 nat buffers inside polyline envelope.
"""

import math
import os
import subprocess
import sys


HERE = os.path.dirname(os.path.abspath(__file__))


def fail(check, msg, actual=None, expected=None):
    print(f"FAIL [{check}]: {msg}")
    if actual is not None or expected is not None:
        print(f"   actual:   {actual!r}")
        print(f"   expected: {expected!r}")
    sys.exit(1)


def approx_eq(a, b, tol):
    return abs(a - b) <= tol


def tuple_approx_eq(a, b, tol):
    return len(a) == len(b) and all(approx_eq(x, y, tol) for x, y in zip(a, b))


# ----------------------------------------------------------------------------
# 1. Strings config
# ----------------------------------------------------------------------------
def check_strings_config():
    name = "1 strings config"
    try:
        from strings import STRINGS
    except Exception as e:
        fail(name, f"could not import STRINGS: {e}")
    if len(STRINGS) != 47:
        fail(name, "STRINGS length mismatch", len(STRINGS), 47)
    if STRINGS[0].note != "C1":
        fail(name, "first string note mismatch", STRINGS[0].note, "C1")
    if STRINGS[-1].note != "G7":
        fail(name, "last string note mismatch", STRINGS[-1].note, "G7")
    return STRINGS


# ----------------------------------------------------------------------------
# 2. build_harp integrity
# ----------------------------------------------------------------------------
def check_build_harp_integrity():
    name = "2 build_harp integrity"
    try:
        import build_harp as bh
    except Exception as e:
        fail(name, f"could not import build_harp: {e}")
    ss = bh.build_strings()
    if len(ss) != 47:
        fail(name, "build_strings length mismatch", len(ss), 47)
    for idx, s in enumerate(ss, start=1):
        for key in ("flat_buffer", "nat_buffer", "sharp_buffer"):
            if key not in s:
                fail(name, f"string #{idx} ({s.get('note')}) missing key {key!r}",
                     sorted(s.keys()), key)
    if bh.R_BUFFER != 8.0:
        fail(name, "R_BUFFER mismatch", bh.R_BUFFER, 8.0)
    for label, pt in [("NB", bh.NB), ("NT", bh.NT), ("ST", bh.ST)]:
        if not (isinstance(pt, tuple) and len(pt) == 2
                and all(isinstance(v, float) for v in pt)):
            fail(name, f"{label} must be a tuple of two floats", pt, "(float, float)")
    return bh, ss


# ----------------------------------------------------------------------------
# 3. Buffer-position sanity
# ----------------------------------------------------------------------------
def check_buffer_positions(bh, ss):
    name = "3 buffer-position sanity"
    SEMITONE = 2 ** (1 / 12)
    for s in ss:
        i = s["i"]
        pin = s["pin"]; grom = s["grom"]

        # Flat buffer: pin + FLAT_BUFFER_OFFSET (bass override for strings 1..4).
        dx, dy = (bh.FLAT_BUFFER_OFFSET_BASS
                  if i <= bh.FLAT_BUFFER_BASS_MAX_STRING
                  else bh.FLAT_BUFFER_OFFSET)
        expected_flat = (pin[0] + dx, pin[1] + dy)
        if not tuple_approx_eq(s["flat_buffer"], expected_flat, 1e-6):
            fail(name, f"string {s['note']} flat_buffer mismatch",
                 s["flat_buffer"], expected_flat)

        # Nat buffer: grommet + (pin - grommet) / SEMITONE.
        ddx = pin[0] - grom[0]; ddy = pin[1] - grom[1]
        L = math.hypot(ddx, ddy)
        ux, uy = ddx / L, ddy / L
        expected_nat = (grom[0] + ux * L / SEMITONE,
                        grom[1] + uy * L / SEMITONE)
        if not tuple_approx_eq(s["nat_buffer"], expected_nat, 1e-6):
            fail(name, f"string {s['note']} nat_buffer mismatch",
                 s["nat_buffer"], expected_nat)

        # Sharp buffer: grommet + (pin - grommet) / SEMITONE**2.
        expected_sharp = (grom[0] + ux * L / SEMITONE**2,
                          grom[1] + uy * L / SEMITONE**2)
        if not tuple_approx_eq(s["sharp_buffer"], expected_sharp, 1e-6):
            fail(name, f"string {s['note']} sharp_buffer mismatch",
                 s["sharp_buffer"], expected_sharp)

    # B4 spot-check.
    b4 = next(s for s in ss if s["note"] == "B4")
    if not tuple_approx_eq(b4["pin"], (554.226, 583.799), 1e-6):
        fail(name, "B4 pin mismatch", b4["pin"], (554.226, 583.799))
    if not approx_eq(b4["nat_buffer"][1], 603.639, 1e-3):
        fail(name, "B4 nat_buffer y mismatch", b4["nat_buffer"][1], 603.639)
    if not approx_eq(b4["sharp_buffer"][1], 622.365, 1e-3):
        fail(name, "B4 sharp_buffer y mismatch", b4["sharp_buffer"][1], 622.365)


# ----------------------------------------------------------------------------
# 4. Soundbox geometry
# ----------------------------------------------------------------------------
def check_soundbox_geometry():
    name = "4 soundbox geometry"
    try:
        from soundbox import geometry as g
    except Exception as e:
        fail(name, f"could not import soundbox.geometry: {e}")
    if not approx_eq(g.L_CO_ST, 1558.858, 0.01):
        fail(name, "L_CO_ST mismatch", g.L_CO_ST, 1558.858)
    if len(g.GROMMETS) != 47:
        fail(name, "GROMMETS length mismatch", len(g.GROMMETS), 47)
    if g.CO[0] != 12.7:
        fail(name, "CO[0] mismatch", g.CO[0], 12.7)
    if not approx_eq(g.ST[1], 481.939, 1e-6):
        fail(name, "ST[1] mismatch", g.ST[1], 481.939)
    if g.FLOOR_Y != 1915.5:
        fail(name, "FLOOR_Y mismatch", g.FLOOR_Y, 1915.5)
    if not approx_eq(g.Y_ST_HORIZ, 481.939, 1e-6):
        fail(name, "Y_ST_HORIZ mismatch", g.Y_ST_HORIZ, 481.939)


# ----------------------------------------------------------------------------
# 5. Inkscape frame
# ----------------------------------------------------------------------------
def check_inkscape_frame():
    name = "5 inkscape frame"
    try:
        from inkscape_frame import (
            INKSCAPE_DX, INKSCAPE_DY, to_authoring, to_inkscape,
        )
    except Exception as e:
        fail(name, f"could not import inkscape_frame: {e}")
    if INKSCAPE_DX != 51.9:
        fail(name, "INKSCAPE_DX mismatch", INKSCAPE_DX, 51.9)
    if INKSCAPE_DY != 81.27:
        fail(name, "INKSCAPE_DY mismatch", INKSCAPE_DY, 81.27)
    got = to_authoring((0, 0))
    if not tuple_approx_eq(got, (51.9, 81.27), 1e-9):
        fail(name, "to_authoring((0,0)) mismatch", got, (51.9, 81.27))
    rt = to_authoring(to_inkscape((10, 20)))
    if not tuple_approx_eq(rt, (10, 20), 1e-9):
        fail(name, "roundtrip to_authoring(to_inkscape((10,20))) mismatch",
             rt, (10, 20))


# ----------------------------------------------------------------------------
# 6. Neck path exists in v2_opt svg
# ----------------------------------------------------------------------------
def check_neck_path():
    name = "6 neck path exists"
    path = os.path.join(HERE, "erand47jc_v2_opt.svg")
    if not os.path.exists(path):
        fail(name, f"{path} not found")
    with open(path, "r") as f:
        text = f.read()
    # The v2_opt SVG uses attributes split across lines; we just need to
    # see both the stroke color and the expected "d" prefix somewhere.
    if 'stroke="#8b4513"' not in text:
        fail(name, "no element with stroke=\"#8b4513\" found in erand47jc_v2_opt.svg")
    if 'd="M -39.200,242.569' not in text:
        fail(name, "no path with d starting 'M -39.200,242.569' (NBO anchor) found")


# ----------------------------------------------------------------------------
# 7. View regeneration via build_views.py
# ----------------------------------------------------------------------------
def check_view_regeneration():
    name = "7 view regeneration"
    proc = subprocess.run(
        [sys.executable, os.path.join(HERE, "build_views.py")],
        cwd=HERE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if proc.returncode != 0:
        print(f"FAIL [{name}]: build_views.py exited with code {proc.returncode}")
        print("---- stdout ----")
        sys.stdout.write(proc.stdout.decode("utf-8", errors="replace"))
        print("---- stderr ----")
        sys.stdout.write(proc.stderr.decode("utf-8", errors="replace"))
        sys.exit(1)
    for fname in ("erand47_side.svg", "erand47_top.svg",
                  "erand47_front.svg", "erand47_rear.svg",
                  "erand47_sbf.svg"):
        p = os.path.join(HERE, fname)
        if not os.path.exists(p):
            fail(name, f"{fname} missing after build_views.py")
        size = os.path.getsize(p)
        if size <= 1024:
            fail(name, f"{fname} too small ({size} bytes <= 1024)",
                 size, "> 1024")


# ----------------------------------------------------------------------------
# 8. Buffer count in erand47.svg
# ----------------------------------------------------------------------------
def check_buffer_count_in_svg():
    name = "8 buffer count in erand47.svg"
    proc = subprocess.run(
        [sys.executable, os.path.join(HERE, "build_harp.py")],
        cwd=HERE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if proc.returncode != 0:
        print(f"FAIL [{name}]: build_harp.py exited with code {proc.returncode}")
        print("---- stdout ----")
        sys.stdout.write(proc.stdout.decode("utf-8", errors="replace"))
        print("---- stderr ----")
        sys.stdout.write(proc.stderr.decode("utf-8", errors="replace"))
        sys.exit(1)
    path = os.path.join(HERE, "erand47.svg")
    if not os.path.exists(path):
        fail(name, "erand47.svg not found after build_harp.py")
    with open(path, "r") as f:
        text = f.read()
    # build_harp writes R=8 buffer circles as r="8.0" (molded CF holes).
    count = text.count('r="8.0"')
    expected = 141  # 47 strings * 3 buffer types (flat + nat + sharp)
    if count != expected:
        fail(name, "R=8 buffer circle count mismatch", count, expected)


# ----------------------------------------------------------------------------
# 9. Nat-buffer feasibility from neck_geodesic.py
# ----------------------------------------------------------------------------
def check_nat_buffer_feasibility():
    name = "9 nat-buffer feasibility"
    proc = subprocess.run(
        [sys.executable, os.path.join(HERE, "neck_geodesic.py")],
        cwd=HERE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if proc.returncode != 0:
        print(f"FAIL [{name}]: neck_geodesic.py exited with code {proc.returncode}")
        print("---- stdout ----")
        sys.stdout.write(proc.stdout.decode("utf-8", errors="replace"))
        print("---- stderr ----")
        sys.stdout.write(proc.stderr.decode("utf-8", errors="replace"))
        sys.exit(1)
    out = proc.stdout.decode("utf-8", errors="replace")
    if "all 47 nat buffers inside polyline envelope" not in out:
        print(f"FAIL [{name}]: expected substring not in stdout")
        print("---- stdout ----")
        sys.stdout.write(out)
        sys.exit(1)


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------
def main():
    check_strings_config()
    bh, ss = check_build_harp_integrity()
    check_buffer_positions(bh, ss)
    check_soundbox_geometry()
    check_inkscape_frame()
    check_neck_path()
    check_view_regeneration()
    check_buffer_count_in_svg()
    check_nat_buffer_feasibility()
    print("OK: 9 checks passed")


if __name__ == "__main__":
    main()
