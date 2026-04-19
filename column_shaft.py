#!/usr/bin/env python3
"""Detect the column SHAFT (clean middle section; no capital, no pedestal ornament),
fit its two parallel near-vertical edges, and report:
  - column axis angle (deviation from true vertical)
  - column shaft width (mm)
  - horizontal distance from column's string-facing edge to the bass (first) string

Calibration: adjacent-bass-band string spacing = 17.9375 mm (DXF band 6).
"""
import os, math, json
import numpy as np
import cv2
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
SRC = '/home/james.clements/projects/erand/erard-big.jpg'
GEOM= '/home/james.clements/projects/erand/harp-geometry.json'
DBG = '/home/james.clements/projects/erand/column-shaft-debug.png'

# --- load flipped image at full res ---
im = np.array(Image.open(SRC).rotate(180, expand=True))
H, W = im.shape
print(f"full-res: {W}x{H}")

# --- use fit_harp.py's low-res column y-range to locate the shaft, but tighten to middle 60% ---
with open(GEOM) as f: g = json.load(f)
LOW_H = g['processing']['low_size'][1]
S_LOW_FULL = H / LOW_H                     # ~12.28
col_x_low  = g['column']['right_xa_yb'][1] # col vertical line x (a=0)
cy0_low    = g['column']['y_top_px']       # top of column
cy1_low    = g['column']['y_bot_px']       # bottom of column
print(f"low-res column: x={col_x_low} (right edge), y={cy0_low}..{cy1_low}")

# Full-res column y-range; shrink to middle 60% to skip capital/pedestal ornaments
y0 = int((cy0_low + 0.20*(cy1_low-cy0_low)) * S_LOW_FULL)
y1 = int((cy0_low + 0.80*(cy1_low-cy0_low)) * S_LOW_FULL)
# Full-res x-range: a window around the column's position (leftmost 25% of bbox)
bb = int(col_x_low * S_LOW_FULL)
x0 = max(bb - int(40*S_LOW_FULL), 0)       # ~40 LOW-px left of column
x1 = min(bb + int(40*S_LOW_FULL), W)       # ~40 LOW-px right
shaft = im[y0:y1, x0:x1]
print(f"shaft crop: x=[{x0}..{x1}], y=[{y0}..{y1}] -> {shaft.shape[1]}x{shaft.shape[0]}")

# --- binarize and find column edges via Hough on near-vertical lines ---
_, bw = cv2.threshold(cv2.GaussianBlur(shaft,(3,3),0), 0, 255,
                       cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
edges = cv2.Canny(bw, 50, 150)
# Require long lines: at least 40% of crop height
min_len = max(100, int(0.06 * shaft.shape[0]))
linesP = cv2.HoughLinesP(edges, 1, np.pi/720,
                          threshold=80, minLineLength=min_len, maxLineGap=60)
if linesP is None:
    raise SystemExit("no Hough segments in shaft crop")
# Near-vertical only (within 2 deg)
vert = []
for x1_, y1_, x2_, y2_ in linesP[:,0,:]:
    ang = math.degrees(math.atan2(y2_-y1_, x2_-x1_))
    ang = (ang + 180) % 180
    if abs(ang - 90) < 3:
        vert.append((x1_, y1_, x2_, y2_, ang))
print(f"near-vertical Hough segments: {len(vert)}")

# Cluster by x (center x of each segment).
centers = np.array([( (v[0]+v[2])/2 ) for v in vert])
# Sort and group
order = np.argsort(centers)
cxs = centers[order]
clusters = []
cur = [cxs[0]]; cur_segs = [vert[order[0]]]
for i in range(1, len(cxs)):
    if cxs[i] - cur[-1] < 15:
        cur.append(cxs[i]); cur_segs.append(vert[order[i]])
    else:
        clusters.append((np.mean(cur), cur_segs))
        cur = [cxs[i]]; cur_segs = [vert[order[i]]]
clusters.append((np.mean(cur), cur_segs))
print(f"{len(clusters)} x-clusters of vertical segments:")
for cx, segs in clusters:
    total_len = sum(math.hypot(s[2]-s[0], s[3]-s[1]) for s in segs)
    print(f"  x_center={cx:.1f}  n={len(segs)}  total_len={total_len:.0f}")

# We want the TWO most prominent clusters (= column's left and right edges).
# Score = total length; require separation of > column-expected-width minus some.
clusters.sort(key=lambda c: -sum(math.hypot(s[2]-s[0], s[3]-s[1]) for s in c[1]))
top2 = [clusters[0]]
for c in clusters[1:]:
    if all(abs(c[0] - other[0]) > 15 for other in top2):
        top2.append(c)
    if len(top2) == 2: break
if len(top2) != 2:
    raise SystemExit("couldn't find two column edges")
top2.sort(key=lambda c: c[0])   # left first, right second
col_left_cluster, col_right_cluster = top2

# Fit a line to each cluster's segments: combine all endpoint samples, fit x = a*y + b
def fit_line(segs):
    xs, ys = [], []
    for s in segs:
        xs += [s[0], s[2]]; ys += [s[1], s[3]]
    xs = np.array(xs, float); ys = np.array(ys, float)
    A = np.vstack([ys, np.ones_like(ys)]).T
    sol, *_ = np.linalg.lstsq(A, xs, rcond=None)
    a, b = float(sol[0]), float(sol[1])
    return a, b, xs, ys

a_L, b_L, _, _ = fit_line(col_left_cluster[1])
a_R, b_R, _, _ = fit_line(col_right_cluster[1])
print(f"\nCOLUMN shaft fit (in shaft-crop coords):")
print(f"  left  edge:  x = {a_L:+.5f}*y + {b_L:.2f}   (angle from vertical = {math.degrees(math.atan(a_L)):+.3f} deg)")
print(f"  right edge:  x = {a_R:+.5f}*y + {b_R:.2f}   (angle from vertical = {math.degrees(math.atan(a_R)):+.3f} deg)")

# Convert to full-res coordinates: x_full = x_crop + x0, y_full = y_crop + y0
# For the line x = a*y + b (in crop coords), in full coords:
#   x_full = a*(y_full - y0) + b + x0 = a*y_full + (b - a*y0 + x0)
a_L_full, b_L_full = a_L, b_L - a_L*y0 + x0
a_R_full, b_R_full = a_R, b_R - a_R*y0 + x0

# Column axis (midline) in full-res:
a_axis = (a_L_full + a_R_full) / 2
b_axis = (b_L_full + b_R_full) / 2
axis_angle_from_vertical = math.degrees(math.atan(a_axis))   # deviation from true vertical
print(f"\nCOLUMN AXIS (midline) in full-res:")
print(f"  x = {a_axis:+.6f}*y + {b_axis:.2f}")
print(f"  angle from true vertical = {axis_angle_from_vertical:+.3f} deg")

# ---- calibration: find bass-band string spacing to set mm/px ----
# String-band y region: middle of the low-res column range, safely below the neck.
# Use a horizontal slice in full-res.
str_y0 = int((cy0_low + 0.40*(cy1_low-cy0_low)) * S_LOW_FULL)
str_y1 = int((cy0_low + 0.80*(cy1_low-cy0_low)) * S_LOW_FULL)
# x-range: from just right of column_right_edge to end of harp bbox
col_x_right_at_mid_full = a_R_full * ((str_y0+str_y1)/2) + b_R_full
sbx0 = int(col_x_right_at_mid_full + 10*S_LOW_FULL)   # 10 LOW-px right of column
sbx1 = int(g['bbox_mm']['w'] * 0 + col_x_right_at_mid_full + 600*S_LOW_FULL)
sbx1 = min(sbx1, W-1)
_, bw_full = cv2.threshold(cv2.GaussianBlur(im,(3,3),0), 0, 255,
                            cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
band = bw_full[str_y0:str_y1, sbx0:sbx1]
proj = band.sum(axis=0) / 255.0
sm = np.convolve(proj, np.ones(5)/5, mode='same')
thr = 0.5*float(sm.max()); peaks = []
for i in range(1, len(sm)-1):
    if sm[i] >= sm[i-1] and sm[i] >= sm[i+1] and sm[i] >= thr:
        if peaks and i - peaks[-1] < 50:
            if sm[i] > sm[peaks[-1]]: peaks[-1] = i
        else: peaks.append(i)
peaks = [p + sbx0 for p in peaks]
peaks.sort()
gaps = np.diff(peaks)
med_gap = float(np.median(gaps[:15])) if len(gaps) >= 15 else float(np.median(gaps))
mm_per_px = 17.9375 / med_gap
print(f"\nCALIBRATION:")
print(f"  {len(peaks)} string peaks, median gap {med_gap:.1f} px (full-res)")
print(f"  scale = 17.9375 mm / {med_gap:.1f} px = {mm_per_px:.5f} mm/px (full-res)")

# ---- distance from column's string-facing edge to the FIRST (bass) string ----
# Bass string = leftmost peak in the stringband region.
bass_x_full = peaks[0]
print(f"\nbass string #47 full-res x = {bass_x_full}")
# Column's right (string-facing) edge at the same y as the string midpoint
str_mid_y = (str_y0 + str_y1) // 2
col_rx_at_str = a_R_full * str_mid_y + b_R_full
gap_px = bass_x_full - col_rx_at_str
print(f"  at y={str_mid_y}: column right edge x = {col_rx_at_str:.2f}  ->  gap = {gap_px:.1f} px "
      f"= {gap_px*mm_per_px:.2f} mm")

# Also report the gap at the TOP and BOTTOM of the shaft (to see if column tilts away/toward string)
y_top = y0; y_bot = y1
gap_top = bass_x_full - (a_R_full * y_top + b_R_full)
gap_bot = bass_x_full - (a_R_full * y_bot + b_R_full)
print(f"  at y={y_top} (shaft top):    gap = {gap_top:.1f} px = {gap_top*mm_per_px:.2f} mm")
print(f"  at y={y_bot} (shaft bottom): gap = {gap_bot:.1f} px = {gap_bot*mm_per_px:.2f} mm")

# Column width
col_w_px = abs((a_R_full*str_mid_y + b_R_full) - (a_L_full*str_mid_y + b_L_full))
col_w_mm = col_w_px * mm_per_px
print(f"\nCOLUMN SHAFT:")
print(f"  width at mid-y = {col_w_px:.1f} px = {col_w_mm:.2f} mm")
print(f"  axis angle from vertical = {axis_angle_from_vertical:+.3f} deg")

# ---- debug visualization: shaft crop with fitted lines ----
dbg = cv2.cvtColor(shaft, cv2.COLOR_GRAY2BGR)
for cluster in (col_left_cluster, col_right_cluster):
    for s in cluster[1]:
        cv2.line(dbg, (s[0], s[1]), (s[2], s[3]), (0, 180, 0), 1)
# Draw fitted lines
h_s = shaft.shape[0]
for y_ in range(0, h_s, 8):
    xL = int(a_L*y_ + b_L); xR = int(a_R*y_ + b_R)
    if 0 <= xL < shaft.shape[1]: cv2.circle(dbg, (xL, y_), 1, (0,0,255), -1)
    if 0 <= xR < shaft.shape[1]: cv2.circle(dbg, (xR, y_), 1, (0,0,255), -1)
cv2.imwrite(DBG, dbg)
print(f"\ndebug saved: {DBG}")

# ---- summary ----
print("\n========== ANSWER ==========")
print(f"Column angle vs vertical:         {axis_angle_from_vertical:+.2f} deg")
print(f"Column shaft width:               {col_w_mm:.1f} mm")
print(f"Column -> bass string gap (mid):  {gap_px*mm_per_px:.1f} mm")
print(f"Column -> bass string gap (top):  {gap_top*mm_per_px:.1f} mm")
print(f"Column -> bass string gap (bot):  {gap_bot*mm_per_px:.1f} mm")
