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
# treble end: ST moved up along soundboard line until horizontal to G7 flat (yf).
SEMITONE_R = 2.0 ** (-1.0/12.0)
y_treble_end_in = treble_r['yf']                              # horizontal to G7 flat
x_treble_end_in = bx_in + (y_treble_end_in - by_in) / sb_slope
# SB: previous ST position, where soundboard met the G7 SHARP-disc y.
sb_point_y_in = treble_r['yg'] + (treble_r['yf'] - treble_r['yg']) * SEMITONE_R * SEMITONE_R
sb_point_x_in = bx_in + (sb_point_y_in - by_in) / sb_slope
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

# Two pins per string, both 6 mm radius (= 12 mm diameter):
#   FLAT  pin (red)    - tangent to the flat point (yf), center 6 mm to the right
#   STRING-end pin (purple) - tangent to the end of the string's key line
#                             (key_tip), center 6 mm further along the key direction
# Buffer ring at 12 mm radius around each pin center (6 mm beyond pin edge).
PIN_R = 3.0         # purple string-end pin radius
FLAT_PIN_R = 3.0    # red flat pin radius
BUF_R = 12.0
KEY_ANG = math.radians(78.0)   # string's tuning-key angle from horizontal in DXF
kdx = math.cos(KEY_ANG)        # SVG: same x
kdy = -math.sin(KEY_ANG)       # SVG: y flipped
for r in srows_by_x:
    fx = tx(r['x']); fy = ty(r['yf'])
    # --- FLAT pin (red, 3 mm radius) — NO buffer (flats don't have buffers) ---
    rcx = fx + FLAT_PIN_R; rcy = fy
    elems.append(f'<circle cx="{rcx:.3f}" cy="{rcy:.3f}" r="{FLAT_PIN_R}" '
                 f'fill="#c00000" stroke="#600" stroke-width="0.4"/>')
    # --- STRING-END pin (purple) tangent to key_tip with HORIZONTAL radius:
    # pin center at the same y as key_tip, offset 6 mm to the right.
    if r.get('key_tip'):
        kx_svg = tx(r['key_tip'][0]); ky_svg = ty(r['key_tip'][1])
        pcx = kx_svg + PIN_R; pcy = ky_svg
        elems.append(f'<circle cx="{pcx:.3f}" cy="{pcy:.3f}" r="{BUF_R}" '
                     f'fill="none" stroke="#000" stroke-width="0.4"/>')
        elems.append(f'<circle cx="{pcx:.3f}" cy="{pcy:.3f}" r="{PIN_R}" '
                     f'fill="#9467bd" stroke="#333" stroke-width="0.4"/>')

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
    # ---- NECK OUTLINE: closed Bezier path with 4 corners (NT, ST, SB, NB) ----
    # Each corner has a sharp turn.  Interior of path:
    #   NT -> N1, N2, N3 -> ST   : top arc (high above the sharp-buffer rings)
    #   ST -> SB                 : straight (down the soundboard line)
    #   SB -> NB                 : bottom arc, barely touching the TOP of the
    #                              sharp-buffer circles from the outside
    #   NB -> NT                 : straight (up the column)
    from scipy.interpolate import CubicSpline as _CS
    import numpy as _np

    # Top polyline: OVER (above) pin buffers (12 mm rings around red flat pins).
    # Bottom polyline: UNDER (below) sharp buffers.  Compute each envelope.
    SEMIT_TOP = 2.0 ** (-1.0/12.0)
    _circles = []       # sharp-buffer circles (for BOTTOM arc)
    _pin_circles = []   # pin-buffer circles at PURPLE string-end pins (for TOP arc)
    PIN_R_LOC = 3.0
    for r in srows_by_x:
        if r['num'] <= 45:
            sy = r['yg'] + (r['yf']-r['yg']) * SEMIT_TOP * SEMIT_TOP
            _circles.append((tx(r['x']), ty(sy), r['num']))
        # purple pin (string-end) buffer center: 3 mm right of key_tip position
        if r.get('key_tip'):
            pxc = tx(r['key_tip'][0]) + PIN_R_LOC
            pyc = ty(r['key_tip'][1])
            _pin_circles.append((pxc, pyc, r['num']))
    _circles.sort()
    _pin_circles.sort()
    def _common_tangent(C1, C2, r, upper):
        """External common tangent.  upper=True -> smaller y (above); False -> below."""
        dxv = C2[0]-C1[0]; dyv = C2[1]-C1[1]
        L = math.hypot(dxv, dyv) or 1.0
        ux, uy = dxv/L, dyv/L
        p1 = (-uy, ux); p2 = (uy, -ux)
        if upper:
            nx, ny = p1 if p1[1] < p2[1] else p2
        else:
            nx, ny = p1 if p1[1] > p2[1] else p2
        return (C1[0]+r*nx, C1[1]+r*ny), (C2[0]+r*nx, C2[1]+r*ny)
    # TOP polyline: upper tangents of PIN buffers
    _pin_tans = []
    for i in range(len(_pin_circles)-1):
        t1, t2 = _common_tangent(_pin_circles[i][:2], _pin_circles[i+1][:2], 12.0, True)
        _pin_tans.append(t1); _pin_tans.append(t2)
    # BOTTOM polyline: lower tangents of SHARP buffers (neck bottom dips below sharps)
    _tans = []
    for i in range(len(_circles)-1):
        t1, t2 = _common_tangent(_circles[i][:2], _circles[i+1][:2], 12.0, False)
        _tans.append(t1); _tans.append(t2)
    # Dedup consecutive close points (bottom = sharp-buffer lower envelope)
    _poly = [_tans[0]]
    for p in _tans[1:]:
        if math.hypot(p[0]-_poly[-1][0], p[1]-_poly[-1][1]) > 0.5:
            _poly.append(p)
    # Dedup pin-buffer upper envelope
    _pin_poly = [_pin_tans[0]]
    for p in _pin_tans[1:]:
        if math.hypot(p[0]-_pin_poly[-1][0], p[1]-_pin_poly[-1][1]) > 0.5:
            _pin_poly.append(p)
    # Douglas-Peucker with constraint: simplified polyline must still be outside
    # every buffer circle.  Try increasing eps until we can't reduce more.
    def _dp(pts, eps):
        if len(pts) < 3: return list(pts)
        first = _np.array(pts[0]); last = _np.array(pts[-1])
        dline = last - first; L2 = float(_np.dot(dline, dline)) or 1.0
        best_i = 0; best_d = 0.0
        for i in range(1, len(pts)-1):
            p = _np.array(pts[i]) - first
            proj = float(_np.dot(p, dline)) / L2
            closest = first + dline * proj
            d = float(_np.linalg.norm(_np.array(pts[i]) - closest))
            if d > best_d: best_d = d; best_i = i
        if best_d > eps:
            left = _dp(pts[:best_i+1], eps); right = _dp(pts[best_i:], eps)
            return left[:-1] + right
        return [pts[0], pts[-1]]
    def _poly_ok(pts):
        # check each segment's closest approach to every circle
        for i in range(len(pts)-1):
            A = _np.array(pts[i]); B = _np.array(pts[i+1])
            ab = B - A; L2 = float(_np.dot(ab, ab)) or 1.0
            for (cx, cy, _n) in _circles:
                ap = _np.array([cx, cy]) - A
                t = max(0.0, min(1.0, float(_np.dot(ap, ab))/L2))
                closest = A + ab*t
                d = float(_np.linalg.norm(_np.array([cx, cy]) - closest))
                if d < 11.9: return False
        return True
    best_poly = _poly; best_eps = 0.5
    for eps in (1.0, 2.0, 3.0, 5.0, 8.0, 12.0):
        simp = _dp(_poly, eps)
        if _poly_ok(simp):
            best_poly = simp; best_eps = eps
        else:
            break
    # TOP arc drawn as the STRAIGHT POLYLINE through tangent points (no spline yet).
    _top_anchors_full = [(nkt_x, nkt_y)] + best_poly + [(sbt_x, sbt_y)]
    top_arc = " ".join(f"L {p[0]:.3f},{p[1]:.3f}" for p in _top_anchors_full[1:])
    print(f"TOP ARC polyline: {len(best_poly)} tangent anchors (eps={best_eps} mm)")

    # Bottom arc SB -> NB: iteratively select buffer-top tangent points so the
    # spline stays outside every sharp-buffer circle.  Start with the highest
    # buffer tops, then add whichever circle the curve most violates, repeat.
    SEMIT = 2.0 ** (-1.0/12.0)
    buf_centers = []    # (cx, cy, n)
    buf_tops = []       # (top_x, top_y, n)
    for r in srows_by_x:
        if r['num'] > 45: continue
        sy = r['yg'] + (r['yf']-r['yg']) * SEMIT * SEMIT
        cx, cy = tx(r['x']), ty(sy)
        buf_centers.append((cx, cy, r['num']))
        buf_tops.append((cx, cy - 12.0, r['num']))
    # NB position
    _e1r = next(r for r in srows if r['num'] == 45)
    _e1_sy_in = _e1r['yg'] + (_e1r['yf'] - _e1r['yg']) * SEMIT * SEMIT
    _NB_x = col_left_tx
    _NB_y = ty(_e1_sy_in) + 12.0
    # Sort buf_tops by x (ascending = bass to treble)
    buf_tops.sort(key=lambda p: p[0])
    # Iterative selection: start with just endpoints, add anchors to fix violations
    selected_tangents = []   # list of (x, y, n) tangent points from buf_tops
    def _build_bot(sel):
        # Build anchor list ordered by x: NB (leftmost), sel (bass->treble), SB (rightmost)
        ordered = sorted(sel, key=lambda p: p[0])
        nodes = [(_NB_x, _NB_y)] + [(p[0], p[1]) for p in ordered] + [(sbt_x, sbt_y)]
        arr = _np.array(nodes)
        tt = _np.arange(len(nodes), dtype=float)
        cx = _CS(tt, arr[:,0], bc_type='natural')
        cy = _CS(tt, arr[:,1], bc_type='natural')
        ss = _np.linspace(0, tt[-1], 1500)
        return _np.column_stack([cx(ss), cy(ss)])
    max_iter = 15
    for _ in range(max_iter):
        bc = _build_bot(selected_tangents)
        worst_n = None; worst_pen = 0.0; worst_p = None
        for (cx, cy, n) in buf_centers:
            d = float(_np.min(_np.hypot(bc[:,0]-cx, bc[:,1]-cy)))
            pen = 12.0 - d
            if pen > worst_pen:
                worst_pen = pen; worst_n = n
                worst_p = next(t for t in buf_tops if t[2] == n)
        if worst_pen < 0.2: break   # converged
        selected_tangents.append(worst_p)
    # Final bottom arc as straight polyline through tangent points
    bot_nodes_srt = sorted(selected_tangents, key=lambda p: p[0])
    bot_nodes = [(sbt_x, sbt_y)] + [(p[0], p[1]) for p in reversed(bot_nodes_srt)] + [(_NB_x, _NB_y)]
    _bp = _np.array([list(n) for n in bot_nodes])
    _bt = _np.arange(len(bot_nodes), dtype=float)
    _bcsx = _CS(_bt, _bp[:,0], bc_type='natural')
    _bcsy = _CS(_bt, _bp[:,1], bc_type='natural')
    _bts = _np.linspace(0, _bt[-1], 300)
    _bsx = _bcsx(_bts); _bsy = _bcsy(_bts)
    bot_arc = " ".join(f"L {_bsx[k]:.3f},{_bsy[k]:.3f}" for k in range(1, len(_bts)))

    # Build the closed outline CCW starting at NB:
    #   NB -> bottom of E1 sharp buffer ->
    #        (lower tangent envelope of SHARP buffers, bass->treble) ->
    #        bottom of G7 sharp buffer -> SB -> ST ->
    #        top of G7 pin buffer ->
    #        (upper tangent envelope of PIN buffers, treble->bass) ->
    #        top of bass-most pin buffer -> NT -> close back to NB.
    _NT = anchors[0]; _ST = anchors[-1]
    _SB = (tx(sb_point_x_in), ty(sb_point_y_in))
    _NB = (_NB_x, _NB_y)
    # sharp lower envelope (bass->treble): _poly already has tangent pts in order
    # (because _tans was built iterating _circles[i], _circles[i+1] bass->treble).
    bot_env = _poly      # from E1-ish to G7-ish sharp buffer bottoms
    # pin upper envelope (bass->treble) -> need reversed for treble->bass
    top_env_rev = list(reversed(_pin_poly))
    # Split path into 4 smooth sections separated by the 4 corners (NB, SB, ST, NT):
    #   bottom section:  NB -> bot_env -> SB     (tangent to sharp buffers, under)
    #   right straight:  SB -> ST                (just two points)
    #   top section:     ST -> top_env_rev -> NT (tangent to pin buffers, over)
    #   left straight:   NT -> NB                (column)
    # Only the bottom and top sections have interior nodes to reduce.  Within
    # each section we build a C²-natural cubic spline and use iterative
    # single-node removal: try dropping each interior node; if the resulting
    # C² spline (sampled) still stays outside every buffer circle, accept the
    # removal.  Loop until no more nodes can be dropped.
    all_circles = _pin_circles + _circles
    def _spline_through(section, N=600):
        arr = _np.array([list(p) for p in section])
        tt = _np.arange(len(section), dtype=float)
        cx = _CS(tt, arr[:,0], bc_type='natural')
        cy = _CS(tt, arr[:,1], bc_type='natural')
        ss = _np.linspace(0, tt[-1], N)
        return _np.column_stack([cx(ss), cy(ss)])
    def _spline_outside(section, r=12.0, tol=0.05):
        pts = _spline_through(section)
        for (cx, cy, _n) in all_circles:
            d_ = float(_np.min(_np.hypot(pts[:,0]-cx, pts[:,1]-cy)))
            if d_ < r - tol: return False
        return True
    def _reduce(section):
        # Build-up approach: start with just corners, add anchors from the
        # candidate pool one at a time (greedy — pick the one that resolves the
        # worst circle violation) until the C² spline stays outside all circles.
        corners = [section[0], section[-1]]
        candidates = section[1:-1]
        cur = list(corners)
        max_iter = 40
        for _ in range(max_iter):
            pts = _spline_through(cur)
            worst_c = None; worst_pen = 0.0
            for (cx, cy, n) in all_circles:
                d = float(_np.min(_np.hypot(pts[:,0]-cx, pts[:,1]-cy)))
                pen = 12.0 - d
                if pen > worst_pen: worst_pen = pen; worst_c = (cx, cy)
            if worst_pen < 0.1:
                break
            # Add the candidate nearest (horizontally) to the worst circle.
            used = {tuple(p) for p in cur}
            avail = [p for p in candidates if tuple(p) not in used]
            if not avail: break
            best = min(avail, key=lambda p: abs(p[0]-worst_c[0]))
            # Insert in x-order (or reversed, depending on section)
            # Determine order based on original section order
            orig_idx = {tuple(p): i for i, p in enumerate(section)}
            cur.append(best)
            cur.sort(key=lambda p: orig_idx.get(tuple(p), 0))
        return cur
    bot_section = [_NB] + list(bot_env) + [_SB]
    top_section = [_ST] + list(top_env_rev) + [_NT]
    # Replace the Douglas-Peucker polyline with a proper convex-hull-style
    # envelope: tangent lines between circles that are on the envelope, arcs on
    # each envelope circle from entry to exit tangent point.  Skipped circles
    # don't appear on the path.
    def _lower_envelope_indices(centers_svg_y_flipped):
        """Indices of points on the LOWER hull (bottom side when viewed in math
        y-up convention).  Input points should already be y-flipped if coming
        from SVG y-down (so 'lower' visually = larger original y = smaller
        flipped y)."""
        def cross(O, A, B):
            return (A[0]-O[0])*(B[1]-O[1]) - (A[1]-O[1])*(B[0]-O[0])
        pts = sorted(enumerate(centers_svg_y_flipped), key=lambda x: (x[1][0], x[1][1]))
        hull = []
        for i, p in pts:
            while len(hull) >= 2 and cross(hull[-2][1], hull[-1][1], p) <= 0:
                hull.pop()
            hull.append((i, p))
        return [h[0] for h in hull]

    def _upper_envelope_indices(centers_svg_y_flipped):
        # Upper hull: same algorithm but with cross >= 0
        def cross(O, A, B):
            return (A[0]-O[0])*(B[1]-O[1]) - (A[1]-O[1])*(B[0]-O[0])
        pts = sorted(enumerate(centers_svg_y_flipped), key=lambda x: (x[1][0], x[1][1]))
        hull = []
        for i, p in pts:
            while len(hull) >= 2 and cross(hull[-2][1], hull[-1][1], p) >= 0:
                hull.pop()
            hull.append((i, p))
        return [h[0] for h in hull]

    def _build_tangent_arc_path(env_circles, r, side):
        """env_circles: list of (cx, cy) on the envelope in order.  side='lower'
        or 'upper'.  Returns an SVG path-data fragment with M/L/A commands."""
        from math import atan2, cos, sin, pi
        def common_tangent(C1, C2):
            dxv = C2[0]-C1[0]; dyv = C2[1]-C1[1]
            L = math.hypot(dxv, dyv) or 1.0
            ux, uy = dxv/L, dyv/L
            p1 = (-uy, ux); p2 = (uy, -ux)
            if side == 'lower':
                nx, ny = p1 if p1[1] > p2[1] else p2
            else:
                nx, ny = p1 if p1[1] < p2[1] else p2
            return ((C1[0]+r*nx, C1[1]+r*ny), (C2[0]+r*nx, C2[1]+r*ny))
        # Compute tangent points at each envelope circle
        parts = []
        prev_exit = None
        for i, C in enumerate(env_circles):
            if i+1 < len(env_circles):
                t_out, _ = common_tangent(C, env_circles[i+1])
            else:
                t_out = None
            if prev_exit is None:
                entry = None
            else:
                entry = prev_exit
            # Emit arc on this circle from entry to t_out (if both exist)
            if entry is not None and t_out is not None:
                # angle from circle center to entry and to t_out
                a0 = atan2(entry[1]-C[1], entry[0]-C[0])
                a1 = atan2(t_out[1]-C[1], t_out[0]-C[0])
                # sweep flag: 0 = CCW (in SVG y-down = visually CW), 1 = CW
                # For lower envelope going left-to-right, arc curves down (outer): sweep=0
                # For upper envelope going left-to-right, arc curves up: sweep=1
                sweep_flag = 0 if side == 'lower' else 1
                # large-arc flag: always 0 for short arcs between neighboring tangents
                parts.append(f"A {r:.2f} {r:.2f} 0 0 {sweep_flag} {t_out[0]:.3f},{t_out[1]:.3f}")
            elif entry is None and t_out is not None:
                # First circle: move to its exit tangent point (no arc yet)
                parts.append(f"M {t_out[0]:.3f},{t_out[1]:.3f}")
            # Tangent segment to next circle's entry
            if t_out is not None and i+1 < len(env_circles):
                _, nxt_entry = common_tangent(C, env_circles[i+1])
                parts.append(f"L {nxt_entry[0]:.3f},{nxt_entry[1]:.3f}")
                prev_exit = nxt_entry
            else:
                prev_exit = None
        return " ".join(parts)

    # Build lower envelope for sharp buffers and upper envelope for pin buffers
    r_buf = 12.0
    sharp_c_flip = [(c[0], -c[1]) for c in _circles]
    pin_c_flip   = [(c[0], -c[1]) for c in _pin_circles]
    sharp_env_idx = _lower_envelope_indices(sharp_c_flip)   # "lower" in SVG = larger y
    pin_env_idx   = _upper_envelope_indices(pin_c_flip)     # "upper" in SVG = smaller y
    sharp_env_centers = [(_circles[i][0], _circles[i][1]) for i in sharp_env_idx]
    pin_env_centers   = [(_pin_circles[i][0], _pin_circles[i][1]) for i in pin_env_idx]
    # Build path fragments
    bot_tangent_arc = _build_tangent_arc_path(sharp_env_centers, r_buf, 'lower')
    top_tangent_arc = _build_tangent_arc_path(list(reversed(pin_env_centers)), r_buf, 'upper')

    # OLD dp_safe remains defined below for fallback but we won't use it.
    def _dp_safe(pts_section, circles, r=12.0, tol_check=0.5):
        """Douglas-Peucker with constraint: simplified polyline stays outside
        every circle in 'circles' (distance from any circle center to any
        simplified segment >= r - tol_check)."""
        def seg_outside(A, B, circles):
            ab = _np.array(B) - _np.array(A); L2 = float(_np.dot(ab, ab)) or 1.0
            for (cx, cy, _n) in circles:
                ap = _np.array([cx, cy]) - _np.array(A)
                t = max(0.0, min(1.0, float(_np.dot(ap, ab))/L2))
                closest = _np.array(A) + ab*t
                d_ = float(_np.linalg.norm(_np.array([cx, cy]) - closest))
                if d_ < r - tol_check: return False
            return True
        def dp(pts, eps):
            if len(pts) < 3: return list(pts)
            A = _np.array(pts[0]); B = _np.array(pts[-1])
            ab = B - A; L2 = float(_np.dot(ab, ab)) or 1.0
            best_i = 0; best_d = 0.0
            for i in range(1, len(pts)-1):
                p = _np.array(pts[i]) - A
                proj = float(_np.dot(p, ab))/L2
                closest = A + ab*proj
                d_ = float(_np.linalg.norm(_np.array(pts[i]) - closest))
                if d_ > best_d: best_d = d_; best_i = i
            if best_d > eps:
                left = dp(pts[:best_i+1], eps)
                right = dp(pts[best_i:], eps)
                return left[:-1] + right
            return [pts[0], pts[-1]]
        def simp_outside(simp, circles):
            for i in range(len(simp)-1):
                if not seg_outside(simp[i], simp[i+1], circles): return False
            return True
        # Try increasing tolerances; keep the most aggressive simplification
        # whose resulting polyline stays outside all circles.
        best = list(pts_section)
        for eps in (1.0, 2.0, 4.0, 8.0, 16.0, 32.0):
            simp = dp(pts_section, eps)
            if simp_outside(simp, circles) and len(simp) < len(best):
                best = simp
        return best
    bot_reduced = _dp_safe(bot_section, _circles)
    top_reduced = _dp_safe(top_section, _pin_circles)
    # Build the closed CCW path with tangent lines + circle arcs:
    #   NB -> lower-envelope tangent-arc of sharp buffers -> SB -> ST ->
    #   upper-envelope tangent-arc of pin buffers -> NT -> close
    parts = [f"M {_NB[0]:.3f},{_NB[1]:.3f}"]
    # Tangent from NB to first sharp envelope circle's entry
    if sharp_env_centers:
        # The lower arc builder starts with a "M ..." at the first exit tangent
        # — we want to instead L from NB into that chain.  Strip the leading M.
        frag = bot_tangent_arc
        if frag.startswith("M "):
            # Replace leading M with L
            frag = "L" + frag[1:]
        parts.append(frag)
    parts.append(f"L {_SB[0]:.3f},{_SB[1]:.3f}")
    parts.append(f"L {_ST[0]:.3f},{_ST[1]:.3f}")
    if pin_env_centers:
        frag2 = top_tangent_arc
        if frag2.startswith("M "):
            frag2 = "L" + frag2[1:]
        parts.append(frag2)
    parts.append(f"L {_NT[0]:.3f},{_NT[1]:.3f}")
    parts.append("Z")
    d_str = " ".join(parts)
    total = len(bot_reduced) + len(top_reduced)   # corners counted once per section
    # corners NB, SB, ST, NT appear at section boundaries so they're counted 4x total
    # in the raw sum above.  Unique anchors = total - 2 (since SB and ST are shared
    # with the straight links).  Just report the interior-reduced counts.
    print(f"NECK BEZIER reduced: bot={len(bot_reduced)}  top={len(top_reduced)}  "
          f"unique-anchors={len(bot_reduced) + len(top_reduced) - 2}", flush=True)
    elems.append(f'<path d="{d_str}" fill="none" stroke="#ff69b4" stroke-width="1.6"/>')
    # Black dots + numeric labels at every anchor of the neck outline (CCW from NB).
    # Sequence: NB = bot[0], bot[1..last-1], SB = bot[-1], ST = top[0], top[1..last-1], NT = top[-1]
    ordered_anchors = [_NB] + list(sharp_env_centers) + [_SB, _ST] + list(reversed(pin_env_centers)) + [_NT]
    for _i, (nx, ny) in enumerate(ordered_anchors):
        elems.append(f'<circle cx="{nx:.3f}" cy="{ny:.3f}" r="3" fill="#000"/>')
        elems.append(f'<text x="{nx+4:.3f}" y="{ny-4:.3f}" font-family="sans-serif" '
                     f'font-size="10" fill="#000">{_i+1}</text>')
    # blank handles (corners = no smooth handles)
    nkt_handle = (anchors[0][0], anchors[0][1])
    sbt_handle = (anchors[-1][0], anchors[-1][1])
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
# Only mark endpoints now (N1..N3 removed per request).
elems.append(f'<circle cx="{anchors[0][0]:.3f}" cy="{anchors[0][1]:.3f}" r="{NDOT_NODE}" fill="#000"/>')
elems.append(f'<circle cx="{anchors[-1][0]:.3f}" cy="{anchors[-1][1]:.3f}" r="{NDOT_NODE}" fill="#000"/>')
# Label just the endpoints.  Place NKT to the right (inside the viewBox); SBT below-right.
elems.append(f'<text x="{anchors[0][0]+12:.3f}" y="{anchors[0][1]-8:.3f}" '
             f'font-family="sans-serif" font-size="18" font-weight="bold" '
             f'fill="#000">NT</text>')
# NB: a point on the column's outer (left) face, horizontally aligned with the
# BOTTOM of the 12 mm buffer ring around the E1 (string #45) sharp-disc position.
NB_x = col_left_tx                                            # same x as NT
_e1_row = next(r for r in srows if r['num'] == 45)
_e1_L = _e1_row['yf'] - _e1_row['yg']
_e1_sharp_y_in = _e1_row['yg'] + _e1_L * SEMITONE_R * SEMITONE_R
NB_y = ty(_e1_sharp_y_in) + 12.0                              # buffer radius
elems.append(f'<circle cx="{NB_x:.3f}" cy="{NB_y:.3f}" r="8" fill="#000"/>')
elems.append(f'<text x="{NB_x+12:.3f}" y="{NB_y+6:.3f}" font-family="sans-serif" '
             f'font-size="18" font-weight="bold" fill="#000">NB</text>')
elems.append(f'<text x="{anchors[-1][0]+12:.3f}" y="{anchors[-1][1]+6:.3f}" '
             f'font-family="sans-serif" font-size="18" font-weight="bold" '
             f'fill="#000">ST</text>')
# SB point: previous ST location (on soundboard line at G7 sharp y)
_sb_svg_x = tx(sb_point_x_in); _sb_svg_y = ty(sb_point_y_in)
elems.append(f'<circle cx="{_sb_svg_x:.3f}" cy="{_sb_svg_y:.3f}" r="8" fill="#000"/>')
elems.append(f'<text x="{_sb_svg_x+12:.3f}" y="{_sb_svg_y+6:.3f}" '
             f'font-family="sans-serif" font-size="18" font-weight="bold" '
             f'fill="#000">SB</text>')

# NT1 (NT handle) and SBT2 (SBT handle): blue line from anchor to handle + blue open dot.
for (anchor, h, lbl) in [(anchors[0], nkt_handle, 'NT1'),
                          (anchors[-1], sbt_handle, 'ST2')]:
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

# (50 mm dimension line between column and bass string removed per user request.)

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
    # (flat marker at yf is subsumed by the red 12 mm flat pin; no separate dot needed)
    # natural + sharp discs only if string has discs (#1..#45)
    if num <= 45:
        y_nat = r['yg'] + L * SEMITONE
        y_shp = r['yg'] + L * SEMITONE * SEMITONE
        elems.append(f'<circle class="n" cx="{tx(r["x"]):.3f}" cy="{ty(y_nat):.3f}" r="{DOT}"/>')
        # Buffer ring around sharp (moved here from the red flats)
        elems.append(f'<circle cx="{tx(r["x"]):.3f}" cy="{ty(y_shp):.3f}" r="12" '
                     f'fill="none" stroke="#000" stroke-width="0.4"/>')
        elems.append(f'<circle class="s" cx="{tx(r["x"]):.3f}" cy="{ty(y_shp):.3f}" r="{DOT}"/>')
    # (Real tuning pin is drawn as a 6 mm filled circle at the flat point elsewhere.)

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
