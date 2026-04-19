#!/usr/bin/env python3
"""Measure the distance from the column's string-facing edge to the bass (longest) string
in the photo, expressed in mm via DXF calibration.

Calibration strategy:
  - Detect the bass string in the photo (leftmost thin line just right of the column).
  - Its photo-pixel length = DXF bass active length (1514.93 mm).
  - Use this scale to convert the col->bass horizontal gap to mm.
"""
import os, math, json
import numpy as np
import cv2

PREV   = '/home/james.clements/projects/erand/harp-prep-low.png'
GEOM   = '/home/james.clements/projects/erand/harp-geometry.json'
DBG    = '/home/james.clements/projects/erand/col-to-bass-debug.png'

BASS_ACTIVE_MM = 1514.93    # DXF bass string active length (grommet -> flat)

# --- load inputs ---
img = cv2.imread(PREV, cv2.IMREAD_GRAYSCALE)
if img is None: raise SystemExit(f"missing {PREV}")
with open(GEOM) as f: geom = json.load(f)
col_x_l  = int(geom['column']['left_xa_yb'][1])
col_x_r  = int(geom['column']['right_xa_yb'][1])
col_y_t  = int(geom['column']['y_top_px'])
col_y_b  = int(geom['column']['y_bot_px'])
print(f"column px: x {col_x_l}..{col_x_r} (w={col_x_r-col_x_l})   "
      f"y {col_y_t}..{col_y_b} (h={col_y_b-col_y_t})")

# --- threshold the grayscale to get ink --
_, bw = cv2.threshold(cv2.GaussianBlur(img,(3,3),0), 0, 255,
                       cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

# --- search region: right of column, middle y range (inside the stringband) ---
MARGIN = 6
sx0 = col_x_r + MARGIN        # start scanning just past column's right edge
sx1 = col_x_r + 220           # only first ~220 px; plenty to catch the bass string
sy0 = col_y_t + 40            # avoid top-of-column ornament
sy1 = col_y_b - 80            # avoid pedestal area

# For many rows y, find the FIRST ink pixel x in [sx0, sx1].
# Discard outliers with a robust median trim.
bass_pts = []
for y in range(sy0, sy1+1, 2):
    row = bw[y, sx0:sx1]
    ink = np.where(row > 0)[0]
    if len(ink) == 0: continue
    # robustness: run-length of the first ink must be thin (string), not a thick block
    x_rel = int(ink[0])
    # Check neighbor width: is this run <= 3 px wide?
    run_end = x_rel
    for k in range(1, len(ink)):
        if ink[k] - ink[k-1] <= 1:
            run_end = int(ink[k])
        else:
            break
    width = run_end - x_rel + 1
    if width > 5: continue        # reject thick runs (not a string)
    bass_pts.append((sx0 + x_rel, y))

bass_pts = np.array(bass_pts)
print(f"bass-string candidate pixels: {len(bass_pts)}")

# Fit a line to the bass-string pixels (x = a*y + b via least squares).
# Robust: use RANSAC-like trimming.
def fit_line(pts, iters=200, thresh=1.5):
    if len(pts) < 5: return None
    best_inliers = None; best_ab = None
    rng = np.random.default_rng(0)
    for _ in range(iters):
        idx = rng.choice(len(pts), 2, replace=False)
        p1, p2 = pts[idx[0]], pts[idx[1]]
        if p2[1] == p1[1]: continue
        a = (p2[0] - p1[0]) / (p2[1] - p1[1])
        b = p1[0] - a*p1[1]
        resid = np.abs(a*pts[:,1] + b - pts[:,0])
        inliers = np.where(resid < thresh)[0]
        if best_inliers is None or len(inliers) > len(best_inliers):
            best_inliers = inliers; best_ab = (a, b)
    if best_inliers is None: return None
    # refit with all inliers
    pts_in = pts[best_inliers]
    y = pts_in[:,1].astype(float); x = pts_in[:,0].astype(float)
    A = np.vstack([y, np.ones_like(y)]).T
    sol, *_ = np.linalg.lstsq(A, x, rcond=None)
    return float(sol[0]), float(sol[1]), best_inliers

fit = fit_line(bass_pts)
if fit is None: raise SystemExit("failed to fit bass string")
a, b, inliers = fit
print(f"bass-string line: x = {a:.4f}*y + {b:.2f}   (inliers: {len(inliers)}/{len(bass_pts)})")

# Bass string endpoints = intersections with the top (flat-point neighborhood) and bottom
# (grommet neighborhood). We'll take them as the extreme inlier points.
inlier_pts = bass_pts[inliers]
bass_y_top = int(inlier_pts[:,1].min())
bass_y_bot = int(inlier_pts[:,1].max())
bass_x_top = a * bass_y_top + b
bass_x_bot = a * bass_y_bot + b
bass_len_px = math.hypot(bass_x_bot - bass_x_top, bass_y_bot - bass_y_top)
print(f"bass-string extent (px): top ({bass_x_top:.1f}, {bass_y_top})  "
      f"bot ({bass_x_bot:.1f}, {bass_y_bot})   length {bass_len_px:.2f} px")

# --- calibration from bass string length ---
scale_mm_per_px = BASS_ACTIVE_MM / bass_len_px
print(f"scale: {scale_mm_per_px:.4f} mm/px  (bass = {BASS_ACTIVE_MM} mm = {bass_len_px:.2f} px)")

# --- horizontal gap at MIDDLE y of the bass string ---
y_mid = (bass_y_top + bass_y_bot) / 2
bass_x_mid = a * y_mid + b
gap_px_mid = bass_x_mid - col_x_r
gap_mm_mid = gap_px_mid * scale_mm_per_px

# --- also at the TOP and BOTTOM of the bass string (useful reference) ---
gap_px_top = bass_x_top - col_x_r
gap_px_bot = bass_x_bot - col_x_r

print(f"\ncolumn (inner face, string-facing) x = {col_x_r} px")
print(f"bass string x at y_mid = {bass_x_mid:.1f} px")
print(f"gap at mid-height:   {gap_px_mid:>6.2f} px   =  {gap_mm_mid:>6.1f} mm")
print(f"gap at bass top:     {gap_px_top:>6.2f} px   =  {gap_px_top*scale_mm_per_px:>6.1f} mm")
print(f"gap at bass bottom:  {gap_px_bot:>6.2f} px   =  {gap_px_bot*scale_mm_per_px:>6.1f} mm")

# --- debug visualization ---
dbg = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
cv2.rectangle(dbg, (col_x_l, col_y_t), (col_x_r, col_y_b), (0,0,255), 2)
for p in bass_pts:
    cv2.circle(dbg, tuple(int(v) for v in p), 1, (255,100,0), -1)
for i in inliers:
    cv2.circle(dbg, tuple(int(v) for v in bass_pts[i]), 1, (0,200,0), -1)
# line
yv = np.arange(bass_y_top, bass_y_bot+1, 2)
xv = (a*yv + b).astype(int)
for y_, x_ in zip(yv, xv):
    if 0 <= x_ < dbg.shape[1]:
        cv2.circle(dbg, (x_, y_), 1, (0,0,255), -1)
cv2.imwrite(DBG, dbg)
print(f"\ndebug: {DBG}")
