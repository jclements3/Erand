#!/usr/bin/env python3
"""Extract harp geometry from erard-big.jpg.

Layout (after rotating 180 into reading orientation):
  column     = leftmost vertical element
  neck       = curved top element (upper-left to upper-right)
  soundboard = curved right edge (from neck right end down to base)
  base/socle = bottom pedestal (with pedals+feet)
  strings    = diagonals from soundboard up-left to neck

Pipeline:
  1. Load + flip 180 + downsample (two resolutions: LOW for silhouette, MED for strings)
  2. Silhouette: Otsu + page-border strip + small-CC removal + morph close
           -> keep tallest-spanning connected component (= harp)
  3. Detect strings in the MED image: Canny + Hough inside a string-region mask;
         pattern-match the detected line spacings to the known mm bands for calibration.
  4. Fit primitives against the outer contour:
         column  = 2 near-vertical lines (left + right edges)
         neck    = cubic Bezier on top edge + cubic Bezier on bottom edge
         soundbd = cubic Bezier on right edge
         base    = bounding rectangle
  5. Emit SVG overlay (mm) and debug PNGs.
"""
import os, math, json
import numpy as np
import cv2
from PIL import Image
from scipy import optimize

SRC       = '/home/james.clements/projects/erand/erard-big.jpg'
PREV_LOW  = '/home/james.clements/projects/erand/harp-prep-low.png'
PREV_MED  = '/home/james.clements/projects/erand/harp-prep-med.png'
SIL       = '/home/james.clements/projects/erand/harp-silhouette.png'
DEBUG_STR = '/home/james.clements/projects/erand/harp-strings.png'
DEBUG_FIT = '/home/james.clements/projects/erand/harp-fit.png'
OUT_SVG   = '/home/james.clements/projects/erand/harp-overlay.svg'
OUT_JSON  = '/home/james.clements/projects/erand/harp-geometry.json'

IN_TO_MM = 25.4
Image.MAX_IMAGE_PIXELS = None

# ========== step 1: load, flip, make LOW + MED resolution images ==========
print("[1] load + flip 180 + downsample")
im_full = Image.open(SRC).rotate(180, expand=True)
orig_w, orig_h = im_full.size
print(f"    full: {orig_w}x{orig_h}")

def resize_to_h(im, target_h):
    s = target_h / im.height
    return im.resize((int(im.width * s), target_h), Image.LANCZOS), s

im_low, s_low = resize_to_h(im_full, 1200)   # for silhouette + primitive fits
im_med, s_med = resize_to_h(im_full, 3200)   # for string detection (denser)
print(f"    low : {im_low.size}   (scale {s_low:.5f})")
print(f"    med : {im_med.size}   (scale {s_med:.5f})")
arr_low = np.array(im_low)
arr_med = np.array(im_med)
im_low.save(PREV_LOW)
im_med.save(PREV_MED)

# ========== step 2: silhouette at LOW res ==========
print("[2] silhouette")
h, w = arr_low.shape

# (a) Otsu threshold: ink -> 255, bg -> 0
blur = cv2.GaussianBlur(arr_low, (5,5), 0)
_, bw_raw = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

# (b) Remove the page frame: it's the CC whose bounding box nearly fills the image.
num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(bw_raw, connectivity=8)
bw = bw_raw.copy()
frame_removed = []
for i in range(1, num_labels):
    bx, by = stats[i, cv2.CC_STAT_LEFT], stats[i, cv2.CC_STAT_TOP]
    bw_ , bh_ = stats[i, cv2.CC_STAT_WIDTH], stats[i, cv2.CC_STAT_HEIGHT]
    area    = stats[i, cv2.CC_STAT_AREA]
    # frame signature: bbox covers >90% of image AND area/bbox_area is low (hollow)
    if bw_ > 0.9*w and bh_ > 0.9*h and area < 0.5*bw_*bh_:
        bw[labels == i] = 0
        frame_removed.append(i)
print(f"    removed {len(frame_removed)} frame-like component(s)")

# (c) Keep components with area >= 400 (drops labels and caption text).
num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(bw, connectivity=8)
clean = np.zeros_like(bw)
kept = 0
for i in range(1, num_labels):
    if stats[i, cv2.CC_STAT_AREA] >= 400:
        clean[labels == i] = 255
        kept += 1
print(f"    kept {kept} larger components")

# (d) Morphological closing to seal gaps in the harp outline, then flood-fill interior.
kernel = np.ones((13,13), np.uint8)
closed = cv2.morphologyEx(clean, cv2.MORPH_CLOSE, kernel)
pad = cv2.copyMakeBorder(closed, 1,1,1,1, cv2.BORDER_CONSTANT, value=0)
ff = pad.copy()
ffmask = np.zeros((pad.shape[0]+2, pad.shape[1]+2), np.uint8)
cv2.floodFill(ff, ffmask, (0,0), 255)
exterior = ff[1:-1, 1:-1]
interior = cv2.bitwise_not(exterior)
sil_all  = cv2.bitwise_or(interior, clean)

# (e) Pick the tallest CC (harp is by far the tallest)
num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(sil_all, connectivity=8)
if num_labels <= 1:
    raise SystemExit("no components after processing")
# Drop any CC whose bbox still touches all 4 image edges (vestigial frame)
valid = []
for i in range(1, num_labels):
    bx, by = stats[i, cv2.CC_STAT_LEFT], stats[i, cv2.CC_STAT_TOP]
    bw_ , bh_ = stats[i, cv2.CC_STAT_WIDTH], stats[i, cv2.CC_STAT_HEIGHT]
    if bx <= 3 and by <= 3 and bx+bw_ >= w-3 and by+bh_ >= h-3:
        continue
    valid.append((i, bh_, stats[i, cv2.CC_STAT_AREA]))
if not valid:
    raise SystemExit("no valid components")
# Pick the one with the greatest HEIGHT (ties broken by area)
valid.sort(key=lambda t: (t[1], t[2]), reverse=True)
biggest = valid[0][0]
sil = (labels == biggest).astype(np.uint8) * 255
cv2.imwrite(SIL, sil)

ys, xs = np.where(sil > 0)
bb_x0, bb_x1 = int(xs.min()), int(xs.max())
bb_y0, bb_y1 = int(ys.min()), int(ys.max())
bb_w, bb_h = bb_x1 - bb_x0, bb_y1 - bb_y0
print(f"    bbox: x={bb_x0}..{bb_x1} y={bb_y0}..{bb_y1}  ({bb_w}x{bb_h} px)")

# Quick sanity: the harp should be the tallest thing in the image. If bbox height is less than
# 50% of image height we likely grabbed the wrong CC.
if bb_h < h * 0.5:
    print("    WARN: silhouette suspiciously small; check harp-silhouette.png")

# ========== step 3: string detection (on MED) + calibration ==========
print("[3] detect strings + calibrate px/mm")
scale_low_to_med = im_med.height / im_low.height

# Use the LOW silhouette to build a region-of-interest for string search on MED.
# Upscale silhouette to MED size and erode a bit so we only examine the inside.
sil_med = cv2.resize(sil, im_med.size, interpolation=cv2.INTER_NEAREST)
sil_med_eroded = cv2.erode(sil_med, np.ones((9,9), np.uint8), iterations=2)

# Run Canny on MED inside the eroded silhouette
med_gray = arr_med.copy()
# Mask pixels outside silhouette to white (so they don't produce edges)
med_masked = np.where(sil_med_eroded > 0, med_gray, 255).astype(np.uint8)
edges = cv2.Canny(med_masked, 40, 120)

# Hough: we don't know exact string angle yet; cast a wide net
linesP = cv2.HoughLinesP(edges, 1, np.pi/720,
                         threshold=70, minLineLength=120, maxLineGap=15)
if linesP is None:
    linesP = np.zeros((0,1,4), int)
linesP = linesP[:,0,:]
print(f"    Hough segments: {len(linesP)}")

def seg_angle(seg):
    x1,y1,x2,y2 = seg
    return (math.degrees(math.atan2(y2-y1, x2-x1)) + 180) % 180

# Bin into a histogram
angs = np.array([seg_angle(s) for s in linesP]) if len(linesP) else np.array([])
# Also compute lengths to weight the histogram
lens = np.array([math.hypot(s[2]-s[0], s[3]-s[1]) for s in linesP]) if len(linesP) else np.array([])

# Skip near-vertical (column & page edges) and near-horizontal (neck baseline)
# Strings should be somewhere in the middle (20..80 deg or 100..160 deg).
if len(angs):
    # weighted histogram
    hist, edges_bin = np.histogram(angs, bins=180, range=(0,180), weights=lens)
    # Suppress 0..8 and 82..98 and 172..180 (verticals and horizontals)
    suppress = np.zeros_like(hist, dtype=bool)
    for a in range(0,180):
        if a <= 8 or a >= 172 or (82 <= a <= 98):
            suppress[a] = True
    hist[suppress] = 0
    peak_bin = int(np.argmax(hist))
    peak_angle = (edges_bin[peak_bin] + edges_bin[peak_bin+1]) / 2
    print(f"    dominant (non-axis) angle: {peak_angle:.2f} deg")
    mask = np.abs(((angs - peak_angle + 90) % 180) - 90) < 4
    string_segs = linesP[mask]
    print(f"    string-like segments within 4deg: {len(string_segs)}")
else:
    peak_angle = 0
    string_segs = np.zeros((0,4), int)

# Cluster into distinct strings by perpendicular distance, using KDE-like peak detection.
if len(string_segs):
    theta_perp = math.radians(peak_angle + 90)
    ct, st = math.cos(theta_perp), math.sin(theta_perp)
    midx = (string_segs[:,0] + string_segs[:,2]) / 2
    midy = (string_segs[:,1] + string_segs[:,3]) / 2
    rho = midx * ct + midy * st
    # KDE: 1D histogram with smoothing, then find local maxima
    rmin, rmax = float(rho.min()), float(rho.max())
    nbins = int(rmax - rmin) + 2   # 1 bin per pixel
    hist, _ = np.histogram(rho, bins=nbins, range=(rmin, rmax+1))
    smooth = np.convolve(hist, np.ones(5)/5, mode='same')
    # Peaks above a minimum prominence
    peaks = []
    min_prom = max(3, 0.2 * float(smooth.max()))
    for i in range(2, len(smooth)-2):
        if smooth[i] >= smooth[i-1] and smooth[i] >= smooth[i+1] and smooth[i] >= min_prom:
            # enforce minimum separation from previous peak
            if peaks and (i - peaks[-1]) < 4:
                if smooth[i] > smooth[peaks[-1]]:
                    peaks[-1] = i
            else:
                peaks.append(i)
    string_rhos = np.array([rmin + p for p in peaks])
else:
    string_rhos = np.array([])

print(f"    distinct string rhos (KDE peaks): {len(string_rhos)}")

# Calibration: compare detected spacing progression with the known mm progression.
# We expect 47 strings across 6 bands: 13.325 x15, 14.35 x7, 15.375 x7, 16.4 x3, 17.425 x4, 17.9375 x11
# (approximate counts based on ERAND.md ranges)
BAND_SPEC = [(15, 13.325), (7, 14.35), (7, 15.375), (3, 16.4), (4, 17.425), (11, 17.9375)]
expected_spacings = []
for n, mm in BAND_SPEC:
    expected_spacings.extend([mm]*n)   # each gap's spacing
expected_spacings = expected_spacings[:-1]   # 46 gaps for 47 strings

# Calibration: use known Erard concert-harp overall height ~= 1800 mm (bbox of silhouette).
# This gives a reliable baseline; string-based refinement is attempted only if it's plausible.
ASSUMED_HARP_H_MM = 1800.0
px_per_mm_low = bb_h / ASSUMED_HARP_H_MM
px_per_mm = px_per_mm_low * scale_low_to_med
calibrated = False
peak_angle_used = peak_angle
print(f"    bbox-height calibration: harp height {ASSUMED_HARP_H_MM} mm -> {px_per_mm_low:.4f} px/mm @ LOW")
# If we found ~47 string peaks, cross-check
if 30 <= len(string_rhos) <= 70:
    detected_gaps = np.diff(string_rhos)
    small = np.sort(detected_gaps)[:max(5, len(detected_gaps)//3)]
    treble_px_med = float(np.median(small))
    implied_px_per_mm_med = treble_px_med / 13.325
    implied_px_per_mm_low = implied_px_per_mm_med / scale_low_to_med
    ratio = implied_px_per_mm_low / px_per_mm_low
    print(f"    string cross-check: treble gap {treble_px_med:.2f} px @MED "
          f"-> {implied_px_per_mm_low:.4f} px/mm @LOW  (ratio vs bbox {ratio:.3f})")
    if 0.85 <= ratio <= 1.15:
        px_per_mm_low = implied_px_per_mm_low
        px_per_mm = implied_px_per_mm_med
        calibrated = True
        print(f"    -> adopted string-based calibration")
    else:
        print(f"    -> string-based value implausible; keeping bbox-height calibration")

# Debug: draw detected strings on MED
dbg = cv2.cvtColor(arr_med, cv2.COLOR_GRAY2BGR)
for s in string_segs:
    cv2.line(dbg, (s[0],s[1]), (s[2],s[3]), (0,0,255), 1)
cv2.imwrite(DEBUG_STR, dbg)

# ========== step 4: fit primitives on LOW silhouette ==========
print("[4] fit primitives (column, neck, soundboard, base)")
contours, _ = cv2.findContours(sil, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
contour = max(contours, key=cv2.contourArea)
pts = contour[:,0,:]
print(f"    contour points: {len(pts)}")

# Column: column-ink projection in the leftmost 28% strip of the bbox.
# For a mostly-vertical column drawn with two parallel ink lines, summing ink down each column
# should show two sharp peaks at the column's left and right edges.
col_x0_strip = bb_x0
col_x1_strip = bb_x0 + int(0.32 * bb_w)
# Restrict to the MIDDLE 70% of the bbox height so we don't include the base/pedestal or the
# extreme top (capital / neck area).
col_search_y0 = int(bb_y0 + 0.10 * bb_h)
col_search_y1 = int(bb_y0 + 0.80 * bb_h)
col_strip = clean[col_search_y0:col_search_y1, col_x0_strip:col_x1_strip+1]
col_proj  = col_strip.sum(axis=0) / 255.0
# Smooth the projection lightly and pick the two most prominent peaks (= column edges).
sm = np.convolve(col_proj, np.ones(3)/3, mode='same')
# Find local maxima above a prominence threshold
thr = 0.25 * float(sm.max()) if sm.max() > 0 else 0
candidates = []
for i in range(1, len(sm)-1):
    if sm[i] >= sm[i-1] and sm[i] >= sm[i+1] and sm[i] >= thr:
        candidates.append((i, float(sm[i])))
# Pick the top-2 by height, but they must be separated by >= 8 px
candidates.sort(key=lambda t: -t[1])
picked = []
for xi, val in candidates:
    if all(abs(xi - p) >= 8 for p in picked):
        picked.append(xi)
    if len(picked) == 2: break
picked.sort()
if len(picked) != 2:
    raise SystemExit(f"column-edge detection failed: found {len(picked)} peaks")
col_x_left  = col_x0_strip + picked[0]
col_x_right = col_x0_strip + picked[1]
col_width_px = col_x_right - col_x_left
print(f"    column edges (projection): x_left={col_x_left}, x_right={col_x_right}, width={col_width_px}px")

# Column Y-range: scan each y in the bbox and check whether BOTH edges have ink near them.
col_valid_ys = []
for y in range(bb_y0, bb_y1+1):
    # consider a +/-3 px window around each edge
    left_has = clean[y, max(col_x_left-3, 0):col_x_left+4].any()
    right_has= clean[y, max(col_x_right-3,0):col_x_right+4].any()
    if left_has and right_has:
        col_valid_ys.append(y)
if not col_valid_ys:
    raise SystemExit("column y-range: no rows with both edges inked")
# Longest contiguous run of valid y's defines the column shaft
col_valid_ys = np.array(col_valid_ys)
gaps = np.where(np.diff(col_valid_ys) > 6)[0]
if len(gaps):
    # take the longest segment
    edges = np.concatenate([[0], gaps+1, [len(col_valid_ys)]])
    seg_lens = np.diff(edges)
    best = int(np.argmax(seg_lens))
    col_y0 = int(col_valid_ys[edges[best]])
    col_y1 = int(col_valid_ys[edges[best+1]-1])
else:
    col_y0, col_y1 = int(col_valid_ys[0]), int(col_valid_ys[-1])

# Expose col_left_pts / col_right_pts as fitted lines (perfectly vertical in this case)
a_l, b_l = 0.0, float(col_x_left)    # x = 0*y + col_x_left
a_r, b_r = 0.0, float(col_x_right)
col_left_pts  = np.array([[col_x_left,  y] for y in range(col_y0, col_y1+1)])
col_right_pts = np.array([[col_x_right, y] for y in range(col_y0, col_y1+1)])
col_height_px = col_y1 - col_y0
print(f"    column: y {col_y0}..{col_y1} ({col_height_px}px), width {col_width_px:.1f}px"
      f"  = {col_width_px/px_per_mm_low:.1f} x {col_height_px/px_per_mm_low:.1f} mm")

# Base: rows below the column
base_rows = []
for y in range(col_y1, bb_y1+1):
    row = sil[y]; ink = np.where(row > 0)[0]
    if len(ink) == 0: continue
    base_rows.append((y, int(ink.min()), int(ink.max())))
if base_rows:
    a = np.array(base_rows)
    base_y_top, base_y_bot = int(a[0,0]), int(a[-1,0])
    base_x_l = float(np.percentile(a[:,1], 10))
    base_x_r = float(np.percentile(a[:,2], 90))
else:
    base_y_top = base_y_bot = col_y1
    base_x_l = base_x_r = 0

# Neck: TOP edge of silhouette over the x-range right of column
neck_x0 = int(a_r * col_y0 + b_r)       # right edge of column at its top
neck_x1 = bb_x1
top_edge = []
for x in range(neck_x0, neck_x1+1):
    col = sil[:, x]; ink = np.where(col > 0)[0]
    if len(ink) == 0: continue
    top_edge.append((x, int(ink.min())))
top_edge = np.array(top_edge)

# Neck bottom edge: tricky because the interior of the neck meets strings. Take the
# topmost contiguous ink region per column within the top third of the image.
third_y = int(bb_y0 + 0.40 * bb_h)
bot_edge = []
for x in range(neck_x0, neck_x1+1):
    col = sil[:, x]; ink = np.where(col > 0)[0]
    ink = ink[ink < third_y]
    if len(ink) == 0: continue
    # find end of the TOP run (where the ink first has a gap)
    gaps = np.where(np.diff(ink) > 4)[0]
    if len(gaps):
        end = ink[gaps[0]]
    else:
        end = ink[-1]
    bot_edge.append((x, int(end)))
bot_edge = np.array(bot_edge)

# Soundboard: RIGHT edge of silhouette over y from neck-right-end down to base top
sb_y0 = int(top_edge[-1,1]) if len(top_edge) else bb_y0
sb_y1 = base_y_top
right_edge = []
for y in range(sb_y0, sb_y1+1):
    row = sil[y]; ink = np.where(row > 0)[0]
    if len(ink) == 0: continue
    right_edge.append((int(ink[-1]), y))
right_edge = np.array(right_edge)

# Cubic Bezier fit
def bezier_cubic(t, P):
    mt = 1 - t
    return ((mt**3)[:,None]*P[0] + (3*mt**2*t)[:,None]*P[1] +
            (3*mt*t**2)[:,None]*P[2] + (t**3)[:,None]*P[3])

def fit_bezier(xy, iters=4):
    if len(xy) < 4: return None
    xy = xy.astype(float)
    d = np.sqrt(np.sum(np.diff(xy, axis=0)**2, axis=1))
    u = np.concatenate([[0], np.cumsum(d)]); u = u/u[-1]
    P0, P3 = xy[0], xy[-1]
    P1 = xy[0] + (xy[-1]-xy[0])*0.33
    P2 = xy[0] + (xy[-1]-xy[0])*0.66
    for _ in range(iters):
        def resid(pa):
            P = np.array([P0, pa[:2], pa[2:], P3])
            pred = bezier_cubic(u, P)
            return (pred - xy).ravel()
        sol = optimize.least_squares(resid, [P1[0],P1[1],P2[0],P2[1]])
        P1 = sol.x[:2]; P2 = sol.x[2:]
        P = np.array([P0, P1, P2, P3])
        ts = np.linspace(0,1,500)
        curve = bezier_cubic(ts, P)
        # reparameterize
        for i, pt in enumerate(xy):
            j = int(np.argmin(np.sum((curve - pt)**2, axis=1)))
            u[i] = ts[j]
    return np.array([P0, P1, P2, P3])

neck_top_bez = fit_bezier(top_edge)
neck_bot_bez = fit_bezier(bot_edge)
sb_bez       = fit_bezier(right_edge)

# ========== step 5: emit SVG overlay (mm) + debug PNG ==========
print("[5] emit SVG + debug PNG")
W_mm = w / px_per_mm_low
H_mm = h / px_per_mm_low
def X(x): return x / px_per_mm_low
def Y(y): return y / px_per_mm_low

svg = []
svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
           f'width="{W_mm:.2f}mm" height="{H_mm:.2f}mm" viewBox="0 0 {W_mm:.2f} {H_mm:.2f}">')
svg.append(f'<image href="{os.path.basename(PREV_LOW)}" x="0" y="0" '
           f'width="{W_mm:.2f}" height="{H_mm:.2f}" opacity="0.55"/>')
svg.append('<style>.lbl{font-family:sans-serif;font-size:5px;font-weight:bold}'
           '.dim{font-family:sans-serif;font-size:3.5px;fill:#333}</style>')

# column
y0m, y1m = Y(col_y0), Y(col_y1)
xlt, xlb = X(a_l*col_y0+b_l), X(a_l*col_y1+b_l)
xrt, xrb = X(a_r*col_y0+b_r), X(a_r*col_y1+b_r)
svg.append(f'<line x1="{xlt:.2f}" y1="{y0m:.2f}" x2="{xlb:.2f}" y2="{y1m:.2f}" stroke="#c00" stroke-width="0.7"/>')
svg.append(f'<line x1="{xrt:.2f}" y1="{y0m:.2f}" x2="{xrb:.2f}" y2="{y1m:.2f}" stroke="#c00" stroke-width="0.7"/>')
col_w_mm = col_width_px / px_per_mm_low
col_h_mm = col_height_px / px_per_mm_low
svg.append(f'<text class="lbl" x="{(xlt+xrt)/2:.2f}" y="{y0m-3:.2f}" text-anchor="middle" fill="#c00">COLUMN</text>')
svg.append(f'<text class="dim" x="{(xlb+xrb)/2:.2f}" y="{(y0m+y1m)/2:.2f}" text-anchor="middle" fill="#c00">{col_w_mm:.1f} x {col_h_mm:.1f} mm</text>')

# base
if base_rows:
    bx, by = X(base_x_l), Y(base_y_top)
    bwm = (base_x_r-base_x_l)/px_per_mm_low
    bhm = (base_y_bot-base_y_top)/px_per_mm_low
    svg.append(f'<rect x="{bx:.2f}" y="{by:.2f}" width="{bwm:.2f}" height="{bhm:.2f}" stroke="#080" stroke-width="0.7" fill="none"/>')
    svg.append(f'<text class="lbl" x="{bx+bwm/2:.2f}" y="{by+bhm+6:.2f}" text-anchor="middle" fill="#080">BASE</text>')
    svg.append(f'<text class="dim" x="{bx+bwm/2:.2f}" y="{by+bhm+10:.2f}" text-anchor="middle" fill="#080">{bwm:.1f} x {bhm:.1f} mm</text>')

# Bezier helper
def bez_d(P):
    p = [(X(x), Y(y)) for (x,y) in P]
    return f'M{p[0][0]:.2f},{p[0][1]:.2f} C{p[1][0]:.2f},{p[1][1]:.2f} {p[2][0]:.2f},{p[2][1]:.2f} {p[3][0]:.2f},{p[3][1]:.2f}'

if neck_top_bez is not None:
    svg.append(f'<path d="{bez_d(neck_top_bez)}" stroke="#06c" stroke-width="0.9" fill="none"/>')
if neck_bot_bez is not None:
    svg.append(f'<path d="{bez_d(neck_bot_bez)}" stroke="#06c" stroke-width="0.9" fill="none" stroke-dasharray="2,1.5"/>')
if neck_top_bez is not None:
    cx = (X(neck_top_bez[0][0]) + X(neck_top_bez[-1][0]))/2
    svg.append(f'<text class="lbl" x="{cx:.2f}" y="{Y(min(neck_top_bez[:,1]))-3:.2f}" text-anchor="middle" fill="#06c">NECK</text>')

if sb_bez is not None:
    svg.append(f'<path d="{bez_d(sb_bez)}" stroke="#a0a" stroke-width="0.9" fill="none"/>')
    midx = X((sb_bez[0][0]+sb_bez[-1][0])/2)
    midy = Y((sb_bez[0][1]+sb_bez[-1][1])/2)
    svg.append(f'<text class="lbl" x="{midx+6:.2f}" y="{midy:.2f}" fill="#a0a">SOUNDBOARD</text>')

# bbox
svg.append(f'<rect x="{X(bb_x0):.2f}" y="{Y(bb_y0):.2f}" width="{bb_w/px_per_mm_low:.2f}" '
           f'height="{bb_h/px_per_mm_low:.2f}" stroke="#888" stroke-dasharray="3,2" fill="none" stroke-width="0.3"/>')
svg.append(f'<text class="lbl" x="{X(bb_x0)+2:.2f}" y="{Y(bb_y0)-1.5:.2f}" fill="#666">'
           f'overall: {bb_w/px_per_mm_low:.0f} x {bb_h/px_per_mm_low:.0f} mm</text>')

svg.append('</svg>')
with open(OUT_SVG, 'w') as f:
    f.write('\n'.join(svg))

# Debug PNG
dbg_fit = cv2.cvtColor(arr_low, cv2.COLOR_GRAY2BGR)
cv2.drawContours(dbg_fit, [contour], -1, (0,180,0), 1)
cv2.line(dbg_fit, (int(a_l*col_y0+b_l), col_y0), (int(a_l*col_y1+b_l), col_y1), (0,0,255), 2)
cv2.line(dbg_fit, (int(a_r*col_y0+b_r), col_y0), (int(a_r*col_y1+b_r), col_y1), (0,0,255), 2)
def draw_bez(img, P, color):
    ts = np.linspace(0,1,300)
    p = bezier_cubic(ts, P).astype(int)
    for i in range(len(p)-1):
        cv2.line(img, tuple(p[i]), tuple(p[i+1]), color, 2)
if neck_top_bez is not None: draw_bez(dbg_fit, neck_top_bez, (255,120,0))
if neck_bot_bez is not None: draw_bez(dbg_fit, neck_bot_bez, (255,180,80))
if sb_bez       is not None: draw_bez(dbg_fit, sb_bez,       (200,0,200))
if base_rows:
    cv2.rectangle(dbg_fit, (int(base_x_l), int(base_y_top)), (int(base_x_r), int(base_y_bot)), (0,170,0), 2)
cv2.imwrite(DEBUG_FIT, dbg_fit)

# JSON
geom = {
    'processing': {
        'orig_size': [orig_w, orig_h],
        'low_size':  list(im_low.size),
        'med_size':  list(im_med.size),
        'px_per_mm_low': px_per_mm_low,
        'px_per_mm_med': px_per_mm,
        'string_angle_deg': float(peak_angle_used),
        'n_string_rhos': int(len(string_rhos)),
        'calibrated_from_strings': calibrated,
    },
    'bbox_mm': {'w': bb_w/px_per_mm_low, 'h': bb_h/px_per_mm_low},
    'column': {
        'left_xa_yb':  [a_l, b_l],
        'right_xa_yb': [a_r, b_r],
        'y_top_px':    col_y0,
        'y_bot_px':    col_y1,
        'width_mm':    col_w_mm,
        'height_mm':   col_h_mm,
    },
    'base_mm': {
        'w': (base_x_r-base_x_l)/px_per_mm_low if base_rows else 0,
        'h': (base_y_bot-base_y_top)/px_per_mm_low if base_rows else 0,
    },
    'neck_top_bez_px': neck_top_bez.tolist() if neck_top_bez is not None else None,
    'neck_bot_bez_px': neck_bot_bez.tolist() if neck_bot_bez is not None else None,
    'soundboard_bez_px': sb_bez.tolist() if sb_bez is not None else None,
}
with open(OUT_JSON,'w') as f: json.dump(geom, f, indent=2)

print("\nResults:")
print(f"  harp bbox  : {bb_w/px_per_mm_low:.0f} x {bb_h/px_per_mm_low:.0f} mm")
print(f"  column     : {col_w_mm:.1f} x {col_h_mm:.1f} mm")
if base_rows:
    print(f"  base       : {(base_x_r-base_x_l)/px_per_mm_low:.1f} x {(base_y_bot-base_y_top)/px_per_mm_low:.1f} mm")
print(f"  calibration: {'strings' if calibrated else 'assumed'}  px/mm_low={px_per_mm_low:.4f}")

print("\nArtifacts:")
for p in [PREV_LOW, PREV_MED, SIL, DEBUG_STR, DEBUG_FIT, OUT_SVG, OUT_JSON]:
    print(f"  {p}  ({os.path.getsize(p)/1024:.1f} KB)")
