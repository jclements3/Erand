#!/usr/bin/env python3
"""Minimal side profile: column as a line A->B, bass string as a line from its tuning pin.
Calibration: adjacent-bass-band string spacing = 17.9375 mm (DXF band 6, strings 36..47).
"""
import os, math, json
import numpy as np
import cv2
from PIL import Image
import ezdxf

Image.MAX_IMAGE_PIXELS = None
SRC    = '/home/james.clements/projects/erand/erard-big.jpg'
DXF    = '/home/james.clements/projects/erand/erand.dxf'
OUT    = '/home/james.clements/projects/erand/harp-profile3.svg'
OUT_PNG= '/home/james.clements/projects/erand/harp-profile3.png'

# ---------------- load full-res flipped image ----------------
im_full = np.array(Image.open(SRC).rotate(180, expand=True))
H_full, W_full = im_full.shape
print(f"full-res flipped: {W_full} x {H_full}")

# ---------------- crop to the harp region (generous) ----------------
# Prior low-res bbox (845x1200): x 134..688, y 70..1113. Scale 12.28x to full.
cx0, cx1 = int(134*12.28), int(688*12.28)
cy0, cy1 = int( 70*12.28), int(1113*12.28)
print(f"harp region (full-res): x {cx0}..{cx1}, y {cy0}..{cy1}")

# --- threshold ---
_, bw_full = cv2.threshold(cv2.GaussianBlur(im_full,(3,3),0), 0, 255,
                            cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

# ---------------- use known column position from fit_harp.py's JSON (LOW-res) ----------------
with open('/home/james.clements/projects/erand/harp-geometry.json') as f:
    geom = json.load(f)
SCALE_LOW_TO_FULL = H_full / geom['processing']['low_size'][1]   # 14740/1200
print(f"low-res->full scale factor: {SCALE_LOW_TO_FULL:.4f}")
col_x_right_low = geom['column']['right_xa_yb'][1]  # vertical line x (a=0)
col_y_top_low   = geom['column']['y_top_px']
col_y_bot_low   = geom['column']['y_bot_px']
col_Ax = int(col_x_right_low * SCALE_LOW_TO_FULL)
col_Ay = int(col_y_top_low   * SCALE_LOW_TO_FULL)
col_Bx = int(col_x_right_low * SCALE_LOW_TO_FULL)
col_By = int(col_y_bot_low   * SCALE_LOW_TO_FULL)
print(f"COLUMN line (from JSON, scaled to full):  A=({col_Ax},{col_Ay})  B=({col_Bx},{col_By})  "
      f"span_y={col_By-col_Ay} px")
col_vec = np.array([col_Bx - col_Ax, col_By - col_Ay], float)
col_angle = math.degrees(math.atan2(col_vec[1], col_vec[0]))
print(f"  column angle (from +x, y-down) = {col_angle:.2f} deg  "
      f"(deviation from 90 vertical = {col_angle - 90:+.2f} deg)")

# ---------------- detect strings: vertical projection of bw in the string band ----------------
# Work in a region to the right of the column, within the harp bbox.
# String band y range: we'll use a slice below the disc area (clean string).
sb_y0 = int(cy0 + 0.35*(cy1-cy0))
sb_y1 = int(cy0 + 0.85*(cy1-cy0))
sb_x0 = max(col_Ax, col_Bx) + 20
sb_x1 = cx1
band = bw_full[sb_y0:sb_y1, sb_x0:sb_x1]
proj = band.sum(axis=0) / 255.0
# Peaks
sm = np.convolve(proj, np.ones(5)/5, mode='same')
thr = 0.5 * float(sm.max())
peaks = []
for i in range(1, len(sm)-1):
    if sm[i] >= sm[i-1] and sm[i] >= sm[i+1] and sm[i] >= thr:
        if peaks and i - peaks[-1] < 50:
            if sm[i] > sm[peaks[-1]]:
                peaks[-1] = i
        else:
            peaks.append(i)
peaks = [p + sb_x0 for p in peaks]  # back to full-res x
print(f"detected {len(peaks)} string peaks in string-band")
# Sort
peaks.sort()

# Calibration from bass-band spacing (17.9375 mm)
if len(peaks) < 5:
    raise SystemExit("not enough string peaks")
gaps = np.diff(peaks)
# Bass band strings have the largest spacing; but we're in the bass end so all nearby gaps ~= 17.9375
median_gap = float(np.median(gaps[:15])) if len(gaps) >= 15 else float(np.median(gaps))
scale_mm_per_px = 17.9375 / median_gap
print(f"median bass-band gap: {median_gap:.1f} px  ->  scale = {scale_mm_per_px:.5f} mm/px")

# Bass string #47 = leftmost peak
bass_x = peaks[0]
print(f"bass string #47 at full-res x = {bass_x}")

# Column-to-bass (at the y of the mid column)
col_mid_y = (col_Ay + col_By) // 2
# At that y, column x is interp between A and B (they have the same x if strictly vertical)
t = (col_mid_y - col_Ay) / max(1, (col_By - col_Ay))
col_x_at_mid = col_Ax + t * (col_Bx - col_Ax)
gap_px = bass_x - col_x_at_mid
print(f"\ncolumn->bass gap (at column mid-height y={col_mid_y}):  "
      f"{gap_px:.1f} px = {gap_px*scale_mm_per_px:.1f} mm")

# ---------------- locate bass-string tuning pin ----------------
# Tuning pin is the TOPMOST circular feature on the bass string.
# Look in a narrow vertical strip around bass_x, in the UPPER portion of the neck region.
pin_search_y0 = max(cy0 - 20, 0)
pin_search_y1 = int(cy0 + 0.20*(cy1-cy0))
pin_strip_half = 30
pin_region = im_full[pin_search_y0:pin_search_y1, bass_x-pin_strip_half:bass_x+pin_strip_half]
pr_blur = cv2.GaussianBlur(pin_region, (5,5), 1.5)
circles = cv2.HoughCircles(pr_blur, cv2.HOUGH_GRADIENT, dp=1, minDist=20,
                            param1=70, param2=18, minRadius=8, maxRadius=28)
pin = None
if circles is not None:
    # Pick the TOPMOST circle (smallest y)
    cs = circles[0]
    cs = cs[cs[:,1].argsort()]  # sort by y ascending
    pin_rel = cs[0]
    pin = (bass_x - pin_strip_half + pin_rel[0], pin_search_y0 + pin_rel[1], pin_rel[2])
if pin is None:
    print("tuning pin not auto-detected; falling back to top of bass-string band")
    pin = (bass_x, cy0, 10)
print(f"bass tuning pin at full-res ({pin[0]:.1f}, {pin[1]:.1f})  r={pin[2]:.1f}")

# ---------------- build the minimal profile SVG in DXF-mm coordinates ----------------
# Align: use the bass tuning pin's photo position as the top-of-bass reference.
# The bass string in DXF goes from flat (254, 1768.9) to grommet (254, 254). In full mm range
# (including tuning-pin area above flat), the tuning pin sits a bit above the flat.
# For simplicity, map PIN -> (bass_x_mm, bass_flat_y_mm + small_offset) and use the DXF coordinates
# for everything else.
# Direction of bass string: use the column's angle as a proxy (column is parallel to the bass string
# in classical pedal harp — both vertical; any slight image rotation will show up as column_angle).
img_vertical_rot_deg = col_angle - 90.0   # photo's "vertical" rotation relative to ideal

# Pull DXF strings
doc = ezdxf.readfile(DXF); msp = doc.modelspace()
strings_raw = []
for L in msp.query('LINE'):
    dx = L.dxf.end.x - L.dxf.start.x; dy = L.dxf.end.y - L.dxf.start.y
    length = math.hypot(dx, dy); ang = math.degrees(math.atan2(dy, dx))
    if abs(ang-90) < 1 and length > 2:
        y0, y1 = sorted([L.dxf.start.y, L.dxf.end.y])
        strings_raw.append({'x_in': L.dxf.start.x, 'yg_in': y0, 'yf_in': y1})
for i, r in enumerate(sorted(strings_raw, key=lambda r: r['yf_in']-r['yg_in'])):
    r['num'] = i + 1
strings_raw.sort(key=lambda r: r['x_in'])
IN_TO_MM = 25.4
for r in strings_raw:
    r['x_mm']  = r['x_in'] * IN_TO_MM
    r['yg_mm'] = r['yg_in'] * IN_TO_MM
    r['yf_mm'] = r['yf_in'] * IN_TO_MM
bass_dxf = strings_raw[0]

# Derive the position of the column in DXF-mm by subtracting the measured gap from the bass string x.
# Note: the bass string is at DXF x = 254 mm.
col_x_mm = bass_dxf['x_mm'] - gap_px * scale_mm_per_px
# Column length in mm: full photo column span -> mm
col_len_px = math.hypot(col_Bx - col_Ax, col_By - col_Ay)
col_len_mm = col_len_px * scale_mm_per_px
print(f"\nCOLUMN in DXF-mm:  x = {col_x_mm:.1f} mm,  length = {col_len_mm:.1f} mm")

# Column A in DXF-mm: anchored so its TOP matches the bass tuning-pin level.
# Let's place the column top A at (col_x_mm, pin_y_mm) where pin_y_mm is bass flat + small.
# For a clean profile, we'll place column TOP A at y = bass_dxf['yf_mm'] + 40 mm (approximately).
# The image tells us: the tuning pin in the photo is ABOVE the neck's bottom edge. From DXF key-tip
# the tuning pin is at yf + 38 mm vertical (for the bass) -> use that.
pin_y_mm = bass_dxf['yf_mm'] + 38.0    # approximate; pin sits above the flat point
col_A = (col_x_mm, pin_y_mm)            # top of column (roughly level with neck/tuning pins)
col_B = (col_x_mm, pin_y_mm - col_len_mm)   # bottom of column (at the base top)

# Bass string A->B in DXF-mm
bass_A_mm = (bass_dxf['x_mm'], pin_y_mm)                     # tuning pin
bass_flat_mm = (bass_dxf['x_mm'], bass_dxf['yf_mm'])         # flat point (string top of active length)
bass_grom_mm = (bass_dxf['x_mm'], bass_dxf['yg_mm'])         # grommet (string bottom)

# ---------------- Emit SVG ----------------
pad = 40
x_min = min(col_A[0], col_B[0]) - pad
x_max = max(s['x_mm'] for s in strings_raw) + pad
y_min = min(col_B[1], bass_grom_mm[1]) - pad
y_max = max(col_A[1], pin_y_mm) + pad
Wmm = x_max - x_min; Hmm = y_max - y_min
def X(x): return x - x_min
def Y(y): return Hmm - (y - y_min)

lines = []
lines.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{Wmm:.2f}mm" height="{Hmm:.2f}mm" '
             f'viewBox="0 0 {Wmm:.2f} {Hmm:.2f}">')
lines.append('<style>'
             '.col{stroke:#000;stroke-width:2.5;fill:none;stroke-linecap:round}'
             '.bass{stroke:#c00;stroke-width:1.5;fill:none;stroke-linecap:round}'
             '.str{stroke:#888;stroke-width:0.7;fill:none;stroke-linecap:round}'
             '.pin{fill:#c00;stroke:none}'
             '.end{fill:#000;stroke:none}'
             '.lbl{font-family:sans-serif;font-size:12px;fill:#000}'
             '.dim{font-family:sans-serif;font-size:8px;fill:#444}'
             '</style>')
lines.append(f'<rect x="0" y="0" width="{Wmm:.2f}" height="{Hmm:.2f}" fill="#fff"/>')

# Other strings
for r in strings_raw[1:]:
    lines.append(f'<line class="str" x1="{X(r["x_mm"]):.2f}" y1="{Y(r["yg_mm"]):.2f}" '
                 f'x2="{X(r["x_mm"]):.2f}" y2="{Y(r["yf_mm"]):.2f}"/>')
# Bass string
lines.append(f'<line class="bass" x1="{X(bass_A_mm[0]):.2f}" y1="{Y(bass_A_mm[1]):.2f}" '
             f'x2="{X(bass_grom_mm[0]):.2f}" y2="{Y(bass_grom_mm[1]):.2f}"/>')
# Tuning pin marker
lines.append(f'<circle class="pin" cx="{X(bass_A_mm[0]):.2f}" cy="{Y(bass_A_mm[1]):.2f}" r="2"/>')
# Column
lines.append(f'<line class="col" x1="{X(col_A[0]):.2f}" y1="{Y(col_A[1]):.2f}" '
             f'x2="{X(col_B[0]):.2f}" y2="{Y(col_B[1]):.2f}"/>')
lines.append(f'<circle class="end" cx="{X(col_A[0]):.2f}" cy="{Y(col_A[1]):.2f}" r="2.5"/>')
lines.append(f'<circle class="end" cx="{X(col_B[0]):.2f}" cy="{Y(col_B[1]):.2f}" r="2.5"/>')
# Labels
lines.append(f'<text class="lbl" x="{X(col_A[0]-20):.2f}" y="{Y(col_A[1])-6:.2f}" text-anchor="end">'
             f'A  col_top</text>')
lines.append(f'<text class="lbl" x="{X(col_B[0]-20):.2f}" y="{Y(col_B[1])+14:.2f}" text-anchor="end">'
             f'B  col_bot</text>')
lines.append(f'<text class="lbl" x="{X(bass_A_mm[0]+8):.2f}" y="{Y(bass_A_mm[1]):.2f}">'
             f'tuning pin (bass)</text>')
# Dimensions
lines.append(f'<text class="dim" x="{X((col_A[0]+bass_A_mm[0])/2):.2f}" y="{Y(col_A[1])+5:.2f}" '
             f'text-anchor="middle">col -> bass = {gap_px*scale_mm_per_px:.1f} mm</text>')
lines.append(f'<text class="dim" x="{X(col_A[0]-40):.2f}" y="{Y((col_A[1]+col_B[1])/2):.2f}" '
             f'text-anchor="end">column {col_len_mm:.0f} mm</text>')
lines.append(f'<text class="dim" x="{X(bass_A_mm[0]+40):.2f}" y="{Y((bass_A_mm[1]+bass_grom_mm[1])/2):.2f}">'
             f'bass string 1515 mm (grommet to flat, DXF)</text>')
# Title dimensions line
lines.append(f'<text class="lbl" x="{X(x_min+pad):.2f}" y="{Y(y_max-pad/3):.2f}">'
             f'Minimal profile | scale {scale_mm_per_px:.4f} mm/px | image rotation {img_vertical_rot_deg:+.2f}° | '
             f'all 47 strings from DXF | column + bass-pin from photo</text>')
lines.append('</svg>')
with open(OUT, 'w') as f: f.write('\n'.join(lines))
print(f"\nWrote {OUT}")
print(f"viewBox: {Wmm:.0f} x {Hmm:.0f} mm")
