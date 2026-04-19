#!/usr/bin/env python3
"""Measure the base block and the total column height using the known 0.1616 mm/px calibration.

Reads the full-res flipped image; manually identifies key corners by scanning the
silhouette / binary ink around the known base region. Outputs mm dimensions.
"""
import math, json
import numpy as np
import cv2
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
SRC = '/home/james.clements/projects/erand/erard-big.jpg'
GEOM = '/home/james.clements/projects/erand/harp-geometry.json'

im = np.array(Image.open(SRC).rotate(180, expand=True))
H, W = im.shape
with open(GEOM) as f: g = json.load(f)
SCALE_LF = H / g['processing']['low_size'][1]       # ~12.28

MM_PER_PX = 0.16160   # from column_shaft.py: 17.9375 mm / 111 px (full-res)

# Column info (full-res)
col_x = g['column']['right_xa_yb'][1] * SCALE_LF
col_y_top_low = g['column']['y_top_px']
col_y_bot_low = g['column']['y_bot_px']
col_y_top = col_y_top_low * SCALE_LF
col_y_bot = col_y_bot_low * SCALE_LF

# Silhouette bbox (full-res)
bbox_w_low = 554                   # from earlier output
bbox_h_low = 1043
bbox_x0 = 134 * SCALE_LF
bbox_y0 = 70  * SCALE_LF
bbox_x1 = bbox_x0 + bbox_w_low * SCALE_LF
bbox_y1 = bbox_y0 + bbox_h_low * SCALE_LF

# --- binarize ---
_, bw = cv2.threshold(cv2.GaussianBlur(im,(3,3),0), 0, 255,
                       cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

# --- column bottom: find where the column shaft ends (ink pattern changes from parallel
# vertical lines to decorative forms below). Approach: scan downward from col_y_top, find the
# last row where both column edges (at fitted line positions) have ink.
# For simplicity we take the column y-range from fit_harp.py, which is the full shaft y-span.
# Total column shaft length in mm:
col_len_mm = (col_y_bot - col_y_top) * MM_PER_PX
print(f"Column shaft: y px {col_y_top:.0f}..{col_y_bot:.0f}   length = {col_len_mm:.1f} mm")

# --- find the FIRST y below col_y_bot where the left-edge of the silhouette drastically
# widens (=base starts). Use outer contour: leftmost ink pixel per row.
ys, xs = np.where(bw > 0)
# Limit to harp region
inside = (xs >= bbox_x0) & (xs <= bbox_x1) & (ys >= bbox_y0) & (ys <= bbox_y1)
xs, ys = xs[inside], ys[inside]
# For each y row, compute leftmost and rightmost ink x.
from collections import defaultdict
row_stats = {}
for y, x in zip(ys, xs):
    s = row_stats.get(y)
    if s is None: row_stats[y] = [int(x), int(x)]
    else:
        if x < s[0]: s[0] = int(x)
        if x > s[1]: s[1] = int(x)
# Arrays
yy = np.array(sorted(row_stats.keys()))
left = np.array([row_stats[y][0] for y in yy])
right = np.array([row_stats[y][1] for y in yy])

# At the column's mid y, leftmost ink ≈ column left edge. Well below, the silhouette widens
# into the base. Find where the left edge shifts leftward by, say, more than 30% of the
# column shaft width (column width ~40 LOW-px = 490 full-px).
col_half_width_full = 245  # shaft fit gave 245 full-res px between edges
# The "leftmost" should go significantly left of (col_x - col_half_width_full/2)
ref_left = col_x - col_half_width_full/2 - 20  # "still part of column"
# Find first y > col_y_bot where left < ref_left - 50
base_top_y = None
for i, y in enumerate(yy):
    if y > col_y_bot and left[i] < ref_left - 50:
        base_top_y = int(y); break
if base_top_y is None:
    print("couldn't detect base-top transition")
    base_top_y = int(col_y_bot + 50 * SCALE_LF)   # fallback

# Base bottom = bbox_y1 (silhouette bottom)
base_bot_y = int(yy[-1])

print(f"Base top (transition y) = {base_top_y}   base bottom = {base_bot_y}")
base_h_px = base_bot_y - base_top_y
base_h_mm = base_h_px * MM_PER_PX
print(f"Base (full) height in pixels = {base_h_px}  =>  {base_h_mm:.1f} mm")

# Base width: maximum (right - left) over y rows in the base region.
base_rows = (yy >= base_top_y) & (yy <= base_bot_y)
if base_rows.any():
    widths = (right - left)[base_rows]
    base_w_px = int(np.max(widths))
    # also the 85th-percentile excludes griffe spikes
    base_w_85 = int(np.percentile(widths, 85))
else:
    base_w_px = 0; base_w_85 = 0
base_w_mm    = base_w_px * MM_PER_PX
base_w_85_mm = base_w_85 * MM_PER_PX
print(f"Base max width = {base_w_px} px = {base_w_mm:.1f} mm   "
      f"(85th pctile = {base_w_85} px = {base_w_85_mm:.1f} mm)")

# --- oblique-view side-face visible width (depth projection) ---
# The base block's left side is visible as a narrow strip between the column's vertical
# position and the base's outer left edge. At the base mid-height, measure:
#   - col_x (the column's vertical)
#   - leftmost ink (outermost extent of visible side face)
# The difference ≈ visible-depth (in projection units).
base_mid_y = (base_top_y + base_bot_y) // 2
idx = int(np.searchsorted(yy, base_mid_y))
if idx < len(yy):
    side_visible_px = col_x - left[idx]
    side_visible_mm = side_visible_px * MM_PER_PX
    print(f"Visible left-side face width (projected): {side_visible_px:.0f} px = {side_visible_mm:.1f} mm")

# --- Summary ---
print("\n========== SUMMARY ==========")
print(f"Calibration: {MM_PER_PX:.5f} mm/px (full-res)")
print(f"Column shaft length:            {col_len_mm:.0f} mm")
print(f"Base (socle + feet) height:     {base_h_mm:.0f} mm")
print(f"Base width (full, incl. feet):  {base_w_mm:.0f} mm")
print(f"Base width (main block, 85%):   {base_w_85_mm:.0f} mm")
print(f"Base side-face visible width:   {side_visible_mm:.0f} mm  (projection; true depth larger)")
print(f"Total harp (column + base):     {col_len_mm + base_h_mm:.0f} mm")
