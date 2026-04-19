#!/usr/bin/env python3
"""Harp side profile in DXF-mm coordinates, using the ACTUAL photo silhouette contour
(not hand-drawn primitives). The silhouette is transformed into DXF mm space by
matching two landmarks: column-top and column-bottom in the photo correspond to
the bass flat and bass grommet points in the DXF (approximately; see notes below).
"""
import os, math
import numpy as np
import cv2
import ezdxf

DXF_PATH = '/home/james.clements/projects/erand/erand.dxf'
SIL_PATH = '/home/james.clements/projects/erand/harp-silhouette.png'  # produced by fit_harp.py
OUT_SVG  = '/home/james.clements/projects/erand/harp-profile2.svg'
OUT_SVG_NOSTR = '/home/james.clements/projects/erand/harp-profile2-nostrings.svg'
IN_TO_MM = 25.4

# --- pull strings from DXF (same as make_svg.py) ---
doc = ezdxf.readfile(DXF_PATH); msp = doc.modelspace()
strings_raw, on_ticks = [], []
for L in msp.query('LINE'):
    dx = L.dxf.end.x - L.dxf.start.x; dy = L.dxf.end.y - L.dxf.start.y
    length = math.hypot(dx, dy); ang = math.degrees(math.atan2(dy, dx))
    if abs(length - 0.25) < 1e-3 and abs(ang) < 1: on_ticks.append(L)
    elif abs(ang - 90) < 1 and length > 2: strings_raw.append(L)
rows = []
for L in strings_raw:
    y0, y1 = sorted([L.dxf.start.y, L.dxf.end.y])
    rows.append({'x_in': L.dxf.start.x, 'yg_in': y0, 'yf_in': y1})
for i, r in enumerate(sorted(rows, key=lambda r: r['yf_in']-r['yg_in'])):
    r['num'] = i + 1
rows.sort(key=lambda r: r['x_in'])
for r in rows:
    r['x_mm'] = r['x_in'] * IN_TO_MM
    r['yg_mm'] = r['yg_in'] * IN_TO_MM
    r['yf_mm'] = r['yf_in'] * IN_TO_MM
bass = rows[0]; treble = rows[-1]

# --- notes & diameters (as before) ---
def build_notes():
    letters=['G','F','E','D','C','B','A']; out=[]; o=7
    for i in range(47):
        L=letters[i%7]; out.append((L,o))
        if L=='A': o -= 1
    return out
NOTES = build_notes()
def dia_in(n):
    t = {**{i:0.025 for i in range(1,8)}, **{i:0.028 for i in range(8,11)},
         11:0.030, **{i:0.032 for i in range(12,15)}, **{i:0.036 for i in range(15,19)},
         **{i:0.040 for i in range(19,22)}, **{i:0.045 for i in range(22,25)},
         **{i:0.050 for i in range(25,28)},
         28:0.061, 29:0.061, 30:0.066, 31:0.066, 32:0.076,
         33:0.081, 34:0.081, 35:0.086, 36:0.092, 37:0.098, 38:0.104,
         39:0.036, 40:0.040, 41:0.040, 42:0.048, 43:0.048,
         44:0.050, 45:0.057, 46:0.061, 47:0.066}
    return t.get(n, 0.04)
def col_for(let):
    return {'C':'#c00000','F':'#1060d0'}.get(let,'#666')

# --- load silhouette + outer contour ---
sil = cv2.imread(SIL_PATH, cv2.IMREAD_GRAYSCALE)
if sil is None:
    raise SystemExit(f"missing {SIL_PATH} -- run fit_harp.py first")
contours, _ = cv2.findContours(sil, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
contour = max(contours, key=cv2.contourArea)[:,0,:]  # (N,2) x,y in photo px

# --- load column detection from fit_harp.py's saved JSON ---
import json
with open('/home/james.clements/projects/erand/harp-geometry.json') as f:
    geom = json.load(f)
col_x_left  = int(geom['column']['left_xa_yb'][1])   # b from x = a*y + b (a is 0 since vertical)
col_x_right = int(geom['column']['right_xa_yb'][1])
col_y_top   = int(geom['column']['y_top_px'])
col_y_bot   = int(geom['column']['y_bot_px'])
print(f"photo column px (from fit_harp.py): x {col_x_left}..{col_x_right} "
      f"({col_x_right-col_x_left} wide)  y {col_y_top}..{col_y_bot} "
      f"({col_y_bot-col_y_top} tall)")

# --- compute similarity transform: photo-px -> DXF-mm ---
# Landmarks:
#   photo A = (col_x_right, col_y_top)    ~= bass flat point  (top of bass string)
#   photo B = (col_x_right, col_y_bot)    ~= bass grommet     (bottom of bass string)
#   dxf   A = (bass['x_mm'], bass['yf_mm'])    [flat_bass]
#   dxf   B = (bass['x_mm'], bass['yg_mm'])    [grommet_bass]
#
# We want: DXF = S * R * PHOTO + T
# Photo vector (A->B) is (0, dy_photo) with dy_photo > 0 (y-down).
# DXF vector  (A->B) is (0, dy_dxf)   with dy_dxf < 0  (y-up).
# Hence R = diag(1, -1) (y-flip), and uniform scale S = |dy_dxf| / |dy_photo|.
pA_px = np.array([col_x_right, col_y_top], float)
pB_px = np.array([col_x_right, col_y_bot], float)
dA_mm = np.array([bass['x_mm'], bass['yf_mm']], float)
dB_mm = np.array([bass['x_mm'], bass['yg_mm']], float)

vec_px = pB_px - pA_px
vec_mm = dB_mm - dA_mm
len_px = float(np.linalg.norm(vec_px))
len_mm = float(np.linalg.norm(vec_mm))
S = len_mm / len_px
print(f"scale: {S:.4f} mm/px  (column len: {len_px:.1f}px -> {len_mm:.1f}mm)")

# For simplicity assume no in-plane rotation beyond y-flip (image is essentially upright).
# Transform: DX = S*px + Tx;  DY = -S*py + Ty.   Solve with landmark A:
Tx = dA_mm[0] - S * pA_px[0]
Ty = dA_mm[1] + S * pA_px[1]
def xf(p):
    px, py = float(p[0]), float(p[1])
    return (S*px + Tx, -S*py + Ty)

# sanity check
print(f"xf(photo A) = {xf(pA_px)}  (target {tuple(dA_mm)})")
print(f"xf(photo B) = {xf(pB_px)}  (target {tuple(dB_mm)})")

# transform contour
contour_mm = np.array([xf(p) for p in contour])
# compute viewBox (mm)
xs_, ys_ = contour_mm[:,0], contour_mm[:,1]
xb0, xb1 = float(xs_.min()), float(xs_.max())
yb0, yb1 = float(ys_.min()), float(ys_.max())
# Also consider DXF string extent
xb0 = min(xb0, min(r['x_mm'] for r in rows))
xb1 = max(xb1, max(r['x_mm'] for r in rows))
yb0 = min(yb0, min(r['yg_mm'] for r in rows))
yb1 = max(yb1, max(r['yf_mm'] for r in rows))
pad = 50
vb_x0 = xb0 - pad; vb_x1 = xb1 + pad
vb_y0 = yb0 - pad; vb_y1 = yb1 + pad
Wmm = vb_x1 - vb_x0; Hmm = vb_y1 - vb_y0

def X(x): return x - vb_x0
def Y(y): return Hmm - (y - vb_y0)   # SVG y-down

# --- emit SVG ---
def build_svg(show_strings: bool) -> str:
    L = []
    L.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{Wmm:.2f}mm" height="{Hmm:.2f}mm" '
             f'viewBox="0 0 {Wmm:.2f} {Hmm:.2f}">')
    L.append('<style>'
             '.outline{fill:none;stroke:#111;stroke-width:1.4;stroke-linejoin:round;stroke-linecap:round}'
             '.str{fill:none;stroke-linecap:round}'
             '.lbl{font-family:sans-serif;font-size:8px;fill:#333}'
             '.dim{font-family:sans-serif;font-size:5px;fill:#666}'
             '.grom{fill:#1f77b4}.flat{fill:#d62728}'
             '</style>')
    L.append(f'<rect x="0" y="0" width="{Wmm:.2f}" height="{Hmm:.2f}" fill="#fff"/>')
    # Outer contour path (the actual photo silhouette, now in DXF mm)
    d = [f'M{X(contour_mm[0,0]):.2f},{Y(contour_mm[0,1]):.2f}']
    for pt in contour_mm[1:]:
        d.append(f'L{X(pt[0]):.2f},{Y(pt[1]):.2f}')
    d.append('Z')
    L.append(f'<path class="outline" d="{" ".join(d)}"/>')
    # Soundboard (dashed line between DXF bass and treble grommets)
    L.append(f'<line class="outline" style="stroke-dasharray:5,3;stroke:#888;stroke-width:0.8" '
             f'x1="{X(bass["x_mm"]):.2f}" y1="{Y(bass["yg_mm"]):.2f}" '
             f'x2="{X(treble["x_mm"]):.2f}" y2="{Y(treble["yg_mm"]):.2f}"/>')
    # Neck-line (dashed, between flat points)
    L.append(f'<line class="outline" style="stroke-dasharray:5,3;stroke:#888;stroke-width:0.8" '
             f'x1="{X(bass["x_mm"]):.2f}" y1="{Y(bass["yf_mm"]):.2f}" '
             f'x2="{X(treble["x_mm"]):.2f}" y2="{Y(treble["yf_mm"]):.2f}"/>')
    if show_strings:
        for r in rows:
            letter, _o = NOTES[r['num']-1]
            stroke_mm = dia_in(r['num']) * IN_TO_MM
            L.append(f'<line class="str" '
                     f'x1="{X(r["x_mm"]):.2f}" y1="{Y(r["yg_mm"]):.2f}" '
                     f'x2="{X(r["x_mm"]):.2f}" y2="{Y(r["yf_mm"]):.2f}" '
                     f'stroke="{col_for(letter)}" stroke-width="{stroke_mm:.3f}"/>')
    # landmarks
    for r in (bass, treble):
        L.append(f'<circle class="grom" cx="{X(r["x_mm"]):.2f}" cy="{Y(r["yg_mm"]):.2f}" r="2"/>')
        L.append(f'<circle class="flat" cx="{X(r["x_mm"]):.2f}" cy="{Y(r["yf_mm"]):.2f}" r="2"/>')
    # labels
    L.append(f'<text class="lbl" x="{X(vb_x0+pad):.2f}" y="{Y(vb_y1-pad+5):.2f}">'
             f'Erard harp profile (mm)  overall: {xb1-xb0:.0f} x {yb1-yb0:.0f}  '
             f'stringband: 47 strings, bass = {len_mm:.1f} mm active  scale: {S:.3f} mm/px</text>')
    L.append(f'<text class="dim" x="{X(vb_x0+pad):.2f}" y="{Y(vb_y1-pad-3):.2f}">'
             f'solid black = actual silhouette contour from erard-big.jpg, aligned to DXF '
             f'via bass-string landmarks; dashed = DXF neck/soundboard chords'
             f'{"; strings coloured (C red, F blue)" if show_strings else "; strings OFF"}</text>')
    L.append('</svg>')
    return '\n'.join(L)

with open(OUT_SVG, 'w') as f: f.write(build_svg(show_strings=True))
with open(OUT_SVG_NOSTR, 'w') as f: f.write(build_svg(show_strings=False))

print(f"\nWrote:")
print(f"  {OUT_SVG}         (with strings)")
print(f"  {OUT_SVG_NOSTR}   (no strings, just outlines)")
print(f"\nPhoto contour + DXF strings/landmarks registered via bass-string calibration.")
print(f"viewBox: {Wmm:.0f} x {Hmm:.0f} mm")
