#!/usr/bin/env python3
"""Register the photo to the DXF by matching the 47 string lines.

Pipeline:
  1. Detect the string lines in the photo (probabilistic Hough).
  2. Cluster line segments into exactly 47 string identities (by perpendicular-distance).
  3. For each detected string: fit a line, get TOP (neck-side) and BOTTOM (soundboard-side)
     endpoints that actually sit on inked pixels.
  4. Match detected strings to DXF strings by x-order (leftmost in image = highest x in DXF?).
     We test both orderings and pick the one with the smaller homography residual.
  5. Solve a homography image_px -> dxf_mm using all 94 endpoint correspondences (findHomography
     with RANSAC).
  6. Transform the column-shaft edge points to DXF-mm and report the column + base geometry.
"""
import math, json
import numpy as np
import cv2
from PIL import Image
import ezdxf

Image.MAX_IMAGE_PIXELS = None

SRC      = '/home/james.clements/projects/erand/erard-big.jpg'
DXF_PATH = '/home/james.clements/projects/erand/erand.dxf'
GEOM     = '/home/james.clements/projects/erand/harp-geometry.json'
DBG      = '/home/james.clements/projects/erand/string-registration.png'
OUT_JSON = '/home/james.clements/projects/erand/homography.json'

IN_TO_MM = 25.4

# ----------------- load image + low-res column info -----------------
im = np.array(Image.open(SRC).rotate(180, expand=True))
H, W = im.shape
with open(GEOM) as f: g = json.load(f)
SLF = H / g['processing']['low_size'][1]    # low->full scale ~12.28

col_x_low  = g['column']['right_xa_yb'][1]
col_y_top_low = g['column']['y_top_px']
col_y_bot_low = g['column']['y_bot_px']
bbox_x0_low = 134; bbox_y0_low = 70
bbox_x1_low = 688; bbox_y1_low = 1113

# Full-res bbox (stringband region within the harp silhouette)
# We'll search strings in a rectangle from just right of the column to the harp's right edge,
# vertically from below-neck to above-soundboard-end.
reg_x0 = int((col_x_low + 8) * SLF)
reg_x1 = int(bbox_x1_low * SLF)
reg_y0 = int((col_y_top_low + 15) * SLF)   # below the neck's topmost tuning pins
reg_y1 = int((col_y_bot_low - 20) * SLF)   # above the base/crosse
print(f"string search region (full-res): x=[{reg_x0}..{reg_x1}], y=[{reg_y0}..{reg_y1}]")

# ----------------- Hough lines -----------------
roi = im[reg_y0:reg_y1, reg_x0:reg_x1]
_, bw = cv2.threshold(cv2.GaussianBlur(roi,(3,3),0), 0, 255,
                       cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
edges = cv2.Canny(bw, 40, 120)
minL = int(0.08 * roi.shape[0])      # strings often get broken by disc mechanisms
linesP = cv2.HoughLinesP(edges, 1, np.pi/1440,
                          threshold=50, minLineLength=minL, maxLineGap=80)
if linesP is None:
    raise SystemExit("no Hough lines in string region")
segs = linesP[:,0,:]
# Convert to full-res coords
segs_full = np.array([[s[0]+reg_x0, s[1]+reg_y0, s[2]+reg_x0, s[3]+reg_y0] for s in segs])
print(f"Hough segments: {len(segs_full)}")

# Filter by angle: strings are at ~120° (down-left)
def ang(seg):
    a = math.degrees(math.atan2(seg[3]-seg[1], seg[2]-seg[0]))
    return (a + 180) % 180
angs = np.array([ang(s) for s in segs_full])
lens = np.array([math.hypot(s[2]-s[0], s[3]-s[1]) for s in segs_full])

# Weighted angle histogram
hist = np.zeros(180);
for a, L in zip(angs, lens):
    hist[int(a) % 180] += L
sm = np.convolve(hist, np.ones(3)/3, mode='same')
# Suppress axes
for i in list(range(0,8)) + list(range(82,98)) + list(range(172,180)):
    sm[i] = 0
peak_angle = int(np.argmax(sm))
print(f"dominant string angle: {peak_angle} deg")

# Keep lines within 8 deg of the peak (strings have slightly varying angles across the band)
ang_ok = np.abs(((angs - peak_angle + 90) % 180) - 90) < 8
ss = segs_full[ang_ok]
print(f"segments within 4° of peak: {len(ss)}")

# ----------------- cluster into 47 strings -----------------
# Use perpendicular distance (rho) in the direction normal to the string angle.
theta_perp = math.radians(peak_angle + 90)
ct, st = math.cos(theta_perp), math.sin(theta_perp)
mid = np.array([[(s[0]+s[2])/2, (s[1]+s[3])/2] for s in ss])
rhos = mid[:,0]*ct + mid[:,1]*st
ll = np.array([math.hypot(s[2]-s[0], s[3]-s[1]) for s in ss])

# KDE: 1D length-weighted histogram over rho, then peak-pick 47 local maxima.
rho_min, rho_max = float(rhos.min()), float(rhos.max())
# Bin resolution: 1 px
nbins = int(rho_max - rho_min) + 2
rbins = np.linspace(rho_min, rho_max + 1, nbins + 1)
# weighted histogram (weight by segment length)
kde, _ = np.histogram(rhos, bins=rbins, weights=ll)
kde = np.convolve(kde, np.ones(7)/7, mode='same')

# Find 47 peaks: choose a min-separation based on expected spacing.
# Expected spacing: treble ~13.325 mm, bass ~17.9375 mm. Scale ~0.16 mm/px so spacing 83..113 px.
min_sep = int(0.7 * 83)   # 58 px minimum separation
peaks = []
for i in range(1, len(kde)-1):
    if kde[i] > kde[i-1] and kde[i] >= kde[i+1]:
        if peaks and (i - peaks[-1]) < min_sep:
            if kde[i] > kde[peaks[-1]]:
                peaks[-1] = i
        else:
            peaks.append(i)
print(f"raw peaks: {len(peaks)}")
# Keep the TOP 47 by weight (value of kde at that bin)
peaks.sort(key=lambda i: -kde[i])
peaks_kept = sorted(peaks[:47])
print(f"kept top 47 rho peaks: count={len(peaks_kept)}")
rho_centres = [float(rbins[i] + 0.5) for i in peaks_kept]

# ----------------- for each rho peak, gather segments and fit a line -----------------
# Assign each segment to its nearest rho peak (if within the min-spacing/2)
strings = [{'rho': rc, 'segs': []} for rc in rho_centres]
gap = 0.6 * (peaks_kept[1] - peaks_kept[0]) if len(peaks_kept) >= 2 else 40
for i, (s, r) in enumerate(zip(ss, rhos)):
    # find nearest rho
    idx = int(np.argmin([abs(r - rc) for rc in rho_centres]))
    if abs(r - rho_centres[idx]) < gap:
        strings[idx]['segs'].append(tuple(s))

# Fit a line to each string's segments: collect endpoints, least-squares ax+by+c=0 via SVD
def fit_line(segs):
    pts = []
    for s in segs:
        pts.append([s[0], s[1]]); pts.append([s[2], s[3]])
    if len(pts) < 4: return None
    pts = np.array(pts, float)
    cx, cy = pts.mean(axis=0)
    M = pts - [cx, cy]
    _, _, VT = np.linalg.svd(M, full_matrices=False)
    d = VT[0]                       # direction vector (unit)
    n = np.array([-d[1], d[0]])     # normal
    return (cx, cy), d, n, pts

# For each string, find TOP and BOTTOM endpoints by projecting the fitted-pts onto direction d
top_pts = []  # (image_x, image_y, string_index)
bot_pts = []
string_records = []
for i, s in enumerate(strings):
    fit = fit_line(s['segs'])
    if fit is None:
        string_records.append(None); continue
    (cx, cy), d, n, pts = fit
    proj = (pts - [cx, cy]) @ d
    t_min, t_max = proj.min(), proj.max()
    P_top = np.array([cx, cy]) + t_min * d
    P_bot = np.array([cx, cy]) + t_max * d
    # Make sure P_top has SMALLER y (higher in image = neck side)
    if P_top[1] > P_bot[1]:
        P_top, P_bot = P_bot, P_top
    top_pts.append((P_top[0], P_top[1], i))
    bot_pts.append((P_bot[0], P_bot[1], i))
    string_records.append({'center': (cx, cy), 'dir': d, 'top': P_top, 'bot': P_bot})
print(f"strings with fits: {sum(1 for r in string_records if r is not None)}")

# ----------------- pull DXF string coordinates -----------------
doc = ezdxf.readfile(DXF_PATH); msp = doc.modelspace()
dxf_rows = []
for L in msp.query('LINE'):
    dy = L.dxf.end.y - L.dxf.start.y
    dx = L.dxf.end.x - L.dxf.start.x
    ang2 = math.degrees(math.atan2(dy, dx))
    if abs(ang2 - 90) < 1 and math.hypot(dx, dy) > 2:
        y0, y1 = sorted([L.dxf.start.y, L.dxf.end.y])
        dxf_rows.append({'x_in': L.dxf.start.x, 'yg_in': y0, 'yf_in': y1})
for i, r in enumerate(sorted(dxf_rows, key=lambda r: r['yf_in']-r['yg_in'])):
    r['num'] = i + 1
dxf_rows.sort(key=lambda r: r['x_in'])
for r in dxf_rows:
    r['x_mm'] = r['x_in'] * IN_TO_MM
    r['yg_mm'] = r['yg_in'] * IN_TO_MM
    r['yf_mm'] = r['yf_in'] * IN_TO_MM
print(f"DXF strings: {len(dxf_rows)}")
assert len(dxf_rows) == 47

# ----------------- match detected strings to DXF C/F strings -----------------
# Convention: C and F strings are drawn heavier than the rest (7 C + 7 F = 14).
# String numbering (DXF): #1=G7 ... #47=C1. Descending diatonically, so:
#   C's: 5, 12, 19, 26, 33, 40, 47
#   F's: 2, 9, 16, 23, 30, 37, 44
CF_NUMS = sorted([5,12,19,26,33,40,47, 2,9,16,23,30,37,44])
dxf_cf = [r for r in dxf_rows if r['num'] in CF_NUMS]
dxf_cf.sort(key=lambda r: r['x_mm'])   # order by x ascending
print(f"DXF C/F strings (14): "
      + ", ".join(f"#{r['num']}({r['x_mm']:.0f}mm)" for r in dxf_cf))

det_ordered = [sr for sr in string_records if sr is not None]
det_ordered.sort(key=lambda sr: sr['top'][0])   # sort by top-x left-to-right
print(f"detected strings: {len(det_ordered)} (sorted by top-x)")

def build_pairs(flip):
    """Match detected strings to C/F DXF strings, either direct or reversed order."""
    img = []; dxf = []
    N = min(len(det_ordered), len(dxf_cf))
    for k in range(N):
        det_idx = (N-1-k) if flip else k
        sr = det_ordered[det_idx]
        dxf_row = dxf_cf[k]
        img.append([sr['top'][0], sr['top'][1]])
        dxf.append([dxf_row['x_mm'], dxf_row['yf_mm']])
        img.append([sr['bot'][0], sr['bot'][1]])
        dxf.append([dxf_row['x_mm'], dxf_row['yg_mm']])
    return np.array(img, float), np.array(dxf, float)

best = None
for flip in (False, True):
    img, dxf = build_pairs(flip)
    if len(img) < 8: continue
    # Homography (allows perspective) - but actually we believe the image is affine-ish
    # We'll try both homography and affine.
    Hmat, mask = cv2.findHomography(img, dxf, method=cv2.RANSAC, ransacReprojThreshold=5.0)
    if Hmat is None: continue
    # Residual: apply H to img, measure distance to dxf
    img_h = np.hstack([img, np.ones((len(img),1))])
    mapped = (Hmat @ img_h.T).T
    mapped = mapped[:,:2] / mapped[:,2:3]
    err = np.linalg.norm(mapped - dxf, axis=1)
    med = float(np.median(err))
    # Also affine
    Amat, _ = cv2.estimateAffine2D(img, dxf, method=cv2.RANSAC, ransacReprojThreshold=5.0)
    if Amat is not None:
        mapped_a = (Amat[:, :2] @ img.T + Amat[:, 2:3]).T
        err_a = np.linalg.norm(mapped_a - dxf, axis=1)
        med_a = float(np.median(err_a))
    else:
        med_a = 9e9
    print(f"flip={flip}: homography median error = {med:.2f} mm  affine median error = {med_a:.2f} mm")
    if best is None or med < best['med']:
        best = {'flip': flip, 'H': Hmat, 'A': Amat, 'med': med, 'med_a': med_a, 'mask': mask,
                'img': img, 'dxf': dxf}

print(f"\nbest: flip={best['flip']}, homography median err = {best['med']:.2f} mm, "
      f"affine median err = {best['med_a']:.2f} mm")
# Use affine if it's within 2x of homography (simpler, less overfitting for this planar problem)
use_affine = best['med_a'] < 2 * best['med']
if use_affine and best['A'] is not None:
    T = np.vstack([best['A'], [0,0,1]])
    print("using AFFINE transform")
else:
    T = best['H']; T = T / T[2,2]
    print("using HOMOGRAPHY transform")

def xf(pt):
    x, y = pt
    v = T @ np.array([x, y, 1.0])
    return (v[0]/v[2], v[1]/v[2])

# ----------------- use the transform to report column + base in DXF mm -----------------
# Column top/bottom (from low-res JSON, scaled)
col_x_full = col_x_low * SLF
col_y_top_full = col_y_top_low * SLF
col_y_bot_full = col_y_bot_low * SLF
col_top_mm = xf((col_x_full, col_y_top_full))
col_bot_mm = xf((col_x_full, col_y_bot_full))
col_length_mm = math.hypot(col_top_mm[0]-col_bot_mm[0], col_top_mm[1]-col_bot_mm[1])
print(f"\nCOLUMN (right-edge line) in DXF-mm:")
print(f"  top    = ({col_top_mm[0]:7.1f}, {col_top_mm[1]:7.1f})")
print(f"  bottom = ({col_bot_mm[0]:7.1f}, {col_bot_mm[1]:7.1f})")
print(f"  length = {col_length_mm:.1f} mm")

# Base silhouette extents (from low-res bbox)
base_corners = [
    (bbox_x0_low*SLF, bbox_y1_low*SLF),   # bottom-left
    (bbox_x1_low*SLF, bbox_y1_low*SLF),   # bottom-right
]
for name, pt in zip(['base-left-bottom', 'base-right-bottom'], base_corners):
    m = xf(pt)
    print(f"  {name}: image {pt} -> dxf ({m[0]:7.1f}, {m[1]:7.1f})")

# First bass string (string 47, bass, DXF x=254 mm) - column distance
dxf_bass = dxf_rows[0]
print(f"\nBass string #{dxf_bass['num']}: DXF x = {dxf_bass['x_mm']:.1f} mm")
col_top_dx = dxf_bass['x_mm'] - col_top_mm[0]
col_bot_dx = dxf_bass['x_mm'] - col_bot_mm[0]
print(f"  bass-x - column-top-x    = {col_top_dx:.1f} mm")
print(f"  bass-x - column-bottom-x = {col_bot_dx:.1f} mm")

# ----------------- save homography + draw debug -----------------
with open(OUT_JSON, 'w') as f:
    json.dump({
        'transform_type': 'affine' if use_affine else 'homography',
        'T': T.tolist(),
        'median_err_mm': best['med_a'] if use_affine else best['med'],
        'flip': best['flip'],
        'column': {'top_px': [col_x_full, col_y_top_full], 'top_mm': list(col_top_mm),
                   'bot_px': [col_x_full, col_y_bot_full], 'bot_mm': list(col_bot_mm),
                   'length_mm': col_length_mm},
    }, f, indent=2)

# Debug image: draw each detected string's fit
dbg = cv2.cvtColor(im, cv2.COLOR_GRAY2BGR)
for sr in string_records:
    if sr is None: continue
    p1 = tuple(int(v) for v in sr['top']); p2 = tuple(int(v) for v in sr['bot'])
    cv2.line(dbg, p1, p2, (0, 180, 0), 2)
    cv2.circle(dbg, p1, 5, (0, 0, 255), -1)
    cv2.circle(dbg, p2, 5, (255, 0, 0), -1)
# column line
cv2.line(dbg, (int(col_x_full), int(col_y_top_full)),
             (int(col_x_full), int(col_y_bot_full)), (0,0,255), 3)
cv2.imwrite(DBG, dbg)
print(f"\ndebug: {DBG}\nhomography JSON: {OUT_JSON}")
