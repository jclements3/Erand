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

VIEWBOX = (-40, 0, 1000, 1940)
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
# ST matched to soundbox Y_ST_HORIZ = 481.939 so the neck outline is
# flush with the chamber's soundboard-face interface. The previous
# lowering to 494.265 (for F7 sharp-buffer tangency) created a 12.33 mm
# gap against the soundbox; F7 sharp buffer is now skipped instead
# (see SKIPPED_BUFFERS below) because the horizontal ST->BT line at
# y=481.939 penetrates it.
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

# Flat buffer center offset relative to the pin. The flat buffer sits
# +9.1 mm east and -38.1 mm north of the pin for strings 5..47. The four
# bass-most strings (C1..F1) instead use +11.1 mm east: they share the same
# soundboard/pin register but have wider pin spacing at the bass end, so
# bumping the flat-buffer column a further 2 mm east keeps the buffer chain
# clear of the adjacent sharp-buffer row. (Collapsing them to the uniform
# 9.1 mm offset would shift those four centers by 2.00 mm each — at the edge
# of what the neck-feasibility tolerance absorbs, so we keep the override.)
#
# Residual drift vs. the literal historical table, for the uniform rows:
#   F1 (11.077 vs 11.100):   0.023 mm   <- bass override row
#   D2 ( 9.077 vs  9.100):   0.023 mm
#   B5 ( 9.125 vs  9.100):   0.025 mm
#   G7 ( 9.078 vs  9.100):   0.022 mm
# All sub-millimeter; absorbed by the neck-optimizer's 12 mm buffer margin.
FLAT_BUFFER_OFFSET = (9.1, -38.1)             # mm, relative to pin (default)
FLAT_BUFFER_OFFSET_BASS = (11.1, -38.1)       # mm, strings 1..4 (C1..F1)
FLAT_BUFFER_BASS_MAX_STRING = 4               # last string to use the bass offset

def _flat_buffer_from_pin(i, pin):
    """Compute flat-buffer center from pin position and string index (1-based)."""
    dx, dy = (FLAT_BUFFER_OFFSET_BASS if i <= FLAT_BUFFER_BASS_MAX_STRING
              else FLAT_BUFFER_OFFSET)
    return (pin[0] + dx, pin[1] + dy)

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
    (46, "sharp"),  # F7 sharp buffer omitted: ST horizontal line at y=481.939 penetrates it (neck-soundbox flush)
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
    for i, ((px, py, gy), note, width) in enumerate(
            zip(_RAW_GEOM, _NOTE_SEQUENCE, _STRING_WIDTHS),
            start=1):
        pin = (px, py); grom = (px, gy)
        fb = _flat_buffer_from_pin(i, pin)
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

    # ------------------------------------------------------------------
    # Soundbox silhouette — limaçon chamber projected onto the xy plane.
    # Uses soundbox/geometry.py as source of truth (CO, CI, u, n, D(s'),
    # clearance stations, floor). Adds:
    #   - floor line y = FLOOR_Y
    #   - CO, CI, BT reference points with labels
    #   - extended soundboard slope CI->CO and ST->S_TREBLE_CLEAR projection
    #   - bulge tip locus, clipped above the floor
    #   - ST->BT horizontal at y = 481.94 (neck/chamber interface)
    # ------------------------------------------------------------------
    import sys as _sys
    _sb_dir = _os.path.join(_HERE, 'soundbox')
    if _sb_dir not in _sys.path:
        _sys.path.insert(0, _sb_dir)
    try:
        import geometry as _sbg  # type: ignore
    except Exception:
        _sbg = None

    if _sbg is not None:
        SB_COLOR = "#0a7"
        # Floor line
        parts.append(
            f'<line x1="0" y1="{_sbg.FLOOR_Y:.3f}" x2="{VIEWBOX[2]}" '
            f'y2="{_sbg.FLOOR_Y:.3f}" stroke="#888" stroke-width="0.6" '
            f'stroke-dasharray="4,3"/>'
        )
        # CO and CI markers
        for label, pt in (("CO", _sbg.CO), ("CI", _sbg.CI)):
            parts.append(
                f'<circle cx="{pt[0]:.3f}" cy="{pt[1]:.3f}" '
                f'r="{ANCHOR_R}" fill="{SB_COLOR}"/>'
            )
            parts.append(
                f'<text x="{pt[0] + 12:.3f}" y="{pt[1] + 6:.3f}" '
                f'class="big">{label}</text>'
            )
        # Extended soundboard slope CI -> CO (dashed).
        parts.append(
            f'<line x1="{CI[0]:.3f}" y1="{CI[1]:.3f}" '
            f'x2="{_sbg.CO[0]:.3f}" y2="{_sbg.CO[1]:.3f}" '
            f'stroke="{SB_COLOR}" stroke-width="0.6" stroke-dasharray="4,3"/>'
        )
        # Extended soundboard past ST to treble-clear station (dashed).
        _tc_x = _sbg.CO[0] + _sbg.S_TREBLE_CLEAR * _sbg.u[0]
        _tc_y = _sbg.CO[1] + _sbg.S_TREBLE_CLEAR * _sbg.u[1]
        parts.append(
            f'<line x1="{ST[0]:.3f}" y1="{ST[1]:.3f}" '
            f'x2="{_tc_x:.3f}" y2="{_tc_y:.3f}" '
            f'stroke="{SB_COLOR}" stroke-width="0.6" stroke-dasharray="4,3"/>'
        )
        # Bulge tip locus: chamber silhouette on the +n side of the
        # soundboard, clipped where it goes past floor.
        _N = 400
        _pts = []
        for _i in range(_N):
            _s = _sbg.S_BASS_CLEAR + (
                _sbg.S_TREBLE_CLEAR - _sbg.S_BASS_CLEAR
            ) * _i / (_N - 1)
            _b = _sbg.b_of(_s)
            _fx = _sbg.CO[0] + _s * _sbg.u[0]
            _fy = _sbg.CO[1] + _s * _sbg.u[1]
            _tx = _fx + 4 * _b * _sbg.n[0]
            _ty = _fy + 4 * _b * _sbg.n[1]
            _pts.append((_tx, _ty))
        # Break into runs above the floor to avoid drawing a clamp line.
        _run = []
        for _x, _y in _pts:
            if _y <= _sbg.FLOOR_Y:
                _run.append((_x, _y))
            elif _run:
                _d = f"M {_run[0][0]:.3f} {_run[0][1]:.3f} " + " ".join(
                    f"L {px:.3f} {py:.3f}" for px, py in _run[1:]
                )
                parts.append(
                    f'<path d="{_d}" fill="none" stroke="{SB_COLOR}" '
                    f'stroke-width="0.9"/>'
                )
                _run = []
        if len(_run) >= 2:
            _d = f"M {_run[0][0]:.3f} {_run[0][1]:.3f} " + " ".join(
                f"L {px:.3f} {py:.3f}" for px, py in _run[1:]
            )
            parts.append(
                f'<path d="{_d}" fill="none" stroke="{SB_COLOR}" '
                f'stroke-width="0.9"/>'
            )
        # BT = east end of the bulge tip locus — the single-point tangency
        # where the limaçon bulge at S_TREBLE_CLEAR touches the ST horizontal
        # plane (y = 481.94). Computed directly from the soundbox geometry
        # rather than hardcoded from interfaces.md, so BT lands exactly at
        # the visible east end of the green silhouette.
        # BT = east end of bulge tip locus at the NECK's ST horizontal
        # (y = ST[1] = 494.265). Numerically find s_p > S_PEAK such that
        # bulge_tip_y(s_p) = ST[1], then compute the tip x.
        def _find_bt():
            target_y = ST[1]
            lo, hi = _sbg.S_PEAK, _sbg.S_TREBLE_FINAL
            for _ in range(60):
                mid = 0.5 * (lo + hi)
                y_mid = _sbg.bulge_tip_point(mid)[1]
                if y_mid < target_y:
                    hi = mid
                else:
                    lo = mid
            s_solution = 0.5 * (lo + hi)
            tip = _sbg.bulge_tip_point(s_solution)
            return (tip[0], tip[1])
        _BT = _find_bt()
        parts.append(
            f'<line x1="{ST[0]:.3f}" y1="{ST[1]:.3f}" '
            f'x2="{_BT[0]:.3f}" y2="{_BT[1]:.3f}" '
            f'stroke="{SB_COLOR}" stroke-width="0.6" stroke-dasharray="4,3"/>'
        )
        parts.append(
            f'<circle cx="{_BT[0]:.3f}" cy="{_BT[1]:.3f}" '
            f'r="{ANCHOR_R}" fill="{SB_COLOR}"/>'
        )
        parts.append(
            f'<text x="{_BT[0] + 12:.3f}" y="{_BT[1] + 6:.3f}" '
            f'class="big">BT</text>'
        )

        # --- Blue future-handle markers ---
        # Visual markers for the handle constraints of the future Bezier
        # neck (see NECK.md). Drawn as dashed blue tangent vectors from each
        # anchor to the handle endpoint, with an open circle at the endpoint.
        #   NT, NB, BT: handles parallel to soundboard slope (+SOUNDBOARD_DIR)
        #   G7fbi:      handle parallel to BT handle (same +SOUNDBOARD_DIR)
        #   C1sbi:      handle horizontal (+east)
        HANDLE_L = 40.0
        H_COLOR = "#1060d0"
        sb = _SOUNDBOARD_DIR

        def _handle(anchor, direction, length=HANDLE_L):
            end = (anchor[0] + length * direction[0],
                   anchor[1] + length * direction[1])
            parts.append(
                f'<line x1="{anchor[0]:.3f}" y1="{anchor[1]:.3f}" '
                f'x2="{end[0]:.3f}" y2="{end[1]:.3f}" '
                f'stroke="{H_COLOR}" stroke-width="0.5" '
                f'stroke-dasharray="2,1.5"/>'
            )
            parts.append(
                f'<circle cx="{end[0]:.3f}" cy="{end[1]:.3f}" r="1.6" '
                f'fill="#fff" stroke="{H_COLOR}" stroke-width="0.6"/>'
            )

        # NB corner handle: outgoing east (handle extends east of NB).
        _handle(NB, (1.0, 0.0))
        # NT corner handle: incoming south, so P2 sits north of NT.
        _handle(NT, (0.0, -1.0))
        # BT corner handles are drawn later, after G7fbo is computed
        # (below in this same block).

        # G7fbo — exit tangent point on G7 flat buffer heading toward F7 flat
        # (the outer common tangent on the north side between equal-radius
        # G7fb and F7fb). This is where the neck leaves G7fb on its way
        # bass-ward, not the G7fb entry from BT.
        _flats_all = [s['flat_buffer'] for s in strings if s['has_flat_buffer']]
        if len(_flats_all) >= 2:
            _G7fb = _flats_all[-1]
            _F7fb = _flats_all[-2]
            _dx, _dy = _F7fb[0] - _G7fb[0], _F7fb[1] - _G7fb[1]
            _L = _math.hypot(_dx, _dy)
            if _L > 0:
                # perpendicular to center-center line, pick north (smaller y)
                _px, _py = -_dy / _L, _dx / _L
                if _py > 0:
                    _px, _py = -_px, -_py
                G7fbo = (_G7fb[0] + R_BUFFER * _px,
                         _G7fb[1] + R_BUFFER * _py)
                # Symmetric handle parallel to the G7fb->F7fb outer common
                # tangent line (i.e., parallel to the center-to-center line
                # between the two equal-radius circles). This is the actual
                # tangent direction of the neck outline at G7fbo, so a
                # symmetric C1 handle here makes the Bezier tangent to G7fb.
                _tan = (_dx / _L, _dy / _L)
                _handle(G7fbo, _tan)
                _handle(G7fbo, (-_tan[0], -_tan[1]))

        # C1sbi — south pole of the bass-most sharp buffer. Symmetric
        # horizontal handle (both +east and -east) since C1sbi is a C1
        # interior waypoint in the future Bezier neck.
        _sharps_all = [s['sharp'] for s in strings if s['has_sharp_buffer']]
        if _sharps_all:
            C1sbi = (_sharps_all[0][0], NB[1])
            _handle(C1sbi, (1.0, 0.0))
            _handle(C1sbi, (-1.0, 0.0))

        # F1fbi — north pole of F1 flat buffer. This is the northernmost
        # point of the flat-buffer chain (F1's flat y is the min among all
        # flats). Symmetric horizontal handle, analogous to C1sbi on the
        # opposite side of the neck.
        _F1_str = next((s for s in strings
                        if s.get('note') == 'F1' and s['has_flat_buffer']),
                       None)
        if _F1_str is not None:
            _F1fb = _F1_str['flat_buffer']
            F1fbi = (_F1fb[0], _F1fb[1] - R_BUFFER)  # north pole
            _handle(F1fbi, (1.0, 0.0))
            _handle(F1fbi, (-1.0, 0.0))

        # Additional interior-anchor handles at natural poles of the
        # specified buffers. Sharps (on leg 1 south side) use the south
        # pole; flats (on leg 2 north side) use the north pole. All
        # handles are symmetric horizontal (±east). These land at
        # gap-adjacent buffers in the chain where the future Bezier
        # neck's interior anchors naturally sit.
        def _pole_handle(note, kind, side):
            _s = next((s for s in strings if s.get('note') == note), None)
            if _s is None:
                return
            if kind == 'flat' and not _s.get('has_flat_buffer'):
                return
            if kind == 'sharp' and not _s.get('has_sharp_buffer'):
                return
            _key = 'flat_buffer' if kind == 'flat' else 'sharp'
            _center = _s[_key]
            _pole = (_center[0],
                     _center[1] - R_BUFFER if side == 'north'
                     else _center[1] + R_BUFFER)
            _handle(_pole, (1.0, 0.0))
            _handle(_pole, (-1.0, 0.0))

        # G2f: symmetric handle tilted 45° "down" (axis running NW→SE, one
        # end angling south-east, the other north-west).
        _G2_str = next((s for s in strings
                        if s.get('note') == 'G2' and s.get('has_flat_buffer')),
                       None)
        _G2_TILT = (_math.cos(_math.pi / 4), _math.sin(_math.pi / 4))
        _G2f_pole = None
        if _G2_str is not None:
            _G2fb = _G2_str['flat_buffer']
            _G2f_pole = (_G2fb[0], _G2fb[1] - R_BUFFER)
            _handle(_G2f_pole, _G2_TILT)
            _handle(_G2f_pole, (-_G2_TILT[0], -_G2_TILT[1]))
        _pole_handle('E2', 'sharp', 'south')
        _pole_handle('F5', 'flat',  'north')
        _pole_handle('E5', 'sharp', 'south')

        # A3s: symmetric handle tilted 45° (rotated CCW from +east in the
        # visual frame, which in SVG y-down means the +x/-y direction —
        # up-right).
        _A3_str = next((s for s in strings
                        if s.get('note') == 'A3' and s.get('has_sharp_buffer')),
                       None)
        _A3_TILT = (_math.cos(_math.pi / 4), _math.sin(_math.pi / 4))
        _A3s_pole = None
        if _A3_str is not None:
            _A3sb = _A3_str['sharp']
            _A3s_pole = (_A3sb[0], _A3sb[1] + R_BUFFER)
            _handle(_A3s_pole, _A3_TILT)
            _handle(_A3s_pole, (-_A3_TILT[0], -_A3_TILT[1]))
        # G7sb has two asymmetric handles (G7s is a corner, not C1):
        #   G7sbo (outgoing, toward BT): south pole of G7sb, single handle
        #     pointing east (horizontal toward BT).
        #   G7sbi (incoming, from F7sb): tangent entry on south side of
        #     G7sb, single handle pointing along the G7->F7 direction
        #     (back toward F7sb).
        # F7sbo = south pole of F7 sharp buffer. This is the ARC END
        # (where the outline exits F7sb heading horizontal east to BT).
        # The arc BEGIN would be on F7sb at the E7sb common-tangent point
        # (roughly 807.36, 491.08), which we don't visit explicitly.
        #
        # Corner anchor: incoming angled toward E7b (direction from F7sbo
        # toward E7b center = nearly pure west), outgoing horizontal east
        # (toward BT).
        F7sbo = None
        _t_f7sbo_in = None
        _F7_str = next((s for s in strings if s.get('note') == 'F7'), None)
        _E7_str = next((s for s in strings if s.get('note') == 'E7'), None)
        if _F7_str is not None and _F7_str.get('has_sharp_buffer'):
            _F7sb = _F7_str['sharp']
            F7sbo = (_F7sb[0], _F7sb[1] + R_BUFFER)
            if _E7_str is not None and _E7_str.get('has_sharp_buffer'):
                _E7sb = _E7_str['sharp']
                # Incoming travel direction = parallel to the E7sb->F7sb
                # center-line (the outer-common-tangent direction between
                # the two equal-radius sharp circles). This gives F7sbo a
                # visibly distinct corner from the horizontal outgoing
                # tangent; a near-horizontal t_in would make the corner
                # invisible.
                _dxe = _F7sb[0] - _E7sb[0]
                _dye = _F7sb[1] - _E7sb[1]
                _Le = _math.hypot(_dxe, _dye)
                if _Le > 0:
                    _t_f7sbo_in = (_dxe / _Le, _dye / _Le)
            if _t_f7sbo_in is None:
                _t_f7sbo_in = (1.0, 0.0)
            # Black anchor dot so the F7sbo position is visually explicit.
            parts.append(
                f'<circle cx="{F7sbo[0]:.3f}" cy="{F7sbo[1]:.3f}" '
                f'r="{ANCHOR_R}" fill="#000"/>'
            )
            parts.append(
                f'<text x="{F7sbo[0] + 12:.3f}" y="{F7sbo[1] + 6:.3f}" '
                f'class="big">F7sbo</text>'
            )
            # Blue handle markers: incoming points from F7sbo toward E7b,
            # outgoing horizontal east to BT.
            _handle(F7sbo, (-_t_f7sbo_in[0], -_t_f7sbo_in[1]))
            _handle(F7sbo, (1.0, 0.0))

        # --- Brown cubic Bezier neck curve through the blue anchors ---
        # Connects NB -> C1sbi -> E2s -> A3s -> E5s -> G7sbi -> G7sbo -> BT
        #          -> G7fbo -> F5f -> G2f -> F1fbi -> NT, closed by a
        # straight leg 3 (NT -> NB). Uses the anchor tangent directions
        # established above. Handle lengths are picked per-segment to keep
        # the curve outside every buffer circle (R_BUFFER = 12 mm).
        def _pole(note, kind, side):
            _s = next((s for s in strings if s.get('note') == note), None)
            if _s is None:
                return None
            if kind == 'flat' and not _s.get('has_flat_buffer'):
                return None
            if kind == 'sharp' and not _s.get('has_sharp_buffer'):
                return None
            _c = _s['flat_buffer' if kind == 'flat' else 'sharp']
            dy = -R_BUFFER if side == 'north' else R_BUFFER
            return (_c[0], _c[1] + dy)

        C1sbi_anchor = None
        if _sharps_all:
            C1sbi_anchor = (_sharps_all[0][0], NB[1])
        E2s_p = _pole('E2', 'sharp', 'south')
        A3s_p = _pole('A3', 'sharp', 'south')
        E5s_p = _pole('E5', 'sharp', 'south')
        F5f_p = _pole('F5', 'flat',  'north')
        G2f_p = _pole('G2', 'flat',  'north')
        F1fbi_anchor = _pole('F1', 'flat', 'north')

        # Compute G7fbo and its tangent direction (along the G7fb->F7fb
        # center line for the outer common tangent on the north side).
        G7fbo = None
        _t_g7fbo = None
        if len(_flats_all) >= 2:
            _G7fb = _flats_all[-1]
            _F7fb = _flats_all[-2]
            _dx2, _dy2 = _F7fb[0] - _G7fb[0], _F7fb[1] - _G7fb[1]
            _L2 = _math.hypot(_dx2, _dy2)
            if _L2 > 0:
                _px2, _py2 = -_dy2 / _L2, _dx2 / _L2
                if _py2 > 0:
                    _px2, _py2 = -_px2, -_py2
                G7fbo = (_G7fb[0] + R_BUFFER * _px2,
                         _G7fb[1] + R_BUFFER * _py2)
                _t_g7fbo = (_dx2 / _L2, _dy2 / _L2)  # G7 -> F7 direction

        # Anchors in traversal order. Each entry is
        # (name, position, tangent_in, tangent_out). For C1-symmetric
        # interior anchors tangent_in == tangent_out. For corners (BT, NT),
        # they differ. tangent_in for the very first anchor (NB) is unused.
        east = (1.0, 0.0)
        west = (-1.0, 0.0)
        south = (0.0, 1.0)
        # Tangents chosen to match the actual direction of travel at each
        # anchor (preventing U-turn loops). Corners at NB, BT, NT.
        # Direction from BT toward G7fbo (the leg-2-start direction).
        _t_bt_out = None
        if G7fbo is not None:
            _dxb, _dyb = G7fbo[0] - _BT[0], G7fbo[1] - _BT[1]
            _Lb = _math.hypot(_dxb, _dyb)
            if _Lb > 0:
                _t_bt_out = (_dxb / _Lb, _dyb / _Lb)
        # Blue handles for BT corner: incoming east (P2 is WEST of BT),
        # outgoing +t_bt_out (P1 is in that direction from BT).
        _handle(_BT, (-1.0, 0.0))
        if _t_bt_out is not None:
            _handle(_BT, _t_bt_out)
        # G7fbe = entry tangent point from BT onto G7 flat buffer (north
        # side). Mirrors the G7sbi/G7sbo pair on leg 1: an entry tangent
        # point plus an exit tangent point with an arc between them.
        G7fbe = None
        _t_g7fbe = None
        if len(_flats_all) >= 1:
            _cx_gf, _cy_gf = _flats_all[-1]  # G7 flat buffer center
            _vx = _BT[0] - _cx_gf
            _vy = _BT[1] - _cy_gf
            _dd = _math.hypot(_vx, _vy)
            if _dd > R_BUFFER:
                _theta = _math.atan2(_vy, _vx)
                _half = _math.asin(R_BUFFER / _dd)
                # Two tangent points; pick the north side (smaller y).
                _ta = _theta - (_math.pi / 2 - _half)
                _tb = _theta + (_math.pi / 2 - _half)
                _pa = (_cx_gf + R_BUFFER * _math.cos(_ta),
                       _cy_gf + R_BUFFER * _math.sin(_ta))
                _pb = (_cx_gf + R_BUFFER * _math.cos(_tb),
                       _cy_gf + R_BUFFER * _math.sin(_tb))
                G7fbe = _pa if _pa[1] < _pb[1] else _pb
                # Tangent direction at G7fbe = BT -> G7fbe direction
                _dxe = G7fbe[0] - _BT[0]
                _dye = G7fbe[1] - _BT[1]
                _Le = _math.hypot(_dxe, _dye)
                if _Le > 0:
                    _t_g7fbe = (_dxe / _Le, _dye / _Le)

        # F7sbo replaces G7sbo as the leg-1 exit. G7sb drops off the
        # outline; the horizontal tangent line from F7sbo south pole
        # extends east to the lowered BT.
        anchors_ordered = [
            ("NB",     NB,             None,          east),
            ("C1sbi",  C1sbi_anchor,   east,          east),
            ("E2s",    E2s_p,          east,          east),
            ("A3s",    A3s_p,          _A3_TILT,      _A3_TILT),
            ("E5s",    E5s_p,          east,          east),
            ("F7sbo",  F7sbo,          _t_f7sbo_in,   east),   # corner
            ("BT",     _BT,            east,          _t_g7fbe),    # corner
            ("G7fbe",  G7fbe,          _t_g7fbe,      _t_g7fbe),
            ("G7fbo",  G7fbo,          _t_g7fbo,      _t_g7fbo),
            ("F5f",    F5f_p,          west,          west),
            ("G2f",    _G2f_pole,      (-_G2_TILT[0], -_G2_TILT[1]),
                                        (-_G2_TILT[0], -_G2_TILT[1])),
            ("F1fbi",  F1fbi_anchor,   west,          west),
            ("NT",     NT,             (0.0, 1.0),    None),
        ]
        # Drop any anchors we couldn't build (missing data).
        anchors_ordered = [
            a for a in anchors_ordered
            if a[1] is not None
            and (a[2] is not None or a[3] is not None)
        ]

        # Buffer centers for clearance checks (all rendered buffers, not just
        # the obstacle chain).
        _all_buf_centers = []
        for s in strings:
            _all_buf_centers.append(s['flat_buffer'])
            _all_buf_centers.append(s['sharp'])

        def _min_dist_to_buffers(cubic, n=40):
            mt = [1 - k / (n - 1) for k in range(n)]
            ts = [k / (n - 1) for k in range(n)]
            pts = []
            P0, P1, P2, P3 = cubic
            for k in range(n):
                t = ts[k]
                m = 1.0 - t
                x = m*m*m*P0[0] + 3*m*m*t*P1[0] + 3*m*t*t*P2[0] + t*t*t*P3[0]
                y = m*m*m*P0[1] + 3*m*m*t*P1[1] + 3*m*t*t*P2[1] + t*t*t*P3[1]
                pts.append((x, y))
            d_min = float('inf')
            for (cx, cy) in _all_buf_centers:
                for (x, y) in pts:
                    dd = _math.hypot(x - cx, y - cy)
                    if dd < d_min:
                        d_min = dd
            return d_min

        # Width assignment respecting PROBLEMv2 symmetry:
        #   - C1-symmetric anchors (everything except BT corner): a single
        #     width per anchor used on BOTH incoming and outgoing sides
        #     (w_in == w_out), preserving C1 continuity.
        #   - BT corner: separate (w_in, w_out) independently tunable.
        #   - NB endpoint: w_out only. NT endpoint: w_in only.
        # Per-anchor coordinate descent: hold others fixed, grid-search the
        # free width at one anchor to maximise min buffer distance across
        # both segments that touch that anchor. Iterate a few passes.
        W_MIN_V2 = 15.0    # visual floor — keeps C1-symmetric handles from
                           # collapsing to 2 mm when larger values tie for
                           # min_dist. A width below ~15 mm renders as a
                           # visual right-angle at the anchor.
        W_MAX_V2 = 80.0    # visual ceiling — very wide handles (200+ mm)
                           # create overshoot lobes/loops even when the
                           # min-buf-dist is good. 80 mm is wide enough to
                           # give handle-length room on long segments
                           # without producing visible self-intersections.
        N_GRID = 24
        W_DEFAULT = 40.0   # visible default, matches the blue handle length

        # Per-anchor storage: for C1-symmetric anchors, 'w' is a single
        # value used on both sides. For BT, we store (w_in, w_out) separately.
        # Anchors with independent per-side widths (true corners).
        _CORNER_NAMES = {'BT', 'F7sbo'}
        widths = []
        for name, pos, t_in, t_out in anchors_ordered:
            if name in _CORNER_NAMES:
                widths.append({'in': W_DEFAULT, 'out': W_DEFAULT})
            elif t_in is None:  # NB (leg-3 closure means no incoming Bezier)
                widths.append({'out': W_DEFAULT})
            elif t_out is None:  # NT
                widths.append({'in': W_DEFAULT})
            else:
                widths.append({'w': W_DEFAULT})

        def _build_segment(i):
            _, P0, _, t_out_i = anchors_ordered[i]
            _, P3, t_in_j, _ = anchors_ordered[i + 1]
            wi = widths[i]
            wj = widths[i + 1]
            w_out = wi.get('out', wi.get('w'))
            w_in  = wj.get('in',  wj.get('w'))
            P1 = (P0[0] + w_out * t_out_i[0], P0[1] + w_out * t_out_i[1])
            P2 = (P3[0] - w_in  * t_in_j[0],  P3[1] - w_in  * t_in_j[1])
            return [P0, P1, P2, P3]

        def _min_dist_segment(i):
            return _min_dist_to_buffers(_build_segment(i))

        def _anchor_min_dist(idx):
            vals = []
            if idx > 0:
                vals.append(_min_dist_segment(idx - 1))
            if idx < len(anchors_ordered) - 1:
                vals.append(_min_dist_segment(idx))
            return min(vals) if vals else float('inf')

        # Coordinate descent over width knobs.
        for _pass in range(4):
            for idx in range(len(anchors_ordered)):
                anchor_name = anchors_ordered[idx][0]
                for key in list(widths[idx].keys()):
                    best = (_anchor_min_dist(idx), widths[idx][key])
                    for k in range(N_GRID):
                        w = W_MIN_V2 + (W_MAX_V2 - W_MIN_V2) * k / (N_GRID - 1)
                        widths[idx][key] = w
                        md = _anchor_min_dist(idx)
                        if md > best[0]:
                            best = (md, w)
                    widths[idx][key] = best[1]

        # Build path from optimized widths.
        # Special case: G7sbi -> G7sbo is an arc on the G7 sharp circle,
        # not a cubic. Both endpoints lie on the same R = 12 circle with
        # different natural tangent directions; a cubic between them
        # creates a U-turn loop because the symmetric-tangent constraint
        # forces the curve to leave G7sbi away from G7sbo.
        path_d = [f"M {NB[0]:.3f} {NB[1]:.3f}"]
        seg_report = []
        for i in range(len(anchors_ordered) - 1):
            name_i = anchors_ordered[i][0]
            name_j = anchors_ordered[i + 1][0]
            _, P0, _, _ = anchors_ordered[i]
            _, P3, _, _ = anchors_ordered[i + 1]
            wi = widths[i]
            wj = widths[i + 1]
            w_out = wi.get('out', wi.get('w'))
            w_in  = wj.get('in',  wj.get('w'))
            if (name_i == 'G7sbi' and name_j == 'G7sbo') or \
               (name_i == 'G7fbe' and name_j == 'G7fbo'):
                # SVG arc on the corresponding buffer circle. Both anchors
                # lie on the same R=12 circle; a cubic between them with
                # locked tangent directions creates a U-turn loop, so we
                # emit a true arc instead. sweep=1 traces the outer side
                # (south for G7sb, north for G7fb).
                sweep = 1 if name_i == 'G7sbi' else 0
                path_d.append(
                    f"A {R_BUFFER:.3f} {R_BUFFER:.3f} 0 0 {sweep} "
                    f"{P3[0]:.3f} {P3[1]:.3f}"
                )
                md = R_BUFFER  # exact — arc is on the circle by construction
            elif name_j == 'G7sbi':
                # Use a straight tangent line into G7sbi (matching the
                # polyline approach). A cubic here creates a visible cusp
                # at G7sbi because the cubic's east-north tangent there
                # clashes with the arc's west-south direction onto G7sb.
                path_d.append(f"L {P3[0]:.3f} {P3[1]:.3f}")
                md = _min_dist_to_buffers([P0, P0, P3, P3])
            else:
                cubic = _build_segment(i)
                _, P1, P2, _ = cubic
                md = _min_dist_to_buffers(cubic)
                path_d.append(
                    f"C {P1[0]:.3f} {P1[1]:.3f} "
                    f"{P2[0]:.3f} {P2[1]:.3f} "
                    f"{P3[0]:.3f} {P3[1]:.3f}"
                )
            seg_report.append((
                f"{name_i}->{name_j}", md, w_out, w_in
            ))
        # Leg 3: straight line NT -> NB (closes the outline).
        path_d.append(f"L {NB[0]:.3f} {NB[1]:.3f}")
        parts.append(
            f'<path d="{" ".join(path_d)}" fill="none" '
            f'stroke="#8B4513" stroke-width="1.6"/>'
        )
        # Emit solve diagnostic to stdout (one report per segment).
        _n_viol = sum(1 for r in seg_report if r[1] < R_BUFFER - 1e-6)
        print(f"\n=== PROBLEMv2 brown-curve solve ({len(seg_report)} segments) ===")
        print(f"   {'segment':24s} {'min_buf_dist':>12s}  {'w_out':>6s} {'w_in':>6s}  status")
        for label, md, wo, wi in seg_report:
            status = "OK" if md >= R_BUFFER - 1e-6 else f"CUT  ({R_BUFFER - md:+.2f}mm)"
            print(f"   {label:24s} {md:12.3f}  {wo:6.2f} {wi:6.2f}  {status}")
        print(f"   {_n_viol}/{len(seg_report)} segments infeasible"
              f" (min_buf_dist < {R_BUFFER:.1f})")

    # Column dashed centerline + label
    parts.append('<line x1="32.20" y1="38.10" x2="32.20" y2="1915.50" '
                 'stroke="#888" stroke-width="0.4" stroke-dasharray="3,2"/>')
    parts.append('<text x="32.20" y="976.80" text-anchor="middle" '
                 'transform="rotate(-90 32.20 976.80)" class="col">'
                 'COLUMN  39 x 1877 mm</text>')
    # Column outer and inner vertical edges (x = 12.7, x = 51.7) from
    # just above NT down to the floor.
    parts.append(f'<line x1="12.70" y1="{NT[1] - 40:.3f}" x2="12.70" '
                 f'y2="{FLOOR_Y:.3f}" stroke="#888" stroke-width="0.6"/>')
    parts.append(f'<line x1="51.70" y1="{NT[1] - 40:.3f}" x2="51.70" '
                 f'y2="{CI[1]:.3f}" stroke="#888" stroke-width="0.6"/>')

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
    # Circles are drawn for EVERY string, regardless of SKIPPED_BUFFERS.
    # SKIPPED_BUFFERS still excludes those buffers from the neck-outline
    # obstacle chain (has_flat_buffer / has_sharp_buffer flags).
    for s in strings:
        fb = s["flat_buffer"]
        parts.append(f'<circle cx="{fb[0]}" cy="{fb[1]}" r="{R_BUFFER}" '
                     f'fill="none" stroke="#000" stroke-width="0.4"/>')
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
    # Sharp circles also drawn for every string regardless of SKIPPED_BUFFERS.
    for s in strings:
        parts.append(f'<circle class="n" cx="{s["nat"][0]:.3f}" cy="{s["nat"][1]:.3f}" r="{DOT_R}"/>')
        parts.append(f'<circle cx="{s["sharp"][0]:.3f}" cy="{s["sharp"][1]:.3f}" '
                     f'r="{R_BUFFER}" fill="none" stroke="#000" stroke-width="0.4"/>')
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
