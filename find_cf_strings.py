#!/usr/bin/env python3
"""Find the 14 C/F strings in the image by measuring string THICKNESS.

Approach:
  1. Scan several horizontal lines across the stringband.
  2. At each y, find string positions (peaks in horizontal projection) AND measure the
     ink-run thickness at that peak.
  3. Strings with systematically larger thickness = C/F.
  4. Take median thickness per string cluster -> rank top 14 = C/F.
"""
import math, json
import numpy as np
import cv2
from PIL import Image
import ezdxf

Image.MAX_IMAGE_PIXELS = None
SRC = '/home/james.clements/projects/erand/erard-big.jpg'
GEOM= '/home/james.clements/projects/erand/harp-geometry.json'
DBG = '/home/james.clements/projects/erand/cf-strings.png'

im = np.array(Image.open(SRC).rotate(180, expand=True))
H, W = im.shape
with open(GEOM) as f: g = json.load(f)
SLF = H / g['processing']['low_size'][1]

col_x_low = g['column']['right_xa_yb'][1]
col_y_bot_low = g['column']['y_bot_px']
bbox_x0_low = 134; bbox_y0_low = 70
bbox_x1_low = 688; bbox_y1_low = 1113

# Define string-scan strip: between the neck bottom curve and the soundboard diagonal,
# in a region where strings are all visible and separated. Use mid-harp.
scan_y0 = int((g['column']['y_top_px'] + 80) * SLF)
scan_y1 = int((col_y_bot_low - 120) * SLF)
scan_x0 = int((col_x_low + 10) * SLF)
scan_x1 = int(bbox_x1_low * SLF)
print(f"scan region: x=[{scan_x0}..{scan_x1}], y=[{scan_y0}..{scan_y1}]")

_, bw_full = cv2.threshold(cv2.GaussianBlur(im,(3,3),0), 0, 255,
                            cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

# --- approach: at each of several y-lines, find string peaks + thickness (run length) ---
N_SCANS = 15
y_samples = np.linspace(scan_y0 + 300, scan_y1 - 300, N_SCANS).astype(int)
print(f"scanning {len(y_samples)} horizontal lines")

# Collect (x, y, thickness) per string crossing
crossings = []
for y in y_samples:
    row = bw_full[y, scan_x0:scan_x1]
    # find runs of 1s
    # Extend so np.diff picks up edges
    padded = np.concatenate([[0], row//255, [0]])
    d = np.diff(padded)
    starts = np.where(d == 1)[0]   # transition 0->1
    ends   = np.where(d == -1)[0]  # transition 1->0
    for s, e in zip(starts, ends):
        # Accept ink runs 1..30 px wide (strings) and ignore very long runs (ornaments)
        w_ = e - s
        if 1 <= w_ <= 30:
            cx = scan_x0 + (s + e) / 2.0
            crossings.append((cx, y, w_))

crossings = np.array(crossings)
print(f"total crossings: {len(crossings)}")

# --- cluster crossings into strings by x-position (nearly-vertical strings share x) ---
# Since strings have a slight slope, cluster by rho (perp. distance) instead of raw x.
# Use the angle from my earlier analysis (~117°).
peak_angle = 117.0  # same as earlier (strings go down-left at ~27° off vertical)
theta_perp = math.radians(peak_angle + 90)
ct, st = math.cos(theta_perp), math.sin(theta_perp)
rhos = crossings[:,0]*ct + crossings[:,1]*st

# KDE: build 1D histogram
rho_min, rho_max = float(rhos.min()), float(rhos.max())
bins = np.arange(rho_min - 2, rho_max + 3, 4.0)  # 4-px wide bins
hist, _ = np.histogram(rhos, bins=bins)
hist_s = np.convolve(hist, np.ones(3)/3, mode='same')
print(f"histogram: {len(hist_s)} bins, max={hist_s.max():.0f}, mean={hist_s.mean():.1f}")

# Find local peaks with min-separation corresponding to ~60 px (smallest string spacing)
min_sep_bins = int(60 / 4.0)   # = 15 bins
peaks = []
for i in range(1, len(hist_s)-1):
    if hist_s[i] > hist_s[i-1] and hist_s[i] >= hist_s[i+1] and hist_s[i] >= 2:
        if peaks and (i - peaks[-1]) < min_sep_bins:
            if hist_s[i] > hist_s[peaks[-1]]:
                peaks[-1] = i
        else:
            peaks.append(i)
print(f"raw rho peaks: {len(peaks)}")

# Assign each crossing to nearest peak; compute median thickness + mean rho per peak
assigned = -np.ones(len(crossings), int)
peak_rhos = np.array([bins[p] + 2.0 for p in peaks])
for i, r in enumerate(rhos):
    j = int(np.argmin(np.abs(peak_rhos - r)))
    if abs(peak_rhos[j] - r) < 25:
        assigned[i] = j

# Gather thickness stats per peak
thick_stats = []
for j in range(len(peak_rhos)):
    mask = assigned == j
    if mask.sum() < 3: continue
    xs = crossings[mask, 0]; ys = crossings[mask, 1]
    ws = crossings[mask, 2]
    thick_stats.append({
        'peak_idx': j,
        'rho': float(peak_rhos[j]),
        'n_crossings': int(mask.sum()),
        'thickness_median': float(np.median(ws)),
        'thickness_mean':   float(np.mean(ws)),
        'x_mean': float(np.mean(xs)),
        'y_mean': float(np.mean(ys)),
    })
# Keep only strings with enough crossings (>=5)
thick_stats = [s for s in thick_stats if s['n_crossings'] >= 5]
# Sort by rho (= by x roughly)
thick_stats.sort(key=lambda s: s['rho'])
print(f"strings with >=5 crossings: {len(thick_stats)}")

# --- classify: 14 thickest = C/F, rest = plain ---
# Sort by thickness descending and mark the top 14.
by_thick = sorted(thick_stats, key=lambda s: -s['thickness_median'])
CF_THRESHOLD_INDEX = 14
for i, s in enumerate(by_thick):
    s['is_cf'] = (i < CF_THRESHOLD_INDEX)
print("\ntop 20 strings by median thickness:")
for i, s in enumerate(by_thick[:20]):
    tag = 'CF' if s['is_cf'] else '. '
    print(f"  {i+1:>2}  {tag}  rho={s['rho']:8.2f}  xmean={s['x_mean']:7.1f}  "
          f"thick_med={s['thickness_median']:.2f}  thick_mean={s['thickness_mean']:.2f}  "
          f"n={s['n_crossings']}")

# Visualize: strings ordered by rho
print("\nALL detected strings (ordered by rho, bass -> treble):")
for i, s in enumerate(thick_stats):
    tag = 'CF' if s['is_cf'] else '. '
    print(f"  #{i+1:>2} {tag}  rho={s['rho']:8.2f}  xmean={s['x_mean']:7.1f}  "
          f"thick_med={s['thickness_median']:4.2f}  n={s['n_crossings']}")

# ---- expected C/F pattern: position 1,4,8,11,15,18,22,25,29,32,36,39,43,46 ----
# (In a diatonic sequence GFEDCBA, C is 5th note, F is 2nd). If we order strings 1..47
# from treble to bass (#1=G7, #47=C1), C's and F's occupy:
#   C: 5, 12, 19, 26, 33, 40, 47
#   F: 2, 9, 16, 23, 30, 37, 44
# Combined and sorted: 2, 5, 9, 12, 16, 19, 23, 26, 30, 33, 37, 40, 44, 47
# If we've detected all 47 in order by rho (bass->treble in image), the C/F indices
# in 1..47 (bass=47, treble=1) -> order-by-rho position is (48 - k) for k in CF list.
CF_IMG_ORDER = [48 - k for k in sorted([5,12,19,26,33,40,47, 2,9,16,23,30,37,44])]
# That is: for string #47 (C1, bass) -> image order 1 (leftmost = bass).
# Thus expected thick indices (1-based, from bass end): 1, 4, 8, 11, 15, 18, 22, 25, 29, 32, 36, 39, 43, 46
print(f"\nExpected thick-string indices (1-based, bass-first): {sorted(CF_IMG_ORDER)}")

# Check: if we detected all 47, the top-14-thickness should match these indices.
if len(thick_stats) == 47:
    # index of CF-flagged strings in bass->treble order
    actual = [i+1 for i, s in enumerate(thick_stats) if s['is_cf']]
    print(f"Actual CF-flagged indices: {actual}")
    match_count = len(set(actual) & set(CF_IMG_ORDER))
    print(f"Matches with expected pattern: {match_count}/14")
else:
    print(f"(didn't detect all 47: got {len(thick_stats)})")

# Visualize debug
dbg = cv2.cvtColor(im, cv2.COLOR_GRAY2BGR)
for y in y_samples:
    cv2.line(dbg, (scan_x0, y), (scan_x1, y), (230,230,230), 1)
for s in thick_stats:
    col = (0,0,255) if s['is_cf'] else (120,120,120)
    cv2.circle(dbg, (int(s['x_mean']), int(s['y_mean'])), 8, col, 2)
cv2.imwrite(DBG, dbg)
print(f"\ndebug: {DBG}")
