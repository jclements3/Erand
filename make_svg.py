#!/usr/bin/env python3
"""Render erand.dxf as an SVG with measurements in millimetres."""
import ezdxf, math

SRC = '/home/james.clements/projects/erand/erand.dxf'
OUT = '/home/james.clements/projects/erand/erand.svg'
IN_TO_MM = 25.4

NOTES = ['G','F','E','D','C','B','A']  # diatonic order descending from G7
def note_for(num):
    """String #1 = G7, descending diatonically. Returns (letter, octave)."""
    idx = num - 1
    letter = NOTES[idx % 7]
    # octave: G7 at num=1, F7=2, ..., A7? no, G is top. G7,F7,E7,D7,C7,B6,A6 ...
    # Each cycle of 7 drops one octave after C. Easier: precompute once.
    return letter

# Precompute note labels for strings 1..47
def build_notes():
    seq = []
    letters = ['G','F','E','D','C','B','A']
    octave = 7
    for i in range(47):
        letter = letters[i % 7]
        seq.append((letter, octave))
        if letter == 'A':      # next string after A is G of next-lower octave
            octave -= 1
    return seq
NOTE_TABLE = build_notes()  # index 0 -> string #1

# String diameters from ERAND.md (effective = core + 2 * wrap for wound strings)
def diameter_in(num):
    if 1  <= num <= 7 : return 0.025
    if 8  <= num <= 10: return 0.028
    if num == 11      : return 0.030
    if 12 <= num <= 14: return 0.032
    if 15 <= num <= 18: return 0.036
    if 19 <= num <= 21: return 0.040
    if 22 <= num <= 24: return 0.045
    if 25 <= num <= 27: return 0.050
    # Middle register: nylon core + nylon/steel wrap (effective = core + 2*wrap)
    if 28 <= num <= 29: return 0.045 + 2*0.008
    if 30 <= num <= 31: return 0.050 + 2*0.008
    if num == 32      : return 0.050 + 2*0.013
    if 33 <= num <= 34: return 0.055 + 2*0.013
    if num == 35      : return 0.060 + 2*0.013
    if num == 36      : return 0.060 + 2*0.016  # interpolated 0.013->0.022
    if num == 37      : return 0.060 + 2*0.019
    if num == 38      : return 0.060 + 2*0.022
    # Lower register: steel core + bronze wrap
    if num == 39      : return 0.020 + 2*0.008
    if num == 40      : return 0.020 + 2*0.010
    if num == 41      : return 0.020 + 2*0.010
    if num == 42      : return 0.022 + 2*0.013
    if num == 43      : return 0.022 + 2*0.013
    if num == 44      : return 0.024 + 2*0.013
    if num == 45      : return 0.025 + 2*0.016  # interpolated 0.013->0.020
    if num == 46      : return 0.025 + 2*0.018
    if num == 47      : return 0.026 + 2*0.020
    return 0.04

def color_for(letter):
    if letter == 'C': return '#c00000'  # red
    if letter == 'F': return '#1060d0'  # blue
    return '#888'                       # gray

doc = ezdxf.readfile(SRC)
msp = doc.modelspace()

strings, on_ticks, keys, texts = [], [], [], []
for L in msp.query('LINE'):
    dx, dy = L.dxf.end.x - L.dxf.start.x, L.dxf.end.y - L.dxf.start.y
    length = math.hypot(dx, dy)
    ang = math.degrees(math.atan2(dy, dx))
    if abs(length - 0.25) < 1e-3 and abs(ang) < 1:
        on_ticks.append(L)
    elif abs(length - 1.53) < 0.02 and abs(ang - 78) < 2:
        keys.append(L)
    elif abs(ang - 90) < 1 and length > 2:
        strings.append(L)
for T in msp.query('TEXT'):
    texts.append(T)

# Rank strings by active length
srows = []
for L in strings:
    y0, y1 = sorted([L.dxf.start.y, L.dxf.end.y])
    srows.append({'x': L.dxf.start.x, 'yg': y0, 'yf': y1,
                  'len': y1 - y0, 'ticks': [], 'key_tip': None})
for i, r in enumerate(sorted(srows, key=lambda r: r['len'])):
    r['num'] = i + 1
srows_by_x = sorted(srows, key=lambda r: r['x'])

for T in on_ticks:
    cx = T.dxf.start.x + 0.125
    cy = T.dxf.start.y
    best = min(srows, key=lambda r: abs(r['x'] - cx))
    if abs(best['x'] - cx) < 0.15:
        best['ticks'].append(cy)
    else:
        best2 = min(srows, key=lambda r: abs(r['x'] + 0.319 - cx) + abs(r['yf'] + 1.497 - cy))
        best2['key_tip'] = (cx, cy)

# Column geometry (from photo measurement + DXF-mm calibration at 0.1616 mm/px):
#   column shaft width:      39 mm
#   column -> bass string:   53 mm (at mid-shaft; 57 at top, 50 at bottom)
#   column shaft length:   1467 mm
#   column tilt from vert: +0.49 deg  (top leans away from strings)
COL_W_MM         = 39.0
COL_TO_BASS_MM   = 50.0     # 50 mm gap from column inner face to bass string
# Column is PARALLEL to the strings (both vertical in DXF), running floor -> top of harp.
BASS_X_IN   = min(r['x'] for r in srows)                    # = 10.0 in (bass string)
BASS_X_MM   = BASS_X_IN * IN_TO_MM                          # 254.0 mm
COL_RIGHT_MM = BASS_X_MM - COL_TO_BASS_MM                   # 204.0 mm (inner / string-facing face)
COL_LEFT_MM  = COL_RIGHT_MM - COL_W_MM                      # 165.0 mm (outer face)
BASS_YF_IN   = next(r['yf'] for r in srows if abs(r['x']-BASS_X_IN) < 1e-6)
# Column extends floor -> top of harp:
#   floor (bottom) = y below the lowest grommet (base sits below strings)
#   top            = y above the highest feature (above all key-tips / tuning pins)
all_y_mm = (
    [r['yg'] * IN_TO_MM for r in srows]
  + [r['yf'] * IN_TO_MM for r in srows]
  + [r['key_tip'][1] * IN_TO_MM for r in srows if r.get('key_tip')]
)
COL_TOP_MM_Y = max(all_y_mm) + 60                           # a bit above the highest feature
COL_BOT_MM_Y = 0.0                                          # floor
COL_LENGTH_MM = COL_TOP_MM_Y - COL_BOT_MM_Y
# Convert back to inches for the global view transform
COL_LEFT_IN  = COL_LEFT_MM  / IN_TO_MM
COL_RIGHT_IN = COL_RIGHT_MM / IN_TO_MM
COL_TOP_IN   = COL_TOP_MM_Y / IN_TO_MM
COL_BOT_IN   = COL_BOT_MM_Y / IN_TO_MM

# Plot-world extent (inches), draw geometry only (exclude legend text block)
xs = [r['x'] for r in srows]
ys_lo = [r['yg'] for r in srows]
ys_hi = [r['yf'] + 2 for r in srows]
xs_pad = 0.5
ys_pad = 0.5
x0 = min(COL_LEFT_IN, min(xs)) - xs_pad
# Include room for the soundboard's treble endpoint + space for the SBT label,
# which extends past the endpoint on the right.
x1 = max(xs) + xs_pad + 5.0   # ~125 mm of headroom on the treble end (fits SBT label)
# No legend strip below the floor; the legend goes IN the triangular empty area
# below the grommet line (strings) and above the base/floor.
y0 = min(COL_BOT_IN, min(ys_lo)) - ys_pad
y1 = max(max(ys_hi), COL_TOP_IN) + ys_pad + 1.0   # extra top margin so column top is visible

# Convert to mm
def tx(x): return (x - x0) * IN_TO_MM
def ty(y): return (y1 - y) * IN_TO_MM  # flip y for SVG

W_mm = (x1 - x0) * IN_TO_MM
H_mm = (y1 - y0) * IN_TO_MM

# Add a right margin for a legend column
LEG_W = 0            # no right-side legend; everything below the strings
total_W = W_mm

elems = []
# Use a max dimension of 900 px so the whole harp fits on typical monitors; viewBox in mm.
MAX_DIM_PX = 900
if H_mm >= total_W:
    VIEW_H_PX = MAX_DIM_PX
    VIEW_W_PX = int(total_W / H_mm * MAX_DIM_PX)
else:
    VIEW_W_PX = MAX_DIM_PX
    VIEW_H_PX = int(H_mm / total_W * MAX_DIM_PX)
elems.append(f'<svg xmlns="http://www.w3.org/2000/svg" '
             f'width="{VIEW_W_PX}" height="{VIEW_H_PX}" '
             f'viewBox="0 0 {total_W:.2f} {H_mm:.2f}" '
             f'preserveAspectRatio="xMidYMid meet">')
elems.append('<style>'
             '.str{fill:none;stroke-linecap:round}'
             '.key{stroke:#888;stroke-width:0.35;fill:none}'
             '.sb{stroke:#555;stroke-width:0.6;fill:none}'
             '.g{fill:#1f77b4}.n{fill:#2ca02c}.f{fill:#d62728}.s{fill:#ff7f0e}.p{fill:#9467bd}'
             '.sml{font-family:sans-serif;font-size:12px;fill:#333}'
             '.lbl{font-family:sans-serif;font-size:17px;fill:#222}'
             '.big{font-family:sans-serif;font-size:22px;fill:#000;font-weight:bold}'
             '.title{font-family:sans-serif;font-size:36px;fill:#000;font-weight:bold}'
             '.mono{font-family:monospace;font-size:14px;fill:#222}'
             '.dim{stroke:#aaa;stroke-width:0.15;stroke-dasharray:1,1;fill:none}'
             '</style>')

# Background
elems.append(f'<rect x="0" y="0" width="{total_W:.2f}" height="{H_mm:.2f}" fill="#fff"/>')

# Soundboard: a single straight line through grommets #47 and #1, extended on the
# bass end back to the column (inner face) and on the treble end up to where it
# meets the G7-pin y-level (~69.7 mm past the G7 pin itself).
bass_r   = srows_by_x[0]                  # leftmost = bass  end = C1 (string #47)
treble_r = srows_by_x[-1]                 # rightmost = treble end = G7 (string #1)
col_right_tx_val = (COL_RIGHT_IN - x0) * IN_TO_MM
g7_pin_x, g7_pin_y = treble_r['key_tip']

bx_in, by_in = bass_r['x'],   bass_r['yg']
tx_in, ty_in = treble_r['x'], treble_r['yg']
sb_slope = (ty_in - by_in) / (tx_in - bx_in)     # inches per inch
# bass end: extend back to x = column inner face (in DXF inches)
x_bass_end_in = COL_RIGHT_IN
y_bass_end_in = by_in + sb_slope * (x_bass_end_in - bx_in)
# treble end: extend soundboard line up to meet y = sharp-y of G7 (string #1).
# Sharp position = yg + (yf - yg) * 2^(-2/12)  (two semitones shorter than flat).
SEMITONE_R = 2.0 ** (-1.0/12.0)
g7_sharp_y = treble_r['yg'] + (treble_r['yf'] - treble_r['yg']) * SEMITONE_R * SEMITONE_R
x_treble_end_in = bx_in + (g7_sharp_y - by_in) / sb_slope
y_treble_end_in = g7_sharp_y
elems.append(f'<line class="sb" '
             f'x1="{tx(x_bass_end_in):.3f}"   y1="{ty(y_bass_end_in):.3f}" '
             f'x2="{tx(x_treble_end_in):.3f}" y2="{ty(y_treble_end_in):.3f}"/>')
# Neck curve (through flat points)
neck_pts = ' '.join(f'{tx(r["x"]):.3f},{ty(r["yf"]):.3f}' for r in srows_by_x)
elems.append(f'<polyline class="dim" points="{neck_pts}"/>')

# Strings (stroke-width = actual string diameter in mm; color: C=red, F=blue, else gray)
for r in srows:
    letter, octave = NOTE_TABLE[r['num'] - 1]
    dia_mm = diameter_in(r['num']) * IN_TO_MM
    col = color_for(letter)
    elems.append(f'<line class="str" stroke="{col}" stroke-width="{dia_mm:.3f}" '
                 f'x1="{tx(r["x"]):.3f}" y1="{ty(r["yg"]):.3f}" '
                 f'x2="{tx(r["x"]):.3f}" y2="{ty(r["yf"]):.3f}"/>')

# ---- COLUMN (outline rectangle in DXF-mm space, oriented to DXF y-up convention) ----
#  tx(x_in) = (x_in - x0) * IN_TO_MM     -> so column left/right in tx units:
col_left_tx  = (COL_LEFT_IN  - x0) * IN_TO_MM
col_right_tx = (COL_RIGHT_IN - x0) * IN_TO_MM
col_top_ty   = (y1 - COL_TOP_IN) * IN_TO_MM
col_bot_ty   = (y1 - COL_BOT_IN) * IN_TO_MM
elems.append(f'<rect x="{col_left_tx:.2f}" y="{col_top_ty:.2f}" '
             f'width="{COL_W_MM:.2f}" height="{COL_LENGTH_MM:.2f}" '
             f'fill="#d0d0d0" stroke="#000" stroke-width="3"/>')
# Center axis line
col_axis_tx = (col_left_tx + col_right_tx) / 2
elems.append(f'<line x1="{col_axis_tx:.2f}" y1="{col_top_ty:.2f}" '
             f'x2="{col_axis_tx:.2f}" y2="{col_bot_ty:.2f}" '
             f'stroke="#888" stroke-width="0.4" stroke-dasharray="3,2"/>')
# Column label (rotated, center of shaft)
col_mid_ty = (col_top_ty + col_bot_ty) / 2
elems.append(f'<text x="{col_axis_tx:.2f}" y="{col_mid_ty:.2f}" '
             f'text-anchor="middle" transform="rotate(-90 {col_axis_tx:.2f} {col_mid_ty:.2f})" '
             f'font-family="sans-serif" font-size="14" font-weight="bold" fill="#000">'
             f'COLUMN  {COL_W_MM:.0f} x {COL_LENGTH_MM:.0f} mm</text>')

# Neck / harmonic-curve: cubic Bezier from NKT (neck takeoff on the column inner face)
# to SBT (soundboard top). The takeoff sits 50 mm above where the C1-D1 pin line,
# extended back, meets the column inner face (at x = 204 mm DXF-mm). The tangent at
# NKT matches the C1->D1 slope so the curve leaves the column tangent to the bass-
# side pin arc. SBT keeps its vertical tangent.
#
# Pins C1 and D1 (bass-most two strings, no sharping discs), in DXF inches:
c1_pin = (srows_by_x[0]['x']  - 0.319, srows_by_x[0]['yf']  + 1.497)
d1_pin = (srows_by_x[1]['x']  - 0.319, srows_by_x[1]['yf']  + 1.497)
slope_cd_in = (d1_pin[1] - c1_pin[1]) / (d1_pin[0] - c1_pin[0])     # +0.193 in DXF
# Takeoff sits on the column OUTER face (left side, x = 165 mm), 50 mm below the
# flat-point of string #47 (bass-most string yf).
nkt_x_in = COL_LEFT_IN
nkt_y_in = srows_by_x[0]['yf'] - 50.0 / IN_TO_MM    # lowered 50 mm from bass yf
nkt_x = tx(nkt_x_in)                      # SVG tx (== col_right_tx)
nkt_y = ty(nkt_y_in)                      # SVG ty
# SVG slope of the tangent (y is flipped):
slope_svg = -slope_cd_in
sbt_x = tx(x_treble_end_in)
sbt_y = ty(y_treble_end_in)
dW = sbt_x - nkt_x
dH = sbt_y - nkt_y
# C1: along tangent direction from NKT; C2: vertical at SBT (just above)
# H1 vertical: directly above NKT.  H2 vertical: directly above SBT.  Both handles
# stretch 30 % of the total vertical span dH so the curve has symmetric tangent pull
# on both ends.
c1x = nkt_x
c1y = nkt_y - 0.30 * dH
c2x = sbt_x
c2y = sbt_y - 0.30 * dH
ctl_x, ctl_y = nkt_x, nkt_y   # re-alias

# ---- Multi-segment Bezier path threading through EVERY pin ------------------
# Anchor nodes (in order, bass -> treble): NKT, pin[0..46], SBT.
# Tangent at each interior anchor is Catmull-Rom style: direction of (next - prev),
# giving C1 continuity.  Handle length = 1/3 of the incoming/outgoing segment
# length (standard Catmull-Rom -> cubic-Bezier conversion).
#
# The endpoint tangents at NKT and SBT use the direction to the first/last pin.
# This replaces the previous N1/N2 anchors.

# Internal anchor positions (from neck_anchors.json).
import json as _json
with open('/home/james.clements/projects/erand/neck_anchors.json') as _f:
    _nd = _json.load(_f)
pin_pts = [tuple(a) for a in _nd['anchors']]
use_c2  = bool(_nd.get('use_c2', False))
anchors = [(nkt_x, nkt_y)] + pin_pts + [(sbt_x, sbt_y)]

# Tangent direction at each anchor (Catmull-Rom). For endpoints use next/prev dir.
def tangent(i):
    if i == 0:
        dx = anchors[1][0] - anchors[0][0]; dy = anchors[1][1] - anchors[0][1]
    elif i == len(anchors) - 1:
        dx = anchors[i][0] - anchors[i-1][0]; dy = anchors[i][1] - anchors[i-1][1]
    else:
        dx = anchors[i+1][0] - anchors[i-1][0]; dy = anchors[i+1][1] - anchors[i-1][1]
    L = math.hypot(dx, dy)
    return (dx/L, dy/L) if L > 1e-6 else (1.0, 0.0)

# For a segment A -> B with tangents tA, tB, use handles at
#    HA = A + tA * (|B-A| / 3)
#    HB = B - tB * (|B-A| / 3)
# Override endpoint tangents at NKT (vertical) and SBT (along soundboard slope).
# Segment lengths L[i] = |anchors[i+1] - anchors[i]|
seg_len = [math.hypot(anchors[i+1][0]-anchors[i][0],
                       anchors[i+1][1]-anchors[i][1])
           for i in range(len(anchors)-1)]
# Per-node handle length.  Internal nodes: equal-length handles on both sides
# (average of neighboring segment lengths / 3).  Endpoints keep their overrides.
handle_len = []
for j in range(len(anchors)):
    if j == 0:                         # NKT — H1 length 2x of the first segment / 3
        handle_len.append(seg_len[0] / 3.0 * 2.0)
    elif j == len(anchors) - 1:        # SBT — H2 length 1.5x of the last segment / 3 (halved from 3x)
        handle_len.append(seg_len[-1] / 3.0 * 1.5)
    else:                              # Internal — equal on both sides
        handle_len.append((seg_len[j-1] + seg_len[j]) / 6.0)

path_parts = [f'M {anchors[0][0]:.3f},{anchors[0][1]:.3f}']
nkt_handle = None
sbt_handle = None
per_anchor_handles = {j: [None, None] for j in range(len(anchors))}
if use_c2:
    # ---- C² clamped cubic spline (curvature-continuous) --------------------
    # Parametrize by cumulative chord length. Clamped tangents at NKT (vertical)
    # and SBT (along soundboard slope).  scipy CubicSpline gives C².
    from scipy.interpolate import CubicSpline as _CS
    _pts_arr = [list(a) for a in anchors]
    _pts_arr = np.array(_pts_arr) if False else __import__('numpy').array(_pts_arr)
    import numpy as _np
    _segs = _np.hypot(_np.diff(_pts_arr[:,0]), _np.diff(_pts_arr[:,1]))
    _t = _np.concatenate([[0], _np.cumsum(_segs)])
    _Ltot = _t[-1]
    # C² clamped cubic spline with endpoint tangent magnitudes chosen so the
    # implicit Bezier handles at NKT and SBT match H1 = 2x, H2 = 1.5x of
    # (segment_length / 3) — matches the rest of the layout exactly.
    H1_MAG = 2.0; H2_MAG = 1.5
    _sbL = math.hypot(1.0, sb_slope)
    _t_nkt = (0.0, -1.0)
    _t_sbt = (-1.0/_sbL, sb_slope/_sbL)
    _csx = _CS(_t, _pts_arr[:,0],
               bc_type=((1, _t_nkt[0]*H1_MAG), (1, _t_sbt[0]*H2_MAG)))
    _csy = _CS(_t, _pts_arr[:,1],
               bc_type=((1, _t_nkt[1]*H1_MAG), (1, _t_sbt[1]*H2_MAG)))
    # Emit path as a polyline of sampled points (C²-faithful rendering)
    _ts = _np.linspace(0, _Ltot, 400)
    _sx = _csx(_ts); _sy = _csy(_ts)
    _plist = " ".join(f"L {_sx[k]:.3f},{_sy[k]:.3f}" for k in range(1, len(_ts)))
    path_parts = [f'M {_sx[0]:.3f},{_sy[0]:.3f} {_plist}']
    # Set H1/H2 handle positions (from the spline's derivative at the ends)
    _dx_s = _csx(0, 1); _dy_s = _csy(0, 1)
    _dx_e = _csx(_Ltot, 1); _dy_e = _csy(_Ltot, 1)
    _hlen_start = _Ltot * 0.08
    _hlen_end   = _Ltot * 0.08
    nkt_handle = (anchors[0][0] + _dx_s * _hlen_start/_Ltot,
                  anchors[0][1] + _dy_s * _hlen_start/_Ltot)
    sbt_handle = (anchors[-1][0] - _dx_e * _hlen_end/_Ltot,
                  anchors[-1][1] - _dy_e * _hlen_end/_Ltot)
    elems.append(f'<path class="sb" d="{path_parts[0]}"/>')
else:
    for i in range(len(anchors) - 1):
        A = anchors[i]; B = anchors[i+1]
        tA = tangent(i); tB = tangent(i+1)
        if i == 0:
            tA = (0.0, -1.0)
        if i + 1 == len(anchors) - 1:
            sb_dx, sb_dy = -1.0, sb_slope
            sbL = math.hypot(sb_dx, sb_dy)
            tB = (sb_dx/sbL, sb_dy/sbL)
        HA = (A[0] + tA[0]*handle_len[i],   A[1] + tA[1]*handle_len[i])
        HB = (B[0] - tB[0]*handle_len[i+1], B[1] - tB[1]*handle_len[i+1])
        if i == 0:               nkt_handle = HA
        if i + 1 == len(anchors) - 1: sbt_handle = HB
        per_anchor_handles[i][1]   = HA
        per_anchor_handles[i+1][0] = HB
        path_parts.append(f'C {HA[0]:.3f},{HA[1]:.3f} {HB[0]:.3f},{HB[1]:.3f} '
                          f'{B[0]:.3f},{B[1]:.3f}')
    elems.append(f'<path class="sb" d="{" ".join(path_parts)}"/>')

# Small black dots at every anchor (NKT, internal N1..N5, SBT).
BEZ = '#1060d0'
NDOT_NODE   = 6.0
NDOT_HANDLE = 6.0
for a in anchors:
    elems.append(f'<circle cx="{a[0]:.3f}" cy="{a[1]:.3f}" r="{NDOT_NODE}" fill="#000"/>')
# Label internal anchors N1..Nk
for j in range(1, len(anchors) - 1):
    nx, ny = anchors[j]
    lbl = f'N{j}'
    elems.append(f'<text x="{nx+10:.3f}" y="{ny-8:.3f}" font-family="sans-serif" '
                 f'font-size="16" font-weight="bold" fill="#000">{lbl}</text>')
# Label just the endpoints.  Place NKT to the right (inside the viewBox); SBT below-right.
elems.append(f'<text x="{anchors[0][0]+12:.3f}" y="{anchors[0][1]-8:.3f}" '
             f'font-family="sans-serif" font-size="18" font-weight="bold" '
             f'fill="#000">NKT</text>')
elems.append(f'<text x="{anchors[-1][0]+12:.3f}" y="{anchors[-1][1]+6:.3f}" '
             f'font-family="sans-serif" font-size="18" font-weight="bold" '
             f'fill="#000">SBT</text>')

# H1 (NKT handle) and H2 (SBT handle): blue line from anchor to handle + blue open dot.
for (anchor, h, lbl) in [(anchors[0], nkt_handle, 'H1'),
                          (anchors[-1], sbt_handle, 'H2')]:
    elems.append(f'<line x1="{anchor[0]:.3f}" y1="{anchor[1]:.3f}" '
                 f'x2="{h[0]:.3f}" y2="{h[1]:.3f}" '
                 f'stroke="{BEZ}" stroke-width="1.2"/>')
    elems.append(f'<circle cx="{h[0]:.3f}" cy="{h[1]:.3f}" r="{NDOT_HANDLE}" '
                 f'fill="#fff" stroke="{BEZ}" stroke-width="1.6"/>')
    elems.append(f'<text x="{h[0]+10:.3f}" y="{h[1]-5:.3f}" font-family="sans-serif" '
                 f'font-size="16" font-weight="bold" fill="{BEZ}">{lbl}</text>')

# Internal nodes: draw each node's two handles (incoming & outgoing) as blue dashed
# lines with blue open circles at handle tips.  Internal anchors are indices 1..N-2.
for j in range(1, len(anchors)-1):
    hIn, hOut = per_anchor_handles[j]
    a = anchors[j]
    for h in (hIn, hOut):
        if h is None: continue
        elems.append(f'<line x1="{a[0]:.3f}" y1="{a[1]:.3f}" '
                     f'x2="{h[0]:.3f}" y2="{h[1]:.3f}" '
                     f'stroke="{BEZ}" stroke-width="0.8"/>')
        elems.append(f'<circle cx="{h[0]:.3f}" cy="{h[1]:.3f}" r="{NDOT_HANDLE-1}" '
                     f'fill="#fff" stroke="{BEZ}" stroke-width="1.2"/>')

# Dimension line between column and bass string (50 mm, uniform since both are parallel vertical)
bass_tx = (BASS_X_IN - x0) * IN_TO_MM
# Place the dimension at the bass-flat y-level (most visible spot)
dim_ty = (y1 - BASS_YF_IN) * IN_TO_MM + 8
elems.append(f'<line x1="{col_right_tx:.2f}" y1="{dim_ty:.2f}" '
             f'x2="{bass_tx:.2f}" y2="{dim_ty:.2f}" '
             f'stroke="#c00" stroke-width="1.5"/>')
for xm in (col_right_tx, bass_tx):
    elems.append(f'<line x1="{xm:.2f}" y1="{dim_ty-5:.2f}" x2="{xm:.2f}" y2="{dim_ty+5:.2f}" '
                 f'stroke="#c00" stroke-width="1.5"/>')
elems.append(f'<text class="big" x="{(col_right_tx+bass_tx)/2:.2f}" y="{dim_ty-2:.2f}" '
             f'text-anchor="middle" fill="#c00" style="font-size:8px">{COL_TO_BASS_MM:.0f} mm</text>')

# Key diagonals (1.53" at 78deg from horizontal)
for r in srows:
    if r['key_tip']:
        kx, ky = r['key_tip']
        elems.append(f'<line class="key" x1="{tx(r["x"]):.3f}" y1="{ty(r["yf"]):.3f}" '
                     f'x2="{tx(kx):.3f}" y2="{ty(ky):.3f}"/>')

# Landmark dots — diameter = 2 x widest string stroke-width (#38 E2, 0.104" = 2.642 mm)
DOT = max(diameter_in(n) for n in range(1, 48)) * IN_TO_MM
# Disc positions derived from the string table, not the DXF ticks.
# Each semitone shortens the string by factor 2^(-1/12) = 0.944 (5.613% reduction).
#   Flat    (pedal up)    = full active length (yg -> yf)
#   Natural (pedal mid)   = at yg + length * (1/2^(1/12))       from grommet
#   Sharp   (pedal down)  = at yg + length * (1/2^(1/12))^2
# Lowest two bass strings (#46 D1, #47 C1) have no sharping discs.
SEMITONE = 2 ** (-1.0/12.0)   # ~0.94387
for r in srows:
    num = r['num']
    L = r['yf'] - r['yg']
    # grommet (bottom)
    elems.append(f'<circle class="g" cx="{tx(r["x"]):.3f}" cy="{ty(r["yg"]):.3f}" r="{DOT}"/>')
    # flat = top of active string
    elems.append(f'<circle class="f" cx="{tx(r["x"]):.3f}" cy="{ty(r["yf"]):.3f}" r="{DOT}"/>')
    # natural + sharp discs only if string has discs (#1..#45)
    if num <= 45:
        y_nat = r['yg'] + L * SEMITONE
        y_shp = r['yg'] + L * SEMITONE * SEMITONE
        elems.append(f'<circle class="n" cx="{tx(r["x"]):.3f}" cy="{ty(y_nat):.3f}" r="{DOT}"/>')
        elems.append(f'<circle class="s" cx="{tx(r["x"]):.3f}" cy="{ty(y_shp):.3f}" r="{DOT}"/>')
    # tuning pin
    if r['key_tip']:
        kx, ky = r['key_tip']
        elems.append(f'<circle class="p" cx="{tx(kx):.3f}" cy="{ty(ky):.3f}" r="{DOT}"/>')

# String number + note name along the bottom (every string, label follows grommet curve)
for r in srows_by_x:
    letter, octave = NOTE_TABLE[r['num'] - 1]
    elems.append(f'<text class="sml" x="{tx(r["x"]):.3f}" y="{ty(r["yg"])+18:.3f}" '
                 f'fill="#000" text-anchor="middle">{r["num"]}</text>')
    elems.append(f'<text class="sml" x="{tx(r["x"]):.3f}" y="{ty(r["yg"])+32:.3f}" '
                 f'fill="#000" text-anchor="middle" font-weight="bold">{letter}{octave}</text>')

# (legend removed per user request; keep these for the console print at the end)
total_span_mm = (max(xs) - min(xs)) * IN_TO_MM
longest_mm = max(r['len'] for r in srows) * IN_TO_MM
shortest_mm = min(r['len'] for r in srows) * IN_TO_MM
elems.append('</svg>')
with open(OUT, 'w') as f:
    f.write('\n'.join(elems))
print(f"Wrote {OUT}")
print(f"SVG canvas: {total_W:.1f} x {H_mm:.1f} mm")
print(f"Geometry area: {W_mm:.1f} x {H_mm:.1f} mm")
print(f"Stringband span: {total_span_mm:.2f} mm")
print(f"String 1 (G7) flat length: {shortest_mm:.2f} mm")
print(f"String 47 (C1) flat length: {longest_mm:.2f} mm")
