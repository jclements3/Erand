#!/usr/bin/env python3
"""Emit a clean side-profile SVG of the Erard harp in mm.

Strings come from the DXF (exact, calibrated). Harp body outlines (column, neck,
soundboard/soundbox, base) are parametric shapes laid out around the string plane
so everything is registered to the same mm coordinate system.

No background image; just vector outlines.
"""
import math, os, ezdxf

SRC_DXF = '/home/james.clements/projects/erand/erand.dxf'
OUT_SVG = '/home/james.clements/projects/erand/harp-profile.svg'
IN_TO_MM = 25.4

# ----------------- note / diameter tables (same as make_svg.py) -----------------
def build_notes():
    letters = ['G','F','E','D','C','B','A']
    out, oct_ = [], 7
    for i in range(47):
        letter = letters[i % 7]
        out.append((letter, oct_))
        if letter == 'A': oct_ -= 1
    return out
NOTES = build_notes()

def diameter_in(n):
    if 1  <= n <= 7 : return 0.025
    if 8  <= n <= 10: return 0.028
    if n == 11      : return 0.030
    if 12 <= n <= 14: return 0.032
    if 15 <= n <= 18: return 0.036
    if 19 <= n <= 21: return 0.040
    if 22 <= n <= 24: return 0.045
    if 25 <= n <= 27: return 0.050
    if 28 <= n <= 29: return 0.045 + 2*0.008
    if 30 <= n <= 31: return 0.050 + 2*0.008
    if n == 32      : return 0.050 + 2*0.013
    if 33 <= n <= 34: return 0.055 + 2*0.013
    if n == 35      : return 0.060 + 2*0.013
    if n == 36      : return 0.060 + 2*0.016
    if n == 37      : return 0.060 + 2*0.019
    if n == 38      : return 0.060 + 2*0.022
    if n == 39      : return 0.020 + 2*0.008
    if n == 40      : return 0.020 + 2*0.010
    if n == 41      : return 0.020 + 2*0.010
    if n == 42      : return 0.022 + 2*0.013
    if n == 43      : return 0.022 + 2*0.013
    if n == 44      : return 0.024 + 2*0.013
    if n == 45      : return 0.025 + 2*0.016
    if n == 46      : return 0.025 + 2*0.018
    if n == 47      : return 0.026 + 2*0.020
    return 0.04

def color_for(letter):
    if letter == 'C': return '#c00000'
    if letter == 'F': return '#1060d0'
    return '#666666'

# ----------------- extract strings from DXF -----------------
import math
doc = ezdxf.readfile(SRC_DXF)
msp = doc.modelspace()
strings_raw, on_ticks, keys = [], [], []
for L in msp.query('LINE'):
    dx = L.dxf.end.x - L.dxf.start.x
    dy = L.dxf.end.y - L.dxf.start.y
    length = math.hypot(dx, dy)
    ang = math.degrees(math.atan2(dy, dx))
    if abs(length - 0.25) < 1e-3 and abs(ang) < 1:
        on_ticks.append(L)
    elif abs(length - 1.53) < 0.02 and abs(ang - 78) < 2:
        keys.append(L)
    elif abs(ang - 90) < 1 and length > 2:
        strings_raw.append(L)

rows = []
for L in strings_raw:
    y0, y1 = sorted([L.dxf.start.y, L.dxf.end.y])
    rows.append({'x_in': L.dxf.start.x, 'y_grommet_in': y0, 'y_flat_in': y1,
                 'ticks': [], 'key_tip': None})
for i, r in enumerate(sorted(rows, key=lambda r: r['y_flat_in'] - r['y_grommet_in'])):
    r['num'] = i + 1

for T in on_ticks:
    cx = T.dxf.start.x + 0.125
    cy = T.dxf.start.y
    best = min(rows, key=lambda r: abs(r['x_in'] - cx))
    if abs(best['x_in'] - cx) < 0.15:
        best['ticks'].append(cy)
    else:
        best2 = min(rows, key=lambda r: abs(r['x_in'] + 0.319 - cx) + abs(r['y_flat_in'] + 1.497 - cy))
        best2['key_tip'] = (cx, cy)

rows.sort(key=lambda r: r['num'])
# Convert to mm, extract landmarks
for r in rows:
    r['x_mm']        = r['x_in'] * IN_TO_MM
    r['grommet_mm']  = (r['x_mm'], r['y_grommet_in'] * IN_TO_MM)
    r['flat_mm']     = (r['x_mm'], r['y_flat_in']    * IN_TO_MM)
    t = sorted(r['ticks'])
    r['natural_mm']  = (r['x_mm'], t[0] * IN_TO_MM) if len(t) >= 1 else None
    r['sharp_mm']    = (r['key_tip'][0] * IN_TO_MM, r['key_tip'][1] * IN_TO_MM) if r['key_tip'] else None

# Sort left-to-right (bass to treble)
rows_by_x = sorted(rows, key=lambda r: r['x_mm'])
bass  = rows_by_x[0]
treble= rows_by_x[-1]

print(f"bass string #{bass['num']}: x={bass['x_mm']:.1f}mm  grommet={bass['grommet_mm']}  flat={bass['flat_mm']}")
print(f"treble string #{treble['num']}: x={treble['x_mm']:.1f}mm  grommet={treble['grommet_mm']}  flat={treble['flat_mm']}")

# ----------------- derive harp-body layout in mm -----------------
# Use the image-measured column width (69 mm) and base height (243 mm), but
# place them such that they register to the DXF string coordinates.
COL_W   = 69.0          # column diameter, from image
BASE_H  = 243.0         # base height, from image
GAP_COL = 12.0          # clearance between column's inner face and bass string
NECK_THICKNESS = 100.0  # vertical thickness of the neck at the bass end (column side)
NECK_TREBLE_TH = 55.0   # neck thickness at the treble end (tapers down to the crook)
SOUNDBOX_BULGE = 95.0   # peak outward bulge of the soundbox back (mm)
FOOT_H = 45.0           # small feet block height

flat_pts    = [r['flat_mm']    for r in rows_by_x]
grommet_pts = [r['grommet_mm'] for r in rows_by_x]
flat_bass   = flat_pts[0]            # bass side (low x)
flat_treble = flat_pts[-1]           # treble side (high x)
grom_bass   = grommet_pts[0]
grom_treble = grommet_pts[-1]

# Column: to the LEFT of the bass string
col_inner_x = grom_bass[0] - GAP_COL         # column inner (string-facing) edge
col_outer_x = col_inner_x - COL_W            # column outer edge
col_top_y   = flat_bass[1] + 30.0            # top of column shaft
col_bot_y   = BASE_H                         # column sits on the base

# Base: rectangle under the harp
base_left_x  = col_outer_x - 15.0
base_right_x = grom_treble[0] + SOUNDBOX_BULGE + 40.0
base_bot_y   = 0.0
base_top_y   = BASE_H

# Neck: two smooth cubic Beziers (top and bottom edges of the neck plane).
# Bottom edge of neck = flat-point curve (where strings engage)
#   bass end:  (col_inner_x, col_top_y + 10)   — connects to column top
#   treble end: flat_treble + small overhang for the crook/console
# Neck bass end: align top/bottom at the same x (= column inner edge) so the end cap is vertical.
neck_bass_x  = col_inner_x
neck_bot_P0  = (neck_bass_x, flat_bass[1] + 10)
neck_top_P0  = (neck_bass_x, flat_bass[1] + NECK_THICKNESS)
# Treble end: just past treble flat
neck_treble_x = flat_treble[0] + 20
neck_bot_P3   = (neck_treble_x, flat_treble[1] - 5)
neck_top_P3   = (neck_treble_x, flat_treble[1] + NECK_TREBLE_TH)
# Control points so the curve passes near the middle flat points
mid_flat = flat_pts[len(flat_pts)//2]
neck_bot_P1 = (neck_bass_x + 120, flat_bass[1] - 50)
neck_bot_P2 = (mid_flat[0] + 80,  mid_flat[1] - 20)
neck_top_P1 = (neck_bass_x + 120, neck_top_P0[1] - 50)
neck_top_P2 = (mid_flat[0] + 80,  mid_flat[1] + NECK_THICKNESS - 20)

# Soundbox back (corps sonore): single cubic Bezier from top (treble-grommet area) down
# to the base (near the column side). One smooth crescent.
sb_P0 = (grom_treble[0] + 30, grom_treble[1] + 10)   # top end, near the treble grommet
sb_P3 = (col_inner_x + 30, base_top_y)               # bottom end, meets base near column
# Control points: bulge outward (to the right) at top; pull toward base at bottom
sb_P1 = (grom_treble[0] + SOUNDBOX_BULGE, (grom_treble[1] + 500) )
sb_P2 = (grom_treble[0] + SOUNDBOX_BULGE*0.55, base_top_y + 180)

# Soundboard (inner face where strings attach): straight line from grommet_bass to grommet_treble.
# (True soundboard is gently curved in reality but approximately linear.)

# Crosse: small S-curve from the bass grommet down to the base top (between column and soundbox).
crosse_P0 = grom_bass                              # bass grommet
crosse_P3 = (col_inner_x + 25, base_top_y)         # base-top just right of the column
crosse_P1 = (grom_bass[0] + 60, grom_bass[1] - 60)
crosse_P2 = (crosse_P3[0] + 20, crosse_P3[1] + 80)

# ----------------- viewBox in mm -----------------
pad = 40
x_min = col_outer_x - pad
x_max = base_right_x + pad
y_min = base_bot_y - pad
y_max = max(neck_top_P0[1], neck_top_P3[1]) + pad
Wmm = x_max - x_min
Hmm = y_max - y_min
def X(x): return x - x_min
def Y(y): return Hmm - (y - y_min)     # flip y to SVG

# ----------------- build SVG -----------------
L = []
L.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{Wmm:.2f}mm" height="{Hmm:.2f}mm" '
         f'viewBox="0 0 {Wmm:.2f} {Hmm:.2f}">')
L.append('<style>'
         '.outline{fill:none;stroke:#222;stroke-width:1.2;stroke-linejoin:round}'
         '.str{fill:none;stroke-linecap:round}'
         '.lbl{font-family:sans-serif;font-size:8px;fill:#222}'
         '.dim{font-family:sans-serif;font-size:5px;fill:#555}'
         '.grom{fill:#1f77b4}.nat{fill:#2ca02c}.flat{fill:#d62728}.sharp{fill:#9467bd}'
         '</style>')

# white background
L.append(f'<rect x="0" y="0" width="{Wmm:.2f}" height="{Hmm:.2f}" fill="#fff"/>')

# --- BASE (rectangle) ---
bx = X(base_left_x); by = Y(base_top_y)
bw = base_right_x - base_left_x; bh = BASE_H
L.append(f'<rect class="outline" x="{bx:.2f}" y="{by:.2f}" width="{bw:.2f}" height="{bh:.2f}"/>')
# small feet nubs
for fx in [base_left_x + 10, (base_left_x + base_right_x)/2 - 40, base_right_x - 60]:
    L.append(f'<rect class="outline" x="{X(fx):.2f}" y="{Y(0):.2f}" width="50" height="{FOOT_H:.2f}"/>')

# --- COLUMN (rectangle -- cylinder viewed from side) ---
cx = X(col_outer_x); cy = Y(col_top_y)
cw = COL_W; ch = col_top_y - col_bot_y
L.append(f'<rect class="outline" x="{cx:.2f}" y="{cy:.2f}" width="{cw:.2f}" height="{ch:.2f}"/>')

# --- NECK: two cubic Beziers (bottom + top) with line end caps ---
def bez(P):
    p = [(X(x), Y(y)) for (x,y) in P]
    return (f'M{p[0][0]:.2f},{p[0][1]:.2f} C{p[1][0]:.2f},{p[1][1]:.2f} '
            f'{p[2][0]:.2f},{p[2][1]:.2f} {p[3][0]:.2f},{p[3][1]:.2f}')

L.append(f'<path class="outline" d="{bez((neck_bot_P0, neck_bot_P1, neck_bot_P2, neck_bot_P3))}"/>')
L.append(f'<path class="outline" d="{bez((neck_top_P0, neck_top_P1, neck_top_P2, neck_top_P3))}"/>')
# Neck end caps
L.append(f'<line class="outline" x1="{X(neck_bot_P0[0]):.2f}" y1="{Y(neck_bot_P0[1]):.2f}" '
         f'x2="{X(neck_top_P0[0]):.2f}" y2="{Y(neck_top_P0[1]):.2f}"/>')
L.append(f'<line class="outline" x1="{X(neck_bot_P3[0]):.2f}" y1="{Y(neck_bot_P3[1]):.2f}" '
         f'x2="{X(neck_top_P3[0]):.2f}" y2="{Y(neck_top_P3[1]):.2f}"/>')

# --- SOUNDBOARD line (grommet-chord) --- dashed, the face the strings terminate on
L.append(f'<line class="outline" style="stroke-dasharray:5,3;stroke:#666" '
         f'x1="{X(grom_bass[0]):.2f}" y1="{Y(grom_bass[1]):.2f}" '
         f'x2="{X(grom_treble[0]):.2f}" y2="{Y(grom_treble[1]):.2f}"/>')

# --- SOUNDBOX BACK (corps sonore) --- single cubic Bezier
L.append(f'<path class="outline" d="{bez((sb_P0, sb_P1, sb_P2, sb_P3))}"/>')
# Short connector from soundbox-top to treble-grommet so the shape closes
L.append(f'<line class="outline" x1="{X(sb_P0[0]):.2f}" y1="{Y(sb_P0[1]):.2f}" '
         f'x2="{X(grom_treble[0]):.2f}" y2="{Y(grom_treble[1]):.2f}"/>')

# --- CROSSE (S-curve from bass grommet down to base top) ---
L.append(f'<path class="outline" d="{bez((crosse_P0, crosse_P1, crosse_P2, crosse_P3))}"/>')

# --- STRINGS (between flat and grommet) ---
# Use actual diameter as stroke-width
for r in rows_by_x:
    letter, oct_ = NOTES[r['num']-1]
    col = color_for(letter)
    dia_mm = diameter_in(r['num']) * IN_TO_MM
    fx, fy = r['flat_mm']; gx, gy = r['grommet_mm']
    L.append(f'<line class="str" x1="{X(gx):.2f}" y1="{Y(gy):.2f}" '
             f'x2="{X(fx):.2f}" y2="{Y(fy):.2f}" stroke="{col}" stroke-width="{dia_mm:.3f}"/>')

# --- LANDMARK DOTS (small) ---
DOT = 0.9
for r in rows_by_x:
    gx, gy = r['grommet_mm']; fx, fy = r['flat_mm']
    L.append(f'<circle class="grom" cx="{X(gx):.2f}" cy="{Y(gy):.2f}" r="{DOT}"/>')
    L.append(f'<circle class="flat" cx="{X(fx):.2f}" cy="{Y(fy):.2f}" r="{DOT}"/>')
    if r.get('natural_mm'):
        nx, ny = r['natural_mm']
        L.append(f'<circle class="nat" cx="{X(nx):.2f}" cy="{Y(ny):.2f}" r="{DOT}"/>')
    if r.get('sharp_mm'):
        sx, sy = r['sharp_mm']
        L.append(f'<circle class="sharp" cx="{X(sx):.2f}" cy="{Y(sy):.2f}" r="{DOT}"/>')

# --- LABELS ---
L.append(f'<text class="lbl" x="{X(col_outer_x + COL_W/2):.2f}" y="{Y(col_top_y/2):.2f}" '
         f'text-anchor="middle" writing-mode="tb">COLUMN  {COL_W:.0f} x {col_top_y - col_bot_y:.0f} mm</text>')
L.append(f'<text class="lbl" x="{X((base_left_x+base_right_x)/2):.2f}" y="{Y(base_top_y/2):.2f}" '
         f'text-anchor="middle">BASE  {base_right_x-base_left_x:.0f} x {BASE_H:.0f} mm</text>')
neck_mid = ( (neck_top_P0[0]+neck_top_P3[0])/2,
             (neck_top_P0[1]+neck_top_P3[1])/2 + 30 )
L.append(f'<text class="lbl" x="{X(neck_mid[0]):.2f}" y="{Y(neck_mid[1]):.2f}" text-anchor="middle">NECK</text>')
sb_label = ( grom_treble[0] + SOUNDBOX_BULGE * 0.6, (grom_treble[1] + base_top_y)/2 )
L.append(f'<text class="lbl" x="{X(sb_label[0]):.2f}" y="{Y(sb_label[1]):.2f}">SOUNDBOX</text>')
L.append(f'<text class="dim" x="{X(sb_label[0]):.2f}" y="{Y(sb_label[1]-18):.2f}">(corps sonore)</text>')
sb_line_mid = ( (grom_bass[0] + grom_treble[0])/2 - 30,
                (grom_bass[1] + grom_treble[1])/2 - 20 )
L.append(f'<text class="dim" x="{X(sb_line_mid[0]):.2f}" y="{Y(sb_line_mid[1]):.2f}" text-anchor="end">'
         f'soundboard (table d\'harmonie)</text>')

# --- OVERALL DIMENSIONS ---
tot_h = max(neck_top_P0[1], neck_top_P3[1]) - base_bot_y
tot_w = base_right_x - base_left_x
L.append(f'<text class="dim" x="{X(x_min+pad):.2f}" y="{Y(y_max-pad+5):.2f}">'
         f'overall: {tot_w:.0f} x {tot_h:.0f} mm  |  stringband: 710.8 mm wide x 1514.9 mm (bass) '
         f'|  strings 47 (G7 -> C1) |  column {COL_W:.0f} mm dia |  base {BASE_H:.0f} mm tall</text>')
L.append(f'<text class="dim" x="{X(x_min+pad):.2f}" y="{Y(y_max-pad-3):.2f}">'
         f'legend: strings -- C red, F blue, other gray (stroke-width = actual diameter)</text>')

L.append('</svg>')
with open(OUT_SVG, 'w') as f:
    f.write('\n'.join(L))

print(f"\nWrote {OUT_SVG}")
print(f"viewBox: {Wmm:.1f} x {Hmm:.1f} mm  "
      f"(string range x: {rows_by_x[0]['x_mm']:.1f}..{rows_by_x[-1]['x_mm']:.1f} mm)")
print(f"column:   {col_outer_x:.1f}..{col_outer_x+COL_W:.1f} mm,  y {col_bot_y:.0f}..{col_top_y:.0f} mm")
print(f"base:     {base_left_x:.1f}..{base_right_x:.1f} mm,  y {base_bot_y:.0f}..{base_top_y:.0f} mm")
print(f"overall:  {tot_w:.0f} x {tot_h:.0f} mm")
