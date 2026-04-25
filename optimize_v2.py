"""optimize_v2.py — v2 neck optimizer.

State vector (~26 DoF):
    θ on circle for n2 (D1sb), n3 (E5s), n4 (G7sb), n7 (G7fb)  [4 DoF]
    (x, y) for n8                                               [2 DoF]
    Handle lengths                                              [~15 DoF]
    Independent handle angles at n1-out, n2-in, n2-out, n8, n9-in [~5 DoF]

Hard constraints:
    - n0, n1, n5, n6, n9 positions locked.
    - n0 out horizontal, n1 in horizontal (= NBO→NBI line).
    - n5 in along +u, n5 out horizontal (seg 5 is the ST→BT line).
    - n6 in horizontal (seg 5 line), n6 out along +u.
    - n3, n4, n7 handles collinear with the circle tangent at their slide point.
    - n7 handles symmetric (equal length both sides).
    - n8 handles collinear (smooth), independent lengths.
    - n2 handles both on the outside-side of D1sb (no inward-kink).
    - Every tunable handle length ≥ W_MIN = 3 mm (except collapsed ones).

Objective: |A_brown − A_pink| + heavy buffer-penetration penalty (strict).

Emits erand47jc_v2_opt.svg.
"""
import math, os, re, shutil, copy, sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
_SB_DIR = os.path.join(HERE, "soundbox")
if _SB_DIR not in sys.path:
    sys.path.insert(0, _SB_DIR)
import build_harp as bh
import geometry as g            # soundbox/geometry.py
from inkscape_frame import INKSCAPE_DX, INKSCAPE_DY, to_inkscape

SRC_V2 = os.path.join(HERE, "erand47jc_v2.svg")
SRC_47 = os.path.join(HERE, "erand47.svg")
# v3 pass: bent-column anchors. The v2_opt SVG is preserved untouched.
DST    = os.path.join(HERE, "erand47jc_v3_opt.svg")

# Buffer-clearance radius for the optimizer. Decoupled from build_harp.R_BUFFER
# (which sizes the visible buffer-circle annotations and NB.y in the SVG).
# 2026-04-25: pitch mechanism switched from clicky-pen (Ø6.5 → R_BUF = 3.25 mm)
# to the Josephus 3D-printed lever. Each lever needs a single Ø2.7 mm clear
# mounting hole + a Ø2.7-3.5 bridge-pin tap; the controlling clearance is the
# mount-hole radius D_MOUNT/2 = 1.35 mm (see pedal/lever_3d.md). Smaller R_BUF
# lets the neck outline hug the buffer points more tightly.
D_MOUNT = 2.7
R_BUF   = D_MOUNT / 2.0   # = 1.35 mm
W_MIN   = 3.0
W_BUF   = 200000.0     # heavy penalty for penetration
W_OUTSIDE = 50000.0    # heavy penalty for inside-kink at n2

# Soundboard-slope +u direction (authoring = Inkscape for directions).
# Single source of truth is soundbox.geometry.u.
U = g.u

# Buffer centers (D1sb, E5s, G7sb, G7fb) in INKSCAPE frame, for circle-welded anchors.
# Reading from erand47jc_v2.svg: circles 0-46 are flat buffers, 47-93 are sharp buffers.
# String indices (0-based): D1=1, E5=30, G7=46 (in either batch).
# So: D1 sharp = circle (47+1) = 48.  E5 sharp = 47+30 = 77.  G7 sharp = 47+46 = 93.
# G7 flat = 46 (in flat batch 0-46).

def _num(s): return float(s)

def read_circles_inkscape(text):
    """Extract r=12 buffer circles in order from the SVG, as list of (cx, cy) Inkscape-frame."""
    out = []
    for m in re.finditer(
            r'<circle\b[^/]*?cx="([-0-9.eE]+)"[^/]*?cy="([-0-9.eE]+)"[^/]*?r="12"', text, re.S):
        out.append((_num(m.group(1)), _num(m.group(2))))
    return out


with open(SRC_V2) as fh: v2_text = fh.read()
circles_ink = read_circles_inkscape(v2_text)
assert len(circles_ink) == 94, f"expected 94 circles, got {len(circles_ink)}"

# Resolve the four welded-anchor buffer centers by string name (authoritative
# source: build_harp.build_strings()) and shift into the Inkscape frame. This
# keeps the optimizer robust to changes in SVG circle-rendering order or
# future edits to the string list — the welded anchors always track the D1
# sharp, E5 sharp, G7 sharp, and G7 flat buffers wherever they happen to sit.
_str_by_note = {s['note']: s for s in bh.build_strings()}

def _ink(pt):
    return (pt[0] - INKSCAPE_DX, pt[1] - INKSCAPE_DY)

D1SB = _ink(_str_by_note['D1']['sharp_buffer'])
E5S  = _ink(_str_by_note['E5']['sharp_buffer'])
G7SB = _ink(_str_by_note['G7']['sharp_buffer'])
G7FB = _ink(_str_by_note['G7']['flat_buffer'])

# Locked nodes, derived from authoritative geometry and shifted into the
# Inkscape frame. For the v3 pass the column anchors NBO, NBI, NTO track
# the bent column helpers in soundbox.geometry:
#   NBO.x = column_outer_x(NB.y)   (was COLUMN_OUTER_X = 12.7)
#   NBI.x = column_inner_x(NB.y)   (was COLUMN_INNER_X = 51.7)
#   NTO.x = column_outer_x(NT.y)   (was COLUMN_OUTER_X = 12.7)
# bh.NB and bh.NT already sample column_outer_x by y (see build_harp.py),
# so reading them directly gives the bent NBO / NTO. NBI needs explicit
# column_inner_x(y) sampling.
# Straight-column values for reference (the v2_opt descendant):
#   NBO_straight = (-39.2, 242.569)
#   NBI_straight = (-0.2,  242.569)
#   NTO_straight = (-39.2, 65.288)
# Bent at R=10000 mm shifts NBO.x ~21 mm west and NTO.x ~34 mm west.
NBO = to_inkscape(bh.NB)
NBI = to_inkscape((g.column_inner_x(bh.NB[1]), bh.NB[1]))
ST  = to_inkscape(g.ST)
_BT_XY = g.bulge_tip_point(g.S_TREBLE_CLEAR)[:2]
BT  = to_inkscape(_BT_XY)
NTO = to_inkscape(bh.NT)


# ---------- path + circle sampling ----------
def sample_cubic(P0, P1, P2, P3, n=200):
    out = []
    for k in range(n + 1):
        t = k/n; u = 1-t
        x = u*u*u*P0[0] + 3*u*u*t*P1[0] + 3*u*t*t*P2[0] + t*t*t*P3[0]
        y = u*u*u*P0[1] + 3*u*u*t*P1[1] + 3*u*t*t*P2[1] + t*t*t*P3[1]
        out.append((x, y))
    return out

def sample_line(P0, P1, n=6):
    return [(P0[0] + (P1[0]-P0[0])*k/n, P0[1] + (P1[1]-P0[1])*k/n) for k in range(n + 1)]

def shoelace(pts):
    s = 0.0
    for i in range(len(pts)):
        x0, y0 = pts[i]; x1, y1 = pts[(i+1) % len(pts)]
        s += x0*y1 - x1*y0
    return 0.5 * s


# ---------- pink polyline area (from erand47.svg) ----------
with open(SRC_47) as fh: main_text = fh.read()

NUM_RE = re.compile(r'[-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][-+]?\d+)?')

def tokenize_d(d):
    toks, i = [], 0
    while i < len(d):
        ch = d[i]
        if ch.isalpha(): toks.append(ch); i += 1
        elif ch in ' ,\t\n': i += 1
        else:
            m = NUM_RE.match(d, i)
            if m: toks.append(_num(m.group())); i = m.end()
            else: i += 1
    return toks

def parse_d(d):
    """Parse SVG path d-string to (M/L/C/A/Z) segment list."""
    toks = tokenize_d(d)
    segs, i = [], 0
    cx = cy = sx = sy = 0.0
    cmd = None
    while i < len(toks):
        t = toks[i]
        if isinstance(t, str):
            cmd = t; i += 1
        if cmd in ('m','M'):
            x,y = toks[i], toks[i+1]; i += 2
            cx,cy = (cx+x, cy+y) if cmd=='m' else (x,y)
            sx,sy = cx,cy
            cmd = 'l' if cmd=='m' else 'L'
        elif cmd in ('l','L'):
            x,y = toks[i], toks[i+1]; i += 2
            nx,ny = (cx+x, cy+y) if cmd=='l' else (x,y)
            segs.append(('L',(cx,cy),(nx,ny))); cx,cy = nx,ny
        elif cmd in ('h','H'):
            x = toks[i]; i += 1
            nx = cx+x if cmd=='h' else x
            segs.append(('L',(cx,cy),(nx,cy))); cx = nx
        elif cmd in ('v','V'):
            y = toks[i]; i += 1
            ny = cy+y if cmd=='v' else y
            segs.append(('L',(cx,cy),(cx,ny))); cy = ny
        elif cmd in ('c','C'):
            x1,y1,x2,y2,x3,y3 = (toks[i+k] for k in range(6)); i += 6
            if cmd == 'c':
                p1=(cx+x1,cy+y1); p2=(cx+x2,cy+y2); p3=(cx+x3,cy+y3)
            else:
                p1,p2,p3 = (x1,y1),(x2,y2),(x3,y3)
            segs.append(('C',(cx,cy),p1,p2,p3)); cx,cy = p3
        elif cmd in ('a','A'):
            rx = toks[i]; ry = toks[i+1]; phi=toks[i+2]
            fa = int(toks[i+3]); fs = int(toks[i+4])
            ex,ey = toks[i+5], toks[i+6]; i += 7
            nx,ny = (cx+ex, cy+ey) if cmd=='a' else (ex,ey)
            segs.append(('A',(cx,cy),(nx,ny),rx,ry,phi,fa,fs)); cx,cy = nx,ny
        elif cmd in ('z','Z'):
            segs.append(('L',(cx,cy),(sx,sy))); cx,cy = sx,sy
        else:
            i += 1
    return segs

def sample_arc(P0, P1, rx, ry, phi, fa, fs, n=12):
    r = rx
    mx, my = (P0[0]+P1[0])/2, (P0[1]+P1[1])/2
    dx, dy = P1[0]-P0[0], P1[1]-P0[1]
    d = math.hypot(dx, dy)
    if d < 1e-9 or d > 2*r + 1e-6: return [P0, P1]
    ux, uy = -dy/d, dx/d
    h = math.sqrt(max(0.0, r*r - (d/2)**2))
    sign = 1 if fa != fs else -1
    cx = mx + sign*h*ux; cy = my + sign*h*uy
    a0 = math.atan2(P0[1]-cy, P0[0]-cx)
    a1 = math.atan2(P1[1]-cy, P1[0]-cx)
    if fs == 1:
        if a1 < a0: a1 += 2*math.pi
    else:
        if a1 > a0: a1 -= 2*math.pi
    return [(cx + r*math.cos(a0 + (a1-a0)*k/n),
             cy + r*math.sin(a0 + (a1-a0)*k/n)) for k in range(n + 1)]

pink_segs = []
for m in re.finditer(r'<path[^>]*?d="([^"]+)"[^>]*?stroke="#ff69b4"', main_text, re.S):
    pink_segs.extend(parse_d(m.group(1)))

pink_pts = []
for s in pink_segs:
    if s[0] == 'C': pts = sample_cubic(s[1], s[2], s[3], s[4], n=40)
    elif s[0] == 'A': pts = sample_arc(s[1], s[2], *s[3:], n=12)
    else: pts = sample_line(s[1], s[2], n=6)
    if pink_pts and pts: pts = pts[1:]
    pink_pts.extend(pts)
A_PINK = abs(shoelace(pink_pts))
print(f"A_pink = {A_PINK:.1f}")


# ---------- state vector parameterization ----------
# For circle-welded anchors, θ is the angle (radians) on the circle measured
# from +x axis (Inkscape frame, y-down). Position = center + R*(cos θ, sin θ).
# Tangent direction (travel direction) = perpendicular to radius. Two choices
# per θ — we pick the one that keeps travel east-ish for n2/n3/n4 and
# west-ish for n7.

def pole_pos(center, theta):
    return (center[0] + R_BUF*math.cos(theta), center[1] + R_BUF*math.sin(theta))

def pole_tangent(theta, sign):
    # sign=+1 → tangent direction rotated +90° from radius (CCW in math frame)
    # sign=-1 → rotated -90°
    return (-sign*math.sin(theta), sign*math.cos(theta))

# Tangent sign convention: with y-down (Inkscape) frame, pole_tangent(θ, sign)
# returns (-sign*sinθ, sign*cosθ). The radial unit from circle center to node is
# (cosθ, sinθ); the travel-direction tangent that matches the real path is the
# one obtained by rotating radial -90° in the y-down frame, i.e. sign = -1 for
# every welded anchor on this path.
#   n2 (D1sb): radial ≈ (cos66°, sin66°) points ES; travel should head ENE →
#     sign=-1 gives (sin66°, -cos66°) = (+0.91, -0.40). ✓
#   n7 (G7fb): radial points WN; travel heads WSW → sign=-1 gives (-0.83, +0.56). ✓
# Previously SIGN_2/3/4 were +1 (travel would have flipped 180° W/south instead
# of E/north), which caused the initial reconstruction to lie ~8 mm inside the
# buffers. See debug log for full derivation.
SIGN_2, SIGN_3, SIGN_4, SIGN_7 = -1, -1, -1, -1


# Initial values from reading the current v2 path.
# θ extracted by: theta = atan2(node_y - center_y, node_x - center_x).
def _theta_from_pos(center, pos):
    return math.atan2(pos[1]-center[1], pos[0]-center[0])

THETA2_INIT = _theta_from_pos(D1SB, (72.585, 235.341))
THETA3_INIT = _theta_from_pos(E5S,  (547.124, 551.559))
THETA4_INIT = _theta_from_pos(G7SB, (769.969, 396.217))
THETA7_INIT = _theta_from_pos(G7FB, (762.990, 334.017))

# State: a plain dict for readability.
S = {
    'theta2': THETA2_INIT,  'theta3': THETA3_INIT,
    'theta4': THETA4_INIT,  'theta7': THETA7_INIT,
    'n8x': 391.465,         'n8y': 258.445,

    # handle lengths
    'w0_out':    0.0,     # NBO out (horizontal, currently zero → can grow)
    'w1_in':    12.87,    # n1 in (horizontal from NBO side)
    'w1_out':   24.54,    # n1 out (with tilt)
    'theta1_out': math.radians(0.0),   # n1 out angle (0=horizontal east, positive=south)
    'w2_in':    53.30,    'theta2_in_dev':  math.radians(-1.58),   # n2 in deviation from tangent (negative: south/east of tangent → outside side)
    'w2_out':  323.30,    'theta2_out_dev': math.radians(+9.35),   # n2 out deviation (positive: north of tangent)
    'w3_in':   269.20,    'w3_out':  59.49,
    'w4_in':    78.12,    'w4_out':  29.00,
    'w5_in':    15.00,   # user-tweaked; keeps ST approach a gentle arc (was 80 which caused overshoot loop at G7sbi->ST)
    'w6_out':  100.92,
    'w7':       49.77,    # n7 symmetric
    'w8_in':   367.70,    'w8_out': 367.70,   'theta_n8_mid': math.radians(-105.85),
    'w9_in':   184.90,    'theta_n9_in': math.radians(147.51),
}


def build_path(S):
    """Construct the 10-segment brown path (list of ('L',...) or ('C',...) tuples)
    from state S. All positions in Inkscape frame."""
    # Node positions
    n0 = NBO
    n1 = NBI
    n2 = pole_pos(D1SB, S['theta2'])
    n3 = pole_pos(E5S,  S['theta3'])
    n4 = pole_pos(G7SB, S['theta4'])
    n5 = ST
    n6 = BT
    n7 = pole_pos(G7FB, S['theta7'])
    n8 = (S['n8x'], S['n8y'])
    n9 = NTO

    # Tangent directions at circle anchors (travel direction along curve)
    tan2 = pole_tangent(S['theta2'], SIGN_2)  # unit vector
    tan3 = pole_tangent(S['theta3'], SIGN_3)
    tan4 = pole_tangent(S['theta4'], SIGN_4)
    tan7 = pole_tangent(S['theta7'], SIGN_7)

    # n8 tangent direction (used both sides, collinear smooth)
    tan8 = (math.cos(S['theta_n8_mid']), math.sin(S['theta_n8_mid']))
    # n9 incoming travel direction
    tan9_in = (math.cos(S['theta_n9_in']), math.sin(S['theta_n9_in']))
    # n1 out
    tan_n1_out = (math.cos(S['theta1_out']), math.sin(S['theta1_out']))
    # n2 handles (deviate from tangent on the OUTSIDE side). Tangent is tan2;
    # perpendicular = radial outward = (cos θ2, sin θ2). We rotate the tangent
    # by the deviation angle around the node, picking the outside side.
    def rot(v, a):
        c,s = math.cos(a), math.sin(a)
        return (c*v[0] - s*v[1], s*v[0] + c*v[1])
    tan2_in  = rot(tan2, S['theta2_in_dev'])
    tan2_out = rot(tan2, S['theta2_out_dev'])

    # +u direction (Inkscape-frame matches authoring for direction)
    u_dir = U

    segs = []

    # seg 0: NBO → n1, cubic. NBO out handle horizontal east (length w0_out),
    # n1 in handle horizontal west (length w1_in).
    P1 = (n0[0] + S['w0_out'], n0[1])
    P2 = (n1[0] - S['w1_in'],  n1[1])
    segs.append(('C', n0, P1, P2, n1))

    # seg 1: n1 → n2. n1 out at angle theta1_out, length w1_out. n2 in along
    # tangent rotated by theta2_in_dev on outside side.
    P1 = (n1[0] + S['w1_out']*tan_n1_out[0], n1[1] + S['w1_out']*tan_n1_out[1])
    # Incoming handle at n2: travel direction at P3=n2 is tan2_in (rotated tangent).
    # P2 = n2 - w2_in * tan2_in.
    P2 = (n2[0] - S['w2_in']*tan2_in[0], n2[1] - S['w2_in']*tan2_in[1])
    segs.append(('C', n1, P1, P2, n2))

    # seg 2: n2 → n3. n2 out along tan2_out, n3 in along tan3 (collinear with circle tangent).
    P1 = (n2[0] + S['w2_out']*tan2_out[0], n2[1] + S['w2_out']*tan2_out[1])
    P2 = (n3[0] - S['w3_in']*tan3[0],      n3[1] - S['w3_in']*tan3[1])
    segs.append(('C', n2, P1, P2, n3))

    # seg 3: n3 → n4. Both along circle tangents.
    P1 = (n3[0] + S['w3_out']*tan3[0], n3[1] + S['w3_out']*tan3[1])
    P2 = (n4[0] - S['w4_in']*tan4[0],  n4[1] - S['w4_in']*tan4[1])
    segs.append(('C', n3, P1, P2, n4))

    # seg 4: n4 → n5. n4 out along tan4. n5 in along +u.
    # n5 incoming travel direction = -u (the "handle" points back up along +u).
    # Travel dir at P3 = -u, so P2 = n5 - w5_in * (-u) = n5 + w5_in*u_dir.
    # But wait — incoming handle "along soundboard slope" = handle vector from
    # n5 extending NE along +u. Handle vector = P2 - n5 = w5_in * u_dir.
    # => P2 = n5 + w5_in*u_dir. Travel dir at P3 = (P3-P2)/|...| = -u_dir.
    P1 = (n4[0] + S['w4_out']*tan4[0], n4[1] + S['w4_out']*tan4[1])
    P2 = (n5[0] + S['w5_in']*u_dir[0], n5[1] + S['w5_in']*u_dir[1])
    segs.append(('C', n4, P1, P2, n5))

    # seg 5: n5 → n6, horizontal line.
    segs.append(('L', n5, n6))

    # seg 6: n6 → n7. n6 out along +u. n7 in along tan7 (collinear with G7fb tangent).
    P1 = (n6[0] + S['w6_out']*u_dir[0], n6[1] + S['w6_out']*u_dir[1])
    P2 = (n7[0] - S['w7']*tan7[0],      n7[1] - S['w7']*tan7[1])
    segs.append(('C', n6, P1, P2, n7))

    # seg 7: n7 → n8. n7 out along tan7 (symmetric, same length w7). n8 in along tan8.
    P1 = (n7[0] + S['w7']*tan7[0],      n7[1] + S['w7']*tan7[1])
    P2 = (n8[0] - S['w8_in']*tan8[0],   n8[1] - S['w8_in']*tan8[1])
    segs.append(('C', n7, P1, P2, n8))

    # seg 8: n8 → n9. n8 out along tan8 (collinear with in). n9 in along tan9_in.
    P1 = (n8[0] + S['w8_out']*tan8[0],  n8[1] + S['w8_out']*tan8[1])
    P2 = (n9[0] - S['w9_in']*tan9_in[0], n9[1] - S['w9_in']*tan9_in[1])
    segs.append(('C', n8, P1, P2, n9))

    # seg 9: n9 → n0, closing cubic along the column outer face.
    # For the v3 (bent-column) pass this cubic is built with vertical
    # tangents at both endpoints and handle lengths = dy/3. That
    # approximates the bent-column arc (R = COLUMN_BEND_RADIUS) to
    # well under 1 mm across the ~177 mm leg -- the arc deviates
    # ~34 mm from straight at the midpoint, but the cubic tracks the
    # arc with sub-mm error. v2's hardcoded (-39.74, 164.73) /
    # (-39.20, 242.569) literals assumed a straight column at x = -39.2
    # Inkscape-frame and are no longer valid once NBO / NTO move west.
    _dy_close = n0[1] - n9[1]
    _L_close  = _dy_close / 3.0
    P1 = (n9[0], n9[1] + _L_close)
    P2 = (n0[0], n0[1] - _L_close)
    segs.append(('C', n9, P1, P2, n0))

    return segs


def sample_path(segs, n_cubic=200, n_line=6):
    pts = []
    for s in segs:
        if s[0] == 'C': p = sample_cubic(s[1], s[2], s[3], s[4], n=n_cubic)
        else:           p = sample_line(s[1], s[2], n=n_line)
        if pts and p: p = p[1:]
        pts.extend(p)
    return pts


# ---------- objective ----------
def objective(S, verbose=False):
    try:
        segs = build_path(S)
    except Exception as e:
        if verbose: print(f"build_path error: {e}")
        return 1e12, 1e12, 0.0

    pts = sample_path(segs, n_cubic=300)
    A = abs(shoelace(pts))
    area_gap = abs(A - A_PINK)

    # Buffer penalty: for each sample point, check distance to each buffer.
    buf_pen = 0.0
    worst = 1e9
    for (bx, by) in circles_ink:
        dmin = 1e18
        for (px, py) in pts:
            d = math.hypot(px-bx, py-by)
            if d < dmin: dmin = d
        if dmin < worst: worst = dmin
        if dmin < R_BUF:
            buf_pen += (R_BUF - dmin) ** 2

    # n2 outside-side constraint. Outward radial at n2 = unit vector from D1sb
    # center to n2.
    n2 = pole_pos(D1SB, S['theta2'])
    ox, oy = (n2[0] - D1SB[0])/R_BUF, (n2[1] - D1SB[1])/R_BUF
    # Handle direction at n2 incoming side (handle vector P2 - n2, not travel dir).
    tan2 = pole_tangent(S['theta2'], SIGN_2)
    hx_in  = -S['w2_in']*math.cos(S['theta2_in_dev'])*tan2[0] + S['w2_in']*math.sin(S['theta2_in_dev'])*tan2[1]
    hy_in  = -S['w2_in']*math.sin(S['theta2_in_dev'])*tan2[0] - S['w2_in']*math.cos(S['theta2_in_dev'])*tan2[1]
    # (simpler: just compute actual P2 and check (P2-n2) · outward)
    # ...use segs[] directly:
    seg1 = segs[1]   # seg 1 ends at n2; P2 is seg1[3]
    P2_seg1 = seg1[3]
    in_vec = (P2_seg1[0]-n2[0], P2_seg1[1]-n2[1])
    dot_in = in_vec[0]*ox + in_vec[1]*oy
    out_pen = 0.0
    if dot_in < 0:
        out_pen += dot_in * dot_in
    # outgoing handle (seg 2 P1)
    seg2 = segs[2]
    P1_seg2 = seg2[2]
    out_vec = (P1_seg2[0]-n2[0], P1_seg2[1]-n2[1])
    dot_out = out_vec[0]*ox + out_vec[1]*oy
    if dot_out < 0:
        out_pen += dot_out * dot_out

    # Width floor
    w_pen = 0.0
    for k in ('w1_in', 'w1_out', 'w2_in', 'w2_out', 'w3_in', 'w3_out',
              'w4_in', 'w4_out', 'w5_in', 'w6_out', 'w7',
              'w8_in', 'w8_out', 'w9_in'):
        if S[k] < W_MIN:
            w_pen += (W_MIN - S[k]) ** 2

    # n1 outgoing tilt constraint (must be in [0, 90°] south-of-east)
    tilt_pen = 0.0
    if S['theta1_out'] < 0:
        tilt_pen += (S['theta1_out']) ** 2
    if S['theta1_out'] > math.pi/2:
        tilt_pen += (S['theta1_out'] - math.pi/2) ** 2

    obj = area_gap + W_BUF*buf_pen + W_OUTSIDE*out_pen + 100*w_pen + 10000*tilt_pen
    if verbose:
        print(f"  area_gap={area_gap:.1f}  buf_pen={buf_pen:.3f}  "
              f"out_pen={out_pen:.3f}  w_pen={w_pen:.3f}  worst={worst:.3f}")
    return obj, area_gap, worst


# ---------- coordinate descent ----------
def cd_scan(S, key, lo, hi, n=21):
    best_v = objective(S)[0]
    best_x = S[key]
    for k in range(n):
        S[key] = lo + (hi-lo)*k/(n-1)
        v = objective(S)[0]
        if v < best_v - 1e-9:
            best_v = v; best_x = S[key]
    S[key] = best_x
    return best_v


v0, gap0, worst0 = objective(S, verbose=True)
print(f"Initial: obj={v0:.1f}  area_gap={gap0:.1f}  worst_buf_dist={worst0:.3f}")

for pass_idx in range(4):
    scale = 0.5 ** pass_idx
    d_theta_circle = math.radians(15) * scale   # slide-on-circle range
    d_theta_h      = math.radians(8)  * scale   # handle angle range
    d_xy           = 30.0 * scale
    rel_w          = 0.4 * scale                # multiplicative window for widths

    # θ on circles
    for k in ('theta2','theta3','theta4','theta7'):
        t0 = S[k]; cd_scan(S, k, t0 - d_theta_circle, t0 + d_theta_circle)

    # n8 (x,y)
    x0 = S['n8x']; cd_scan(S, 'n8x', x0 - d_xy, x0 + d_xy)
    y0 = S['n8y']; cd_scan(S, 'n8y', y0 - d_xy, y0 + d_xy)

    # handle angles
    for k in ('theta1_out','theta2_in_dev','theta2_out_dev','theta_n8_mid','theta_n9_in'):
        t0 = S[k]; cd_scan(S, k, t0 - d_theta_h, t0 + d_theta_h)

    # handle widths — multiplicative scan around current.
    # USER-LOCKED widths (handles at G7sb and ST): w4_in, w4_out, w5_in are
    # excluded from the scan. The user hand-set these lengths in
    # erand47jc_v2.svg and does not want the optimizer to grow them
    # (unbounded-growth was producing the ST/BT loop).
    for k in ('w0_out','w1_in','w1_out','w2_in','w2_out','w3_in','w3_out',
              'w6_out','w7','w8_in','w8_out','w9_in'):
        w0 = S[k]
        lo = max(0.0, w0 * (1.0 - rel_w))
        hi = w0 * (1.0 + rel_w)
        if hi - lo < 2.0:
            hi = lo + 2.0
        cd_scan(S, k, lo, hi)

    v, gap, worst = objective(S, verbose=True)
    print(f"pass {pass_idx}: obj={v:.1f}  area_gap={gap:.1f}  worst={worst:.3f}")


# ---------- emit svg ----------
segs = build_path(S)
# Build d string. Mix of relative/absolute for readability; use all-absolute for simplicity.
d_parts = [f"M {segs[0][1][0]:.3f},{segs[0][1][1]:.3f}"]
for s in segs:
    if s[0] == 'L':
        q = s[2]
        d_parts.append(f"L {q[0]:.3f},{q[1]:.3f}")
    else:
        _, _, p1, p2, p3 = s
        d_parts.append(f"C {p1[0]:.3f},{p1[1]:.3f} {p2[0]:.3f},{p2[1]:.3f} {p3[0]:.3f},{p3[1]:.3f}")

d_new = " ".join(d_parts)

# Replace the brown-path d in erand47jc_v2.svg and write to DST.
new_text = re.sub(
    r'(<path\s+d=")([^"]+)(")',
    lambda m: m.group(1) + d_new + m.group(3),
    v2_text, count=1)

with open(DST, "w") as fh: fh.write(new_text)
print(f"\nwrote {DST}")
print(f"final obj={v:.1f}  area_gap={gap:.1f}  worst_buf_dist={worst:.3f}")
