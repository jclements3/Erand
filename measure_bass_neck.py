#!/usr/bin/env python3
"""Measure horizontal distances from the column inner face to:
  - the bass string (first string that is rendered; C1 and D1 have no discs)
  - its tuning pin (cheville)
  - flat point  (fret at top of active length)
  - natural point (upper disc centre, on first string that has discs)
  - sharp point  (lower disc centre, on first string that has discs)
Calibration uses adjacent-string spacing = 13.325 mm (bass band in DXF).
"""
import os, math
import numpy as np
import cv2
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
CROP_BOX = (2500, 800, 4200, 3200)   # (x0, y0, x1, y1) in full-res flipped
SRC = '/home/james.clements/projects/erand/erard-big.jpg'
CROP_OUT = '/home/james.clements/projects/erand/bass-neck-anno.png'

# --- load + crop at full-res ---
im_full = Image.open(SRC).rotate(180, expand=True)
crop = np.array(im_full.crop(CROP_BOX))
H, W = crop.shape
print(f"crop {W}x{H}  origin in full-res: {CROP_BOX[:2]}")

# --- binary ink ---
_, bw = cv2.threshold(cv2.GaussianBlur(crop,(3,3),0), 0, 255,
                       cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

# --- find the strings (vertical lines in the lower half where they run clean) ---
# Use a y-band well below the disc area: take y in [H*0.7, H*0.95] (string field)
y0_band = int(H * 0.72); y1_band = int(H * 0.95)
band = bw[y0_band:y1_band, :]
proj = band.sum(axis=0) / 255.0    # per-column ink count
# Peaks above a prominence threshold = string positions
sm = np.convolve(proj, np.ones(3)/3, mode='same')
thr = 0.5 * float(sm.max())
peaks = []
for i in range(1, W-1):
    if sm[i] >= sm[i-1] and sm[i] >= sm[i+1] and sm[i] >= thr:
        if peaks and i - peaks[-1] < 25:    # min-separation
            if sm[i] > sm[peaks[-1]]:
                peaks[-1] = i
        else:
            peaks.append(i)
print(f"detected {len(peaks)} raw string-peak columns in y-band {y0_band}..{y1_band}")
# Drop any peak in the first 40 px after the column (likely column ornament)
# -- also drop peaks that are too close to the next peak (half-spacing false positives)
# We'll filter these below once we know the column.
print(f"raw peaks (crop-px): {peaks[:12]} ...")

# --- column right-edge at disc height ---
# Column body takes the left portion of the crop. Scan vertical projection for the
# LEFTMOST sustained ink block.
# Column inner face: take the leftmost continuous-vertical-ink line.
# For each x in the leftmost 30% of the crop, count the fraction of y-rows where ink is present.
# The column is the LAST x position with high (>80%) coverage that hasn't been broken by a large gap.
fraction = bw[:, :int(W*0.3)].sum(axis=0) / (255.0 * H)
# The column shaft has near-100% coverage; its right edge is where coverage drops sharply.
# Find the rightmost x in the leftmost contiguous run with fraction > 0.75.
start = None
col_x_right_crop = 0
for x in range(len(fraction)):
    if fraction[x] > 0.75:
        if start is None: start = x
        col_x_right_crop = x
    else:
        if start is not None and (x - col_x_right_crop) > 10:
            break  # run ended
print(f"column inner face (vertical-coverage method): crop-x = {col_x_right_crop}  "
      f"(coverage at that x = {fraction[col_x_right_crop]:.2f})")

# --- filter peaks: require x > column_right + 30 px (drop capital ornaments),
# and drop peaks whose spacing to the next peak is less than 60% of the median spacing.
filtered = [p for p in peaks if p > col_x_right_crop + 30]
if len(filtered) >= 3:
    gaps0 = np.diff(filtered)
    med0 = float(np.median(gaps0))
    kept = [filtered[0]]
    for i, p in enumerate(filtered[1:], start=1):
        if p - kept[-1] < 0.6 * med0:
            # too close - keep the peak with bigger projection value
            if sm[p] > sm[kept[-1]]:
                kept[-1] = p
        else:
            kept.append(p)
    peaks = kept
print(f"filtered peaks ({len(peaks)}): {peaks[:12]} ...")

# --- calibration from adjacent-string spacing ---
# The first 15 strings (from treble end) have 13.325 mm spacing in the DXF; by symmetry,
# the LAST 11 strings (bass band) have 17.9375 mm spacing. Our crop shows the BASS end,
# so consecutive adjacent string peaks should be ~17.9375 mm apart.
# Use median of differences between adjacent peaks:
if len(peaks) >= 2:
    gaps = np.diff(peaks)
    median_gap_px = float(np.median(gaps))
    scale_mm_per_px = 17.9375 / median_gap_px   # bass band spacing
    print(f"median adjacent-string gap: {median_gap_px:.2f} px"
          f" -> scale {scale_mm_per_px:.4f} mm/px   (using bass-band 17.9375 mm)")
else:
    raise SystemExit("not enough string peaks to calibrate")

def px_to_mm(px): return px * scale_mm_per_px

# --- bass strings ---
# Leftmost peak = string 47 (C1, no discs). peaks[0] is the first one.
# The user said strings 47 and 46 have no sharp discs. String 45 (E1) is first with discs.
# Find the leftmost 4 strings' x positions:
for i, p in enumerate(peaks[:5]):
    gap_px = p - col_x_right_crop
    print(f"  string_from_left #{i+1}:  crop-x = {p}  "
          f"gap from column = {gap_px} px = {px_to_mm(gap_px):.1f} mm")

bass_string_x = peaks[0]     # = DXF string #47, bass
print(f"\nbass string (#47): crop-x = {bass_string_x}")

# --- tuning pins / discs ---
# Find circular features in the neck area (upper half of crop) using Hough circles.
# Restrict to: y in [0, 0.7*H]
upper = cv2.GaussianBlur(crop[:int(H*0.7), :], (5,5), 1.5)
circles = cv2.HoughCircles(upper, cv2.HOUGH_GRADIENT,
                            dp=1, minDist=20,
                            param1=80, param2=22,
                            minRadius=8, maxRadius=26)
if circles is None:
    print("no circles found")
    circles = np.zeros((1,0,3), float)
else:
    circles = circles[0]    # (N,3) x,y,r
print(f"detected {len(circles)} circles in neck/pin area")

# Classify circles: attach each to the nearest string column
# For each circle, find nearest string peak; keep if distance < 25 px
def nearest_string(x):
    if not peaks: return None, None
    idx = int(np.argmin([abs(px - x) for px in peaks]))
    return idx, peaks[idx]

# Organize circles by string
by_string = {}
for (cx, cy, r) in circles:
    si, sx = nearest_string(cx)
    if si is None: continue
    if abs(cx - sx) > 28: continue
    by_string.setdefault(si, []).append((cx, cy, r))

# Sort each string's circles by y (top-down). On a typical harp:
#   top row = tuning pin (highest y-coord in SVG terms, lowest numeric y)
#   then flat fret area
#   then natural disc
#   then sharp disc
for si in sorted(by_string.keys())[:6]:
    rows = sorted(by_string[si], key=lambda c: c[1])
    sx = peaks[si]
    print(f"\nstring_from_left #{si+1}  (crop-x={sx})  --  circles (top->bottom):")
    for j, (cx, cy, r) in enumerate(rows):
        horiz_from_col = cx - col_x_right_crop
        print(f"   circle {j+1}: crop=({cx:.1f}, {cy:.1f})  r={r:.1f}  "
              f"x-from-col = {px_to_mm(horiz_from_col):.1f} mm   "
              f"x-from-string = {px_to_mm(cx-sx):+.1f} mm")

# --- final summary table for the BASS string and the FIRST string with full action ---
# Labels we want: tuning pin (topmost), flat (top of active length; just below button row),
# natural (upper disc), sharp (lower disc)
def classify_features(circles_sorted):
    """Given circles sorted top->bottom (by y), label them."""
    out = {'tuning_pin': None, 'flat': None, 'natural': None, 'sharp': None}
    if not circles_sorted: return out
    # Topmost circle is the tuning pin (button at top of neck).
    out['tuning_pin'] = circles_sorted[0]
    if len(circles_sorted) >= 2: out['flat']    = circles_sorted[1]
    if len(circles_sorted) >= 3: out['natural'] = circles_sorted[2]
    if len(circles_sorted) >= 4: out['sharp']   = circles_sorted[3]
    return out

# find string 45 (first with full action): index 2 (0 = #47, 1 = #46, 2 = #45)
print("\n==== SUMMARY (mm, relative to column inner face) ====")
for label, si in [('bass #47', 0), ('D1 #46', 1), ('E1 #45', 2), ('F1 #44', 3)]:
    if si not in by_string:
        print(f"\n{label}: no circles detected")
        continue
    feats = classify_features(sorted(by_string[si], key=lambda c: c[1]))
    sx = peaks[si]
    print(f"\n{label} (crop-x = {sx}, mm from column = {px_to_mm(sx - col_x_right_crop):.1f}):")
    for name, c in feats.items():
        if c is None:
            print(f"  {name:<12}: -")
        else:
            cx, cy, r = c
            print(f"  {name:<12}: crop=({cx:.1f}, {cy:.1f}) r={r:.1f}   "
                  f"col->feat = {px_to_mm(cx-col_x_right_crop):.1f} mm   "
                  f"str->feat = {px_to_mm(cx-sx):+.1f} mm")

# --- visualize ---
dbg = cv2.cvtColor(crop, cv2.COLOR_GRAY2BGR)
# column right edge
cv2.line(dbg, (col_x_right_crop, 0), (col_x_right_crop, H-1), (0,0,255), 2)
for p in peaks:
    cv2.line(dbg, (p, 0), (p, H-1), (200,200,0), 1)
for (cx, cy, r) in circles:
    cv2.circle(dbg, (int(cx), int(cy)), int(r), (0,180,0), 2)
    cv2.circle(dbg, (int(cx), int(cy)), 2, (0,0,255), -1)
cv2.imwrite(CROP_OUT, dbg)
print(f"\nannotated: {CROP_OUT}")
