"""
build_harp.py — single source of truth for the Erard 47-string harp SVG.

Run:
    python3 build_harp.py
Output:
    /mnt/user-data/outputs/erand47.svg
    /mnt/user-data/outputs/erand47.png

Everything is data-driven. To change the design, edit the CONFIG section
and re-run. No manual SVG editing.

Variables (user's naming convention):
    (s, i)   String identity. i=1..47 bass to treble. s is note name (c1..g7)
             where octaves increment at C (scientific pitch notation).
    pin      Tuning peg at top of string.
    flat     Flat-pedal engagement point (same as pin in new design).
    nat      Natural-pedal engagement point.
    sharp    Sharp-pedal engagement point.
    grom     Grommet (string termination at soundboard).
    CO       Column Outer — start of soundboard line (bass side, floor).
    NB       Neck Bottom.
    NT       Neck Top.
    ST       Soundboard Top.
"""
import math

# ============================================================================
# OUTPUT
# ============================================================================
import os as _os
_HERE = _os.path.dirname(_os.path.abspath(__file__))
OUTPUT_SVG = _os.path.join(_HERE, "erand47.svg")
OUTPUT_PNG = _os.path.join(_HERE, "erand47.png")

VIEWBOX = (0, 0, 952.24, 1928.20)
CANVAS_W = 444
CANVAS_H = 900
PNG_W, PNG_H = 888, 1800

R_BUFFER = 12.0
SEMITONE = 2 ** (1 / 12)
DOT_R = 2.6416
ANCHOR_R = 2.6416

# Renamed per soundbox handoff: the old CO is now CI (column Inner), and
# CO is the column-Outer × extended soundboard slope point on the floor plane.
CO = (12.700, 1803.910)     # column outer × soundboard slope extended
CI = (51.700, 1741.510)     # column inner × soundboard (was "CO" pre-handoff)
# NB sits at the y-coordinate of the south edge of the C1 sharp buffer,
# so the tangent line from NB to C1 sharp buffer is horizontal.
# C1 sharp buffer center y = 311.844 (computed via physics, stable).
# NB y = 311.844 + R_BUFFER = 323.844
NB = (12.700, 323.844)
NT = (12.700, 146.563)
ST = (838.784, 481.939)
FLOOR_Y = 1915.5            # floor plane (from soundbox handoff)

# ---------------------------------------------------------------------------
# HANDLE CONSTRAINTS — design decisions for the Bezier handles at corners.
# Each entry: corner_name -> (Hxa_direction, Hxb_direction) where each is
# either None (free), a unit vector (dx, dy), or a symbolic spec like
# "soundboard_slope".
# These are honored when the outline transitions from polyline to Bezier.
# ---------------------------------------------------------------------------
import math as _math
def _unit(v):
    n = _math.hypot(v[0], v[1])
    return (v[0]/n, v[1]/n) if n > 0 else (0.0, 0.0)

_SOUNDBOARD_DIR = _unit((ST[0] - CO[0], ST[1] - CO[1]))  # from CO toward ST

HANDLE_CONSTRAINTS = {
    # NB: entry from column (vertical down); exit along horizontal to C1 sharp.
    "NB": {
        "entry_dir": (0.0, -1.0),      # arriving from above along the column
        "exit_dir":  (1.0, 0.0),       # leaving horizontal (east) to C1 sharp
    },
    # ST: entry from last sharp buffer (free for now);
    # exit direction along the soundboard slope (from CO toward ST, reversed
    # to head outward from ST = ST - CO direction).
    "ST": {
        "entry_dir": None,
        "exit_dir":  _SOUNDBOARD_DIR,
    },
    # NT: arriving along harmonic curve (free); exit down the column vertical.
    "NT": {
        "entry_dir": None,
        "exit_dir":  (0.0, 1.0),       # heading south down the column
    },
}

# ============================================================================
# STRING TABLE (bass -> treble)
# ============================================================================
# (pin_x, pin_y, grommet_y)
_RAW_GEOM = [
    (101.700, 146.563, 1661.495), (119.632, 143.109, 1632.793),
    (137.565, 139.654, 1604.091), (155.523, 136.200, 1575.389),
    (173.455, 137.775, 1546.662), (191.387, 139.375, 1517.960),
    (209.320, 140.975, 1489.258), (227.252, 142.575, 1460.556),
    (245.210, 149.230, 1431.854), (263.142, 160.914, 1403.152),
    (281.075, 152.380, 1374.425), (299.007, 159.035, 1345.723),
    (316.432, 206.888, 1317.833), (333.856, 234.574, 1289.970),
    (351.280, 272.319, 1262.080), (368.705, 310.088, 1234.191),
    (385.113, 344.455, 1207.953), (401.522, 388.879, 1181.689),
    (417.905, 423.245, 1155.451), (433.297, 464.266, 1130.839),
    (448.664, 485.120, 1106.251), (464.031, 511.028, 1081.639),
    (479.423, 531.856, 1057.026), (494.790, 547.629, 1032.414),
    (510.157, 558.399, 1007.826), (525.524, 569.143,  983.214),
    (539.875, 576.484,  960.252), (554.226, 583.799,  937.291),
    (568.577, 586.085,  914.329), (582.928, 588.371,  891.367),
    (597.279, 590.657,  868.406), (611.630, 582.834,  845.444),
    (625.981, 585.120,  822.482), (639.316, 578.947,  801.147),
    (652.626, 572.775,  779.811), (665.961, 566.603,  758.500),
    (679.296, 560.431,  737.164), (692.606, 554.259,  715.853),
    (705.941, 548.086,  694.517), (719.250, 541.889,  673.181),
    (732.585, 530.687,  651.871), (745.920, 519.435,  630.535),
    (759.230, 508.234,  609.224), (772.565, 496.982,  587.888),
    (785.874, 485.780,  566.578), (799.209, 474.553,  545.242),
    (812.544, 463.327,  523.931),
]

# Scientific pitch notation: octave number increments at C.
_NOTE_SEQUENCE = [
    "C1","D1","E1","F1","G1","A1","B1",
    "C2","D2","E2","F2","G2","A2","B2",
    "C3","D3","E3","F3","G3","A3","B3",
    "C4","D4","E4","F4","G4","A4","B4",
    "C5","D5","E5","F5","G5","A5","B5",
    "C6","D6","E6","F6","G6","A6","B6",
    "C7","D7","E7","F7","G7",
]
assert len(_RAW_GEOM) == 47 == len(_NOTE_SEQUENCE)

_STRING_WIDTHS = [
    1.676,1.549,1.448,1.270,1.219,1.219,1.016,1.016,0.914,2.642,2.489,2.337,
    2.184,2.057,2.057,1.930,1.676,1.676,1.549,1.549,1.270,1.270,1.270,1.143,
    1.143,1.143,1.016,1.016,1.016,0.914,0.914,0.914,0.813,0.813,0.813,0.813,
    0.762,0.762,0.762,0.711,0.711,0.660,0.635,0.635,0.635,0.635,0.635,
]

# Flat buffer centers — from original SVG, preserved as data.
_FLAT_BUFFER_CENTERS = [
    (112.803,108.463),(130.735,105.009),(148.667,101.554),(166.600, 98.100),
    (182.558, 99.675),(200.490,101.275),(218.422,102.875),(236.355,104.475),
    (254.287,111.130),(272.245,122.814),(290.175,114.280),(308.107,120.935),
    (325.532,168.788),(342.956,196.474),(360.380,234.219),(377.805,271.988),
    (394.213,306.355),(410.622,350.779),(427.005,385.145),(442.397,426.166),
    (457.764,447.020),(473.131,472.928),(488.523,493.756),(503.890,509.529),
    (519.257,520.299),(534.624,531.043),(548.975,538.384),(563.326,545.699),
    (577.677,547.985),(592.028,550.271),(606.379,552.557),(620.730,544.734),
    (635.081,547.020),(648.416,540.847),(661.751,534.675),(675.061,528.503),
    (688.396,522.331),(701.706,516.159),(715.041,509.986),(728.350,503.789),
    (741.685,492.587),(755.020,481.335),(768.330,470.134),(781.665,458.882),
    (794.974,447.680),(808.309,436.453),(821.622,425.227),
]
assert len(_FLAT_BUFFER_CENTERS) == 47

# ============================================================================
# DESIGN CHOICES
# ============================================================================
# Set of (i, "flat"|"sharp") to omit buffer circle rendering for.
SKIPPED_BUFFERS = {
    (13, "flat"),   # A2 flat buffer omitted
    (5,  "flat"),   # G1 flat buffer omitted
    (6,  "flat"),   # A1 flat buffer omitted
    (7,  "flat"),   # B1 flat buffer omitted
    (9,  "flat"),   # D2 flat buffer omitted
    (10, "flat"),   # E2 flat buffer omitted
    (30, "flat"),   # D5 flat buffer omitted
    (31, "flat"),   # E5 flat buffer omitted
    (33, "flat"),   # G5 flat buffer omitted
    (34, "flat"),   # A5 flat buffer omitted
    (40, "flat"),   # G6 flat buffer omitted
    (8,  "sharp"),  # C2 sharp buffer omitted
    (9,  "sharp"),  # D2 sharp buffer omitted
    (11, "sharp"),  # F2 sharp buffer omitted
    (12, "sharp"),  # G2 sharp buffer omitted
    (21, "sharp"),  # B3 sharp buffer omitted
    (29, "sharp"),  # C5 sharp buffer omitted
    (30, "sharp"),  # D5 sharp buffer omitted
    (32, "sharp"),  # F5 sharp buffer omitted
}

# ============================================================================
# PHYSICS
# ============================================================================
def _natural(pin, grom):
    dx = pin[0] - grom[0]; dy = pin[1] - grom[1]
    L = math.hypot(dx, dy); ux, uy = dx / L, dy / L
    return (grom[0] + ux * L / SEMITONE, grom[1] + uy * L / SEMITONE)

def _sharp(pin, grom):
    dx = pin[0] - grom[0]; dy = pin[1] - grom[1]
    L = math.hypot(dx, dy); ux, uy = dx / L, dy / L
    return (grom[0] + ux * L / SEMITONE**2, grom[1] + uy * L / SEMITONE**2)

def _stroke_color(note):
    c = note[0]
    return "#c00000" if c == "C" else ("#1060d0" if c == "F" else "#888")

# ============================================================================
# MODEL
# ============================================================================
def build_strings():
    out = []
    for i, ((px, py, gy), note, width, fb) in enumerate(
            zip(_RAW_GEOM, _NOTE_SEQUENCE, _STRING_WIDTHS, _FLAT_BUFFER_CENTERS),
            start=1):
        pin = (px, py); grom = (px, gy)
        out.append({
            "s": note.lower(), "i": i, "note": note,
            "pin": pin, "flat": pin,
            "nat": _natural(pin, grom),
            "sharp": _sharp(pin, grom),
            "grom": grom,
            "flat_buffer": fb,
            "sharp_buffer": _sharp(pin, grom),
            "has_flat_buffer":  (i, "flat")  not in SKIPPED_BUFFERS,
            "has_sharp_buffer": (i, "sharp") not in SKIPPED_BUFFERS,
            "stroke": _stroke_color(note),
            "width": width,
        })
    return out

# ============================================================================
# SVG
# ============================================================================
STYLE = (
    ".str{fill:none;stroke-linecap:round}"
    ".key{stroke:#888;stroke-width:0.35;fill:none}"
    ".sb{stroke:#555;stroke-width:0.6;fill:none}"
    ".g{fill:#1f77b4}.n{fill:#2ca02c}.f{fill:#d62728}"
    ".s{fill:#ff7f0e}.p{fill:#9467bd}"
    ".sml{font-family:sans-serif;font-size:10px;fill:#333}"
    ".lbl{font-family:sans-serif;font-size:14px;fill:#222;font-weight:bold}"
    ".big{font-family:sans-serif;font-size:18px;fill:#000;font-weight:bold}"
    ".col{font-family:sans-serif;font-size:14px;fill:#000;font-weight:bold}"
)

def emit_svg(strings):
    parts = []
    vb = " ".join(str(v) for v in VIEWBOX)
    parts.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{CANVAS_W}" '
                 f'height="{CANVAS_H}" viewBox="{vb}" preserveAspectRatio="xMidYMid meet">')
    parts.append(f'<style>{STYLE}</style>')
    parts.append(f'<rect x="0" y="0" width="{VIEWBOX[2]}" height="{VIEWBOX[3]}" fill="#fff"/>')

    # Soundboard line CI -> ST (the actual soundboard; CO is the extended
    # slope point on the floor, used only for the soundbox loft).
    parts.append(f'<line class="sb" x1="{CI[0]:.3f}" y1="{CI[1]:.3f}" '
                 f'x2="{ST[0]:.3f}" y2="{ST[1]:.3f}"/>')

    # Column dashed centerline + label
    parts.append('<line x1="32.20" y1="38.10" x2="32.20" y2="1915.50" '
                 'stroke="#888" stroke-width="0.4" stroke-dasharray="3,2"/>')
    parts.append('<text x="32.20" y="976.80" text-anchor="middle" '
                 'transform="rotate(-90 32.20 976.80)" class="col">'
                 'COLUMN  39 x 1877 mm</text>')

    # Strings
    for s in strings:
        parts.append(f'<line class="str" stroke="{s["stroke"]}" stroke-width="{s["width"]}" '
                     f'x1="{s["grom"][0]}" y1="{s["grom"][1]}" '
                     f'x2="{s["pin"][0]}" y2="{s["pin"][1]}"/>')

    # Key lines (pin -> flat buffer center)
    for s in strings:
        parts.append(f'<line class="key" x1="{s["pin"][0]}" y1="{s["pin"][1]}" '
                     f'x2="{s["flat_buffer"][0]}" y2="{s["flat_buffer"][1]}"/>')

    # Flat buffers + pin dot + purple dot inside flat buffer
    for s in strings:
        fb = s["flat_buffer"]
        if s["has_flat_buffer"]:
            parts.append(f'<circle cx="{fb[0]}" cy="{fb[1]}" r="{R_BUFFER}" '
                         f'fill="none" stroke="#000" stroke-width="0.4"/>')
            # Small label INSIDE the circle — zoom in to read
            parts.append(
                f'<text x="{fb[0]:.3f}" y="{fb[1] - 5:.3f}" '
                f'text-anchor="middle" font-family="sans-serif" '
                f'font-size="5" fill="#000">{s["note"]}</text>'
            )
        # Purple pin-highlight dot at flat_buffer center (always drawn)
        parts.append(f'<circle class="p" cx="{fb[0]}" cy="{fb[1]}" r="{DOT_R}"/>')
        # Red pin/flat dot at pin position (always drawn)
        parts.append(f'<circle class="f" cx="{s["pin"][0]}" cy="{s["pin"][1]}" r="{DOT_R}"/>')

    # Natural + Sharp points (all 47 strings in new design)
    for s in strings:
        parts.append(f'<circle class="n" cx="{s["nat"][0]:.3f}" cy="{s["nat"][1]:.3f}" r="{DOT_R}"/>')
        if s["has_sharp_buffer"]:
            parts.append(f'<circle cx="{s["sharp"][0]:.3f}" cy="{s["sharp"][1]:.3f}" '
                         f'r="{R_BUFFER}" fill="none" stroke="#000" stroke-width="0.4"/>')
            # Small label INSIDE the sharp circle
            parts.append(
                f'<text x="{s["sharp"][0]:.3f}" y="{s["sharp"][1] - 5:.3f}" '
                f'text-anchor="middle" font-family="sans-serif" '
                f'font-size="5" fill="#000">{s["note"]}</text>'
            )
        parts.append(f'<circle class="s" cx="{s["sharp"][0]:.3f}" cy="{s["sharp"][1]:.3f}" r="{DOT_R}"/>')
        parts.append(f'<circle class="g" cx="{s["grom"][0]}" cy="{s["grom"][1]}" r="{DOT_R}"/>')

    # Note labels + index
    for s in strings:
        parts.append(f'<text x="{s["grom"][0]}" y="{s["grom"][1] + 32}" '
                     f'text-anchor="middle" class="lbl">{s["note"]}</text>')
        parts.append(f'<text x="{s["grom"][0] - 4}" y="{s["grom"][1] + 18}" '
                     f'class="sml">{s["i"]}</text>')

    # Anchor markers (NB, NT, ST): small black dots with labels
    for label, xy in [("NB", NB), ("NT", NT), ("ST", ST)]:
        parts.append(f'<circle cx="{xy[0]:.3f}" cy="{xy[1]:.3f}" r="{ANCHOR_R}" fill="#000"/>')
        parts.append(f'<text x="{xy[0] + 12:.3f}" y="{xy[1] + 6:.3f}" class="big">{label}</text>')

    parts.append("</svg>")
    return "\n".join(parts)

# ============================================================================
# MAIN
# ============================================================================
def main():
    strings = build_strings()
    svg = emit_svg(strings)
    with open(OUTPUT_SVG, "w") as f:
        f.write(svg)
    print(f"Wrote {OUTPUT_SVG}")

    try:
        import subprocess
        subprocess.run(["rsvg-convert", "-w", str(PNG_W), "-h", str(PNG_H),
                        "-o", OUTPUT_PNG, OUTPUT_SVG], check=True)
        print(f"Wrote {OUTPUT_PNG}")
    except Exception as e:
        print(f"PNG render failed: {e}")

    n_flat = sum(1 for s in strings if s["has_flat_buffer"])
    n_sharp = sum(1 for s in strings if s["has_sharp_buffer"])
    print(f"  {len(strings)} strings | {n_flat} flat buffers | {n_sharp} sharp buffers")
    if SKIPPED_BUFFERS:
        print(f"  skipped: {sorted(SKIPPED_BUFFERS)}")


if __name__ == "__main__":
    main()
