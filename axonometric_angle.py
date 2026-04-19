#!/usr/bin/env python3
"""Determine the drawing's projection angles by analysing dominant line orientations
in the base + column-base region, where real-3D axes are clearest.

In an axonometric/oblique drawing of a rectangular block:
  - real vertical edges  -> image ~vertical
  - real front-face horizontals -> image ~horizontal (if oblique with front face parallel
    to the picture plane) OR at some angle (if iso/trimetric)
  - real depth edges (going back) -> image at the "receding" angle alpha
"""
import math
import numpy as np
import cv2
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
SRC = '/home/james.clements/projects/erand/corner-zoom.png'
DBG = '/home/james.clements/projects/erand/angles-debug.png'

im = np.array(Image.open(SRC))
H, W = im.shape
print(f"{W}x{H}")

# Binarize and edge-detect
_, bw = cv2.threshold(cv2.GaussianBlur(im,(3,3),0), 0, 255,
                       cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
edges = cv2.Canny(bw, 60, 160)

# Hough: find all lines long enough to be structural edges (not ornamental)
linesP = cv2.HoughLinesP(edges, 1, np.pi/1440,
                         threshold=60, minLineLength=80, maxLineGap=8)
segs = [] if linesP is None else linesP[:,0,:]
print(f"Hough segments: {len(segs)}")

# Classify by angle (0..180 degrees, 0=E, 90=S in y-down image)
def angle_deg(seg):
    x1,y1,x2,y2 = seg
    a = math.degrees(math.atan2(y2-y1, x2-x1))
    return (a + 180) % 180     # 0..180

def length(seg):
    x1,y1,x2,y2 = seg
    return math.hypot(x2-x1, y2-y1)

# Weighted histogram (weight by length so longer lines matter more)
bin_width = 0.5
hist = np.zeros(int(180/bin_width))
for s in segs:
    a = angle_deg(s); L = length(s)
    hist[int(a/bin_width) % len(hist)] += L

# Smooth
hist = np.convolve(hist, np.ones(3)/3, mode='same')

# Find peaks
peaks = []
for i in range(len(hist)):
    left = hist[(i-1)%len(hist)]; right = hist[(i+1)%len(hist)]
    if hist[i] > left and hist[i] > right and hist[i] > 300:
        peaks.append((i*bin_width, float(hist[i])))
peaks.sort(key=lambda p: -p[1])
print(f"\nTop dominant line angles (weighted by length, degrees 0..180):")
for ang, score in peaks[:12]:
    # interpret: 0 = horizontal east-going, 90 = vertical (down), ...
    print(f"   {ang:6.2f} deg   weight={score:.0f}")

# Identify the three projection axes.
# By construction: 0 = image-horizontal (pure east-west), 90 = image-vertical.
# Non-orthogonal peaks (far from 0, 90, 180) are the oblique/isometric axes.
def nearest(p, targets):
    return min(abs(((p - t + 90) % 180) - 90) for t in targets)

axes = []
for ang, score in peaks[:15]:
    d_from_axis = nearest(ang, [0, 90, 180])
    if d_from_axis > 8 and d_from_axis < 65:
        axes.append((ang, score, d_from_axis))

print(f"\nOblique/depth axes (non-orthogonal angles):")
for ang, score, dev in axes[:8]:
    # Two natural conventions:
    #   angle FROM HORIZONTAL (positive going down right = y-down)
    from_horiz_ccw = -ang  # counter-clockwise from +x (math convention; image is y-down)
    # Express as elevation above horizontal (positive = going up-and-right in real world)
    # ang in 0..180 with 90 = straight down. So a line at, say, 120 goes down-and-left with 30° from horizontal.
    elev = 90 - abs(90 - ang)  # angle FROM horizontal axis, 0..90
    side = 'down-right' if ang < 90 else 'down-left'
    print(f"   {ang:6.2f} deg (in 0..180)  =>  {elev:.2f} deg from horizontal, going {side}"
          f"   weight={score:.0f}")

# --- Visualise ---
dbg = cv2.cvtColor(im, cv2.COLOR_GRAY2BGR)
for s in segs:
    a = angle_deg(s)
    # Colour-code by angle bin: near-horizontal = blue, near-vertical = red, oblique = green
    dev_h = abs(((a - 0 + 90) % 180) - 90)
    dev_v = abs(((a - 90 + 90) % 180) - 90)
    if dev_h < 3:   col = (255, 0, 0)    # horizontal
    elif dev_v < 3: col = (0, 0, 255)    # vertical
    elif 8 < dev_h < 65 and 8 < dev_v < 65: col = (0, 200, 0)  # oblique
    else:           col = (180, 180, 180)
    cv2.line(dbg, (s[0],s[1]), (s[2],s[3]), col, 1)

cv2.imwrite(DBG, dbg)
print(f"\ndebug image: {DBG}")
