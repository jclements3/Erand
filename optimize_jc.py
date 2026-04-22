"""optimize_jc.py — tighten the hand-drawn brown neck curve in erand47jc.svg
toward the pink geodesic polyline, without penetrating any buffer.

Warm start: the 9-node (8 distinct + closure) brown path authored in Inkscape.
Work in authoring frame; translate to Inkscape frame only on output.

Parameterization
----------------
  For each segment s (except the two locked lines), two independent handles:
      P1_s = P0_s + w_out_s * unit(theta_out_s)
      P2_s = P3_s - w_in_s  * unit(theta_in_s)
  This allows cusps at every node (matches the Inkscape "c" nodetype).

  Floaters n2..n6: positions (x, y) are tunable.

Locked
------
  n0 NB       = (12.700, 323.844). seg 7 (NT->NB) locked line; seg 0 (NB->C1sbi)
                locked horizontal line; theta_out_seg0 = east, theta_in_seg0 = east.
  n1 C1sbi    = (101.700, 323.844). seg 1 outgoing handle locked east:
                theta_out_seg1 = 0.
  n7 NT       = (12.700, 146.563). seg 6 incoming handle locked south:
                theta_in_seg6 = pi/2.

Objective
---------
    |A_brown - A_pink|                        # shoelace signed-area difference
    + W_buf * sum max(0, R_buf - dist)^2      # buffer penetration penalty
    + W_wmin * sum max(0, w_min - w)^2        # handle floor
"""
import math
import re
import json

SRC_JC = "erand47jc.svg"                # original hand-drawn reference
SRC_47 = "erand47.svg"                  # buffers + pink polyline
DST = "erand47jc_opt.svg"               # optimizer output
SNAP = "erand47jc_opt.pre_edit.svg"     # snapshot of last optimizer output
LOCKS = "erand47jc_opt.locks.json"      # persistent locks (accumulates each run)

# Detect user edits by diffing DST vs SNAP. If SNAP doesn't exist (first run),
# no pins are detected and the hand-drawn erand47jc.svg is the warm start.
# - Any node whose warm-start position differs from snapshot by > NODE_MOVE_EPS
#   mm is PINNED for this pass.
# - Inkscape nodetype in {'s', 'z', 'a'} at a given index forces C¹ at that node
#   (outgoing tangent direction must equal incoming tangent direction).
NODE_MOVE_EPS = 0.5
HANDLE_EDIT_EPS = 0.5          # mm: treat as user edit if P1/P2 moved this much
HV_SNAP_DEG = 2.0              # snap to exact H/V only for true approximations
                               # (tight enough not to steal 5-10° intentional tilts)

# Pole-welded anchors: nodes that live on a specific buffer circle. Position
# is 1-D parameterized by `theta_circle` (angle on the circle); the tangent
# direction at that point is derived from theta_circle (perpendicular to the
# radius), so rotating the outgoing handle off-horizontal automatically slides
# the anchor along the circle. The default (southern pole) for C1sbi is
# theta = pi/2 in SVG math convention.
POLE_ANCHOR = {
    # node_idx: (center_x, center_y, radius, default_theta, tangent_sign)
    # tangent_sign: +1 => east-going at default, -1 => west-going
    1: (101.700, 311.844, 12.0, math.pi/2, +1),
}

def pole_pos(i, theta):
    cx, cy, R, _, _ = POLE_ANCHOR[i]
    return (cx + R*math.cos(theta), cy + R*math.sin(theta))

def pole_tangent(i, theta):
    """Tangent direction angle (radians) at the pole-anchor's position."""
    _, _, _, _, sign = POLE_ANCHOR[i]
    # Tangent vector perpendicular to radius: (sin θ, -cos θ) for "east-going"
    # sense (sign=+1) or (-sin θ, cos θ) for "west-going" (sign=-1).
    tx = sign * math.sin(theta)
    ty = -sign * math.cos(theta)
    return math.atan2(ty, tx)

def theta_from_tangent(i, tangent_angle):
    """Given a desired outgoing tangent angle at pole anchor i, return the
    theta_circle value that makes the tangent match. Inverse of pole_tangent."""
    _, _, _, _, sign = POLE_ANCHOR[i]
    # (sign*sin θ, -sign*cos θ) = (cos τ, sin τ) where τ = tangent_angle.
    # Solve sin θ = sign*cos τ, cos θ = -sign*sin τ.
    c, s = math.cos(tangent_angle), math.sin(tangent_angle)
    return math.atan2(sign*c, -sign*s)

INKSCAPE_DX = 51.9
INKSCAPE_DY = 121.64

R_BUF = 12.0
W_MIN = 3.0
TOL_BUF = 0.0
W_BUF = 200000.0
W_WMIN = 100.0
N_CUBIC_SAMPLES = 400

NUM_RE = re.compile(r'[-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][-+]?\d+)?')

def tokenize_d(d):
    toks, i = [], 0
    while i < len(d):
        ch = d[i]
        if ch.isalpha():
            toks.append(ch); i += 1
        elif ch in ' ,\t\n':
            i += 1
        else:
            m = NUM_RE.match(d, i)
            if not m:
                i += 1; continue
            toks.append(float(m.group())); i = m.end()
    return toks


def parse_d_to_segments(d):
    toks = tokenize_d(d)
    segs, i = [], 0
    cx = cy = sx = sy = 0.0
    cmd = None
    while i < len(toks):
        t = toks[i]
        if isinstance(t, str):
            cmd = t; i += 1
        if cmd in ('m', 'M'):
            x, y = toks[i], toks[i+1]; i += 2
            cx, cy = (cx+x, cy+y) if cmd == 'm' else (x, y)
            sx, sy = cx, cy
            cmd = 'l' if cmd == 'm' else 'L'
        elif cmd in ('l', 'L'):
            x, y = toks[i], toks[i+1]; i += 2
            nx, ny = (cx+x, cy+y) if cmd == 'l' else (x, y)
            segs.append(('L', (cx, cy), (nx, ny))); cx, cy = nx, ny
        elif cmd in ('h', 'H'):
            x = toks[i]; i += 1
            nx = cx + x if cmd == 'h' else x
            segs.append(('L', (cx, cy), (nx, cy))); cx = nx
        elif cmd in ('v', 'V'):
            y = toks[i]; i += 1
            ny = cy + y if cmd == 'v' else y
            segs.append(('L', (cx, cy), (cx, ny))); cy = ny
        elif cmd in ('c', 'C'):
            x1, y1, x2, y2, x3, y3 = (toks[i+k] for k in range(6)); i += 6
            if cmd == 'c':
                p1 = (cx+x1, cy+y1); p2 = (cx+x2, cy+y2); p3 = (cx+x3, cy+y3)
            else:
                p1, p2, p3 = (x1, y1), (x2, y2), (x3, y3)
            segs.append(('C', (cx, cy), p1, p2, p3)); cx, cy = p3
        elif cmd in ('z', 'Z'):
            segs.append(('L', (cx, cy), (sx, sy))); cx, cy = sx, sy
        elif cmd in ('a', 'A'):
            rx, ry = toks[i], toks[i+1]
            phi = toks[i+2]; fa = int(toks[i+3]); fs = int(toks[i+4])
            ex, ey = toks[i+5], toks[i+6]; i += 7
            nx, ny = (cx+ex, cy+ey) if cmd == 'a' else (ex, ey)
            segs.append(('A', (cx, cy), (nx, ny), rx, ry, phi, fa, fs))
            cx, cy = nx, ny
        else:
            raise ValueError(f"unhandled {cmd!r}")
    return segs


def sample_cubic(P0, P1, P2, P3, n=40):
    out = []
    for k in range(n+1):
        t = k/n; u = 1-t
        x = u*u*u*P0[0] + 3*u*u*t*P1[0] + 3*u*t*t*P2[0] + t*t*t*P3[0]
        y = u*u*u*P0[1] + 3*u*u*t*P1[1] + 3*u*t*t*P2[1] + t*t*t*P3[1]
        out.append((x, y))
    return out

def sample_line(P0, P1, n=6):
    return [(P0[0]+(P1[0]-P0[0])*k/n, P0[1]+(P1[1]-P0[1])*k/n) for k in range(n+1)]

def sample_arc(P0, P1, rx, ry, phi, fa, fs, n=12):
    r = rx
    mx, my = (P0[0]+P1[0])/2, (P0[1]+P1[1])/2
    dx, dy = P1[0]-P0[0], P1[1]-P0[1]
    d = math.hypot(dx, dy)
    if d < 1e-9: return [P0, P1]
    if d > 2*r: d = 2*r
    ux, uy = -dy/d, dx/d
    h = math.sqrt(max(0.0, r*r - (d/2)**2))
    sign = 1 if (fa != fs) else -1
    cx = mx + sign*h*ux; cy = my + sign*h*uy
    a0 = math.atan2(P0[1]-cy, P0[0]-cx)
    a1 = math.atan2(P1[1]-cy, P1[0]-cx)
    if fs == 1:
        if a1 < a0: a1 += 2*math.pi
    else:
        if a1 > a0: a1 -= 2*math.pi
    return [(cx + r*math.cos(a0 + (a1-a0)*k/n),
             cy + r*math.sin(a0 + (a1-a0)*k/n)) for k in range(n+1)]

def shoelace(pts):
    s = 0.0
    for i in range(len(pts)):
        x0, y0 = pts[i]; x1, y1 = pts[(i+1) % len(pts)]
        s += x0*y1 - x1*y0
    return 0.5*s


# ---------- read data ----------
import os
with open(SRC_JC) as fh: jc_text = fh.read()
with open(SRC_47) as fh: main_text = fh.read()


def extract_brown_path(svg_text):
    """Return (brown_d, nodetypes_str). Nodetypes may be ''."""
    for attrs in re.findall(r'<path\b([^>]*?)/>', svg_text, re.S | re.I):
        if 'stroke="#8b4513"' in attrs.lower():
            md = re.search(r'\bd="([^"]+)"', attrs, re.S)
            mnt = re.search(r'\bsodipodi:nodetypes="([^"]+)"', attrs, re.S)
            if md:
                return md.group(1), (mnt.group(1) if mnt else '')
    return None, ''


def untrans(p): return (p[0] + INKSCAPE_DX, p[1] + INKSCAPE_DY)


def brown_to_segs(d):
    raw = parse_d_to_segments(d)
    out = []
    for s in raw:
        if s[0] == 'L':
            out.append(('L', untrans(s[1]), untrans(s[2])))
        else:
            out.append(('C', untrans(s[1]), untrans(s[2]), untrans(s[3]), untrans(s[4])))
    return out


# Hand-drawn (only used as fallback warm start).
hand_d, hand_nt = extract_brown_path(jc_text)
assert hand_d
hand_segs = brown_to_segs(hand_d)
hand_nodes = [hand_segs[0][1]] + [s[-1] for s in hand_segs[:-1]]

# Reference for pin-detection: the snapshot of the previous optimizer output.
# If it doesn't exist (first ever run), fall back to the hand-drawn reference.
ref_d, ref_nt = hand_d, hand_nt
ref_source = SRC_JC
if os.path.exists(SNAP):
    with open(SNAP) as fh: snap_text = fh.read()
    sd, snt = extract_brown_path(snap_text)
    if sd:
        ref_d, ref_nt = sd, snt
        ref_source = SNAP

ref_segs = brown_to_segs(ref_d)
ref_nodes = [ref_segs[0][1]] + [s[-1] for s in ref_segs[:-1]]

# Warm start: prefer DST if it exists and differs from the reference.
warm_source = SRC_JC
if os.path.exists(DST):
    with open(DST) as fh: warm_text = fh.read()
    wd, wnt = extract_brown_path(warm_text)
    if wd and wd != ref_d:
        warm_source = DST
        brown_d, nodetypes = wd, wnt
    else:
        brown_d, nodetypes = ref_d, ref_nt
else:
    brown_d, nodetypes = ref_d, ref_nt

print(f"warm start: {warm_source}")
print(f"pin reference: {ref_source}")
print(f"nodetypes: {nodetypes!r}")

brown_segs = brown_to_segs(brown_d)

N_SEG = len(brown_segs)
print(f"brown: {N_SEG} segments")
for k, s in enumerate(brown_segs):
    print(f"  seg {k}: {s[0]}  P0={s[1]}  P3={s[-1]}")

# nodes (distinct) — drop the wraparound
nodes = [brown_segs[0][1]]
for s in brown_segs[:-1]:
    nodes.append(s[-1])
assert math.hypot(brown_segs[-1][-1][0]-nodes[0][0], brown_segs[-1][-1][1]-nodes[0][1]) < 1e-6
N_NODES = len(nodes)
print(f"nodes: {N_NODES}")
for i, n in enumerate(nodes):
    print(f"  n{i}: ({n[0]:8.3f}, {n[1]:8.3f})")

# ---------- buffers + pink ----------
buffers = []
for cx, cy in re.findall(
        r'<circle\b[^>]*?cx="([-0-9.eE]+)"[^>]*?cy="([-0-9.eE]+)"[^>]*?r="12\.0"[^>]*?stroke="#000"',
        main_text, re.S):
    buffers.append((float(cx), float(cy)))
print(f"buffers: {len(buffers)}")

pink_segs = []
for m in re.finditer(r'<path[^>]*?d="([^"]+)"[^>]*?stroke="#ff69b4"', main_text, re.S):
    pink_segs.extend(parse_d_to_segments(m.group(1)))

def sample_segments(segs, n_cubic=40, n_line=6, n_arc=12):
    out = []
    for s in segs:
        if s[0] == 'C': pts = sample_cubic(s[1], s[2], s[3], s[4], n=n_cubic)
        elif s[0] == 'A': pts = sample_arc(s[1], s[2], *s[3:], n=n_arc)
        else: pts = sample_line(s[1], s[2], n=n_line)
        if out and pts: pts = pts[1:]
        out.extend(pts)
    return out

pink_pts = sample_segments(pink_segs)
A_pink = shoelace(pink_pts)
print(f"A_pink = {A_pink:.1f}  (|A|={abs(A_pink):.1f})")


# ---------- parameterization ----------
# Node indices: 0=NB, 1=C1sbi, 2..6=floaters, 7=NT.
# Locked positions:
LOCKED_NODES = {0, 1, 7}

# Locked tangents (per segment, per side):
#   seg 0 (NB->C1sbi line, LOCKED  — not tunable at all)
#   seg 7 (NT->NB   line, LOCKED)
#   seg 1 P0 (C1sbi outgoing) = east
#   seg 6 P3 (NT incoming)    = south
# No other tangent locks — every cusp is free.
LOCKED_SEGS = {0, 7}
TUNABLE_SEGS = [s for s in range(N_SEG) if s not in LOCKED_SEGS]
print(f"tunable segs: {TUNABLE_SEGS}")

# State: per-tunable-segment, (theta_out, w_out, theta_in, w_in). But some of
# these scalars are pinned:
#   theta_out[1] = 0 (east)
#   theta_in[6]  = pi/2 (south)
# Floaters: pos[i] for i in {2,3,4,5,6} tunable.

pos = [list(n) for n in nodes]

theta_out = [0.0]*N_SEG
theta_in  = [0.0]*N_SEG
w_out = [0.0]*N_SEG
w_in  = [0.0]*N_SEG

for s, seg in enumerate(brown_segs):
    if seg[0] == 'C':
        P0, P1, P2, P3 = seg[1], seg[2], seg[3], seg[4]
        theta_out[s] = math.atan2(P1[1]-P0[1], P1[0]-P0[0])
        w_out[s] = math.hypot(P1[0]-P0[0], P1[1]-P0[1])
        theta_in[s]  = math.atan2(P3[1]-P2[1], P3[0]-P2[0])  # travel direction at P3
        w_in[s]  = math.hypot(P3[0]-P2[0], P3[1]-P2[1])

# Enforce initial locks.
# Only theta_out[1] is truly locked (C1sbi is AT the south pole of C1 sharp,
# so the natural buffer-tangent direction there is +east; anything else would
# immediately cut into the C1 sharp circle). NT's incoming tangent is a genuine
# cusp in the hand-drawn shape (~148°, not +south), so we DON'T lock it — it
# stays free.
theta_out[1] = 0.0


def apply_c1_ties():
    """For each C¹ node i, set theta_out[seg_i] = theta_in[seg_{i-1}]."""
    for i in C1_NODES:
        seg_out = i % N_SEG                # segment starting at node i
        seg_in  = (i - 1) % N_SEG          # segment ending at node i
        if seg_out in LOCKED_SEGS or seg_in in LOCKED_SEGS:
            continue
        theta_out[seg_out] = theta_in[seg_in]


def rebuild_handles():
    apply_c1_ties()
    H = [None]*N_SEG
    for s in range(N_SEG):
        i0 = s % N_NODES
        i3 = (s+1) % N_NODES
        P0 = tuple(pos[i0]); P3 = tuple(pos[i3])
        if s == 0:  # NB->C1sbi straight horizontal line (kept as line)
            H[s] = ('L', P0, P3)
        elif s == 7:  # NT->NB vertical line
            H[s] = ('L', P0, P3)
        else:
            c0, s0 = math.cos(theta_out[s]), math.sin(theta_out[s])
            c3, s3 = math.cos(theta_in[s]),  math.sin(theta_in[s])
            P1 = (P0[0] + w_out[s]*c0, P0[1] + w_out[s]*s0)
            P2 = (P3[0] - w_in[s]*c3,  P3[1] - w_in[s]*s3)
            H[s] = ('C', P0, P1, P2, P3)
    return H


def sample_brown(H, n_cubic=N_CUBIC_SAMPLES, n_line=4):
    out = []
    for s in H:
        if s[0] == 'C': pts = sample_cubic(s[1], s[2], s[3], s[4], n=n_cubic)
        else: pts = sample_line(s[1], s[2], n=n_line)
        if out and pts: pts = pts[1:]
        out.extend(pts)
    return out


def objective():
    H = rebuild_handles()
    pts = sample_brown(H)
    A = shoelace(pts)
    area_gap = abs(abs(A) - abs(A_pink))

    buf_pen = 0.0
    worst = 1e9
    for (bx, by) in buffers:
        d_min = min(math.hypot(px-bx, py-by) for (px, py) in pts)
        if d_min < worst: worst = d_min
        if d_min < R_BUF - TOL_BUF:
            buf_pen += (R_BUF - TOL_BUF - d_min) ** 2

    w_pen = 0.0
    for s in TUNABLE_SEGS:
        if not w_out_locked(s) and w_out[s] < W_MIN:
            w_pen += (W_MIN - w_out[s]) ** 2
        if not w_in_locked(s) and w_in[s] < W_MIN:
            w_pen += (W_MIN - w_in[s]) ** 2

    return area_gap + W_BUF*buf_pen + W_WMIN*w_pen, area_gap, worst


# ---------- coordinate descent ----------
def cd_scan(setter, lo, hi, initial, n=21):
    best_val = objective()[0]
    best_x = initial
    for k in range(n):
        x = lo + (hi-lo)*k/(n-1)
        setter(x)
        v = objective()[0]
        if v < best_val - 1e-9:
            best_val = v; best_x = x
    setter(best_x)
    return best_val


# n4 is the near-BT corner of the treble end. Pinning its position preserves
# the silhouette's rightmost extent; otherwise the optimizer pulls it ~48 mm
# inward because the treble bulge contributes a lot of area. Its handles (on
# segs 3 and 4) still tune.
FLOATERS_DEFAULT = [2, 3, 5, 6]

# Apply user pins: any floater whose warm-start position differs from the
# reference (last optimizer snapshot, or hand-drawn on first run) by
# > NODE_MOVE_EPS mm is pinned at the warm-start value.
USER_PINNED = set()
for i in range(N_NODES):
    dx = nodes[i][0] - ref_nodes[i][0]
    dy = nodes[i][1] - ref_nodes[i][1]
    if math.hypot(dx, dy) > NODE_MOVE_EPS:
        USER_PINNED.add(i)
        print(f"  user-pinned n{i}: ref({ref_nodes[i][0]:.3f},{ref_nodes[i][1]:.3f}) "
              f"-> pinned({nodes[i][0]:.3f},{nodes[i][1]:.3f})  delta=({dx:+.3f},{dy:+.3f})")

# Merge with persisted locks (if any).
persisted = {"pinned_nodes": [], "c1_nodes": [], "handle_locks": [],
             "pinned_positions": {}, "theta_circle": {}}
if os.path.exists(LOCKS):
    with open(LOCKS) as fh:
        persisted = json.load(fh)
for i in persisted.get("pinned_nodes", []):
    USER_PINNED.add(i)
    recorded = persisted.get("pinned_positions", {}).get(str(i))
    if recorded is not None:
        pos[i][0], pos[i][1] = recorded[0], recorded[1]

# Apply persisted theta_circle values (slides the pole anchor along its buffer).
THETA_CIRCLE = {}
for k, v in persisted.get("theta_circle", {}).items():
    i = int(k)
    THETA_CIRCLE[i] = float(v)
    pos[i][0], pos[i][1] = pole_pos(i, THETA_CIRCLE[i])

FLOATERS = [i for i in FLOATERS_DEFAULT if i not in USER_PINNED]
print(f"floaters this pass: {FLOATERS}")
print(f"persisted pins: {sorted(USER_PINNED)}")

# Detect user-edited handles: for each segment s, compare (P1, P2) in warm
# start vs reference (snapshot). If the relative handle vector changed by
# > HANDLE_EDIT_EPS, lock that handle. Snap angles within HV_SNAP_DEG of
# exact H/V to the exact value.
HANDLE_LOCKED = set()   # {(s, 'out'), (s, 'in')}
def handle_rel(seg, end):
    """Return handle vector relative to its anchor, in segment-local sense."""
    if seg[0] != 'C':
        return None
    if end == 'out':
        return (seg[2][0]-seg[1][0], seg[2][1]-seg[1][1])
    else:  # 'in' — at P3, vector is P3 - P2 (travel direction at P3)
        return (seg[4][0]-seg[3][0], seg[4][1]-seg[3][1])

SNAP_NOTES = []
for s in range(N_SEG):
    if s in LOCKED_SEGS: continue
    ref_seg = ref_segs[s] if s < len(ref_segs) else None
    warm_seg = brown_segs[s]
    if ref_seg is None or ref_seg[0] != 'C' or warm_seg[0] != 'C':
        continue
    for end in ('out', 'in'):
        rv = handle_rel(ref_seg, end)
        wv = handle_rel(warm_seg, end)
        if rv is None or wv is None: continue
        dx = wv[0] - rv[0]; dy = wv[1] - rv[1]
        if math.hypot(dx, dy) > HANDLE_EDIT_EPS:
            HANDLE_LOCKED.add((s, end))
            # Skip angle snap for zero-length handles (angle undefined).
            if math.hypot(wv[0], wv[1]) < 0.1:
                SNAP_NOTES.append(
                    f"  user-collapsed handle (seg{s}, {end}): len 0")
                continue
            # Snap to H/V if within tolerance.
            ang = math.degrees(math.atan2(wv[1], wv[0]))
            # Normalize to (-180, 180]
            while ang <= -180: ang += 360
            while ang > 180:  ang -= 360
            snap_to = None
            for target in (0.0, 90.0, 180.0, -90.0):
                delta = ang - target
                while delta > 180: delta -= 360
                while delta < -180: delta += 360
                if abs(delta) <= HV_SNAP_DEG:
                    snap_to = target
                    break
            if snap_to is not None:
                r = math.hypot(wv[0], wv[1])
                ca, sa = math.cos(math.radians(snap_to)), math.sin(math.radians(snap_to))
                new_v = (r*ca, r*sa)
                # Write back into brown_segs (and into the initial theta/w below)
                if end == 'out':
                    P0 = warm_seg[1]
                    brown_segs[s] = ('C', P0, (P0[0]+new_v[0], P0[1]+new_v[1]),
                                     warm_seg[3], warm_seg[4])
                else:
                    P3 = warm_seg[4]
                    brown_segs[s] = ('C', warm_seg[1], warm_seg[2],
                                     (P3[0]-new_v[0], P3[1]-new_v[1]), P3)
                SNAP_NOTES.append(
                    f"  snapped handle (seg{s}, {end}): {ang:+.2f}° -> {snap_to:+.1f}°")
            else:
                SNAP_NOTES.append(
                    f"  user-edited handle (seg{s}, {end}): angle {ang:+.2f}°, "
                    f"len {math.hypot(wv[0], wv[1]):.1f}")

# Merge handle locks from persisted set.
for hl in persisted.get("handle_locks", []):
    HANDLE_LOCKED.add((hl[0], hl[1]))
# Merge C1 nodes from persisted set (and from the nodetypes string below).
persisted_c1 = set(persisted.get("c1_nodes", []))

for note in SNAP_NOTES:
    print(note)
print(f"handle-locked: {sorted(HANDLE_LOCKED)}")

# Re-extract theta/w for any segment whose handles were snapped/rewritten,
# so the optimizer's initial state matches the snapped geometry.
for s, seg in enumerate(brown_segs):
    if seg[0] != 'C': continue
    P0, P1, P2, P3 = seg[1], seg[2], seg[3], seg[4]
    theta_out[s] = math.atan2(P1[1]-P0[1], P1[0]-P0[0])
    w_out[s]     = math.hypot(P1[0]-P0[0], P1[1]-P0[1])
    theta_in[s]  = math.atan2(P3[1]-P2[1], P3[0]-P2[0])
    w_in[s]      = math.hypot(P3[0]-P2[0], P3[1]-P2[1])

# Pole-anchor slide: for each pole anchor whose outgoing handle was user-locked,
# infer theta_circle from the locked tangent angle. This slides the anchor
# along its buffer circle so the tangent is geometrically valid (matches the
# circle tangent at the new point), instead of penetrating the buffer.
for i in POLE_ANCHOR:
    seg_out_idx = i   # segment starting at node i
    if (seg_out_idx, 'out') in HANDLE_LOCKED:
        THETA_CIRCLE[i] = theta_from_tangent(i, theta_out[seg_out_idx])
        pos[i][0], pos[i][1] = pole_pos(i, THETA_CIRCLE[i])
        theta_out[seg_out_idx] = pole_tangent(i, THETA_CIRCLE[i])
        print(f"  pole-slide n{i}: theta_circle={math.degrees(THETA_CIRCLE[i]):+.2f}°, "
              f"pos=({pos[i][0]:.3f},{pos[i][1]:.3f}), "
              f"tangent={math.degrees(theta_out[seg_out_idx]):+.2f}°")
    elif i in THETA_CIRCLE:
        # Persisted from prior run — keep position in sync with theta.
        pos[i][0], pos[i][1] = pole_pos(i, THETA_CIRCLE[i])
        theta_out[seg_out_idx] = pole_tangent(i, THETA_CIRCLE[i])

# Default pole-anchor angle if no lock and no persisted theta: south pole (+east).
for i in POLE_ANCHOR:
    if i not in THETA_CIRCLE and (i, 'out') not in HANDLE_LOCKED:
        _, _, _, default_theta, _ = POLE_ANCHOR[i]
        THETA_CIRCLE[i] = default_theta
        pos[i][0], pos[i][1] = pole_pos(i, default_theta)
        theta_out[i] = pole_tangent(i, default_theta)

# Nodes marked 's', 'z', or 'a' in Inkscape nodetypes string are C¹. In my
# parameterization this means theta_out[seg_i] = theta_in[seg_{i-1}] at node i.
# We enforce this by tying theta_out[i] to theta_in[(i-1) % N_SEG] each time
# the objective is evaluated, and NOT scanning theta_out[i] independently.
C1_NODES = set(persisted_c1)
# Nodetypes explicitly set to 'c' by the user override the persisted C1 status.
for i, ch in enumerate(nodetypes[:N_NODES]):
    if ch == 'c':
        C1_NODES.discard(i)
    elif ch in ('s', 'z', 'a'):
        C1_NODES.add(i)
print(f"C1-constrained nodes: {sorted(C1_NODES)}")

# unlocked theta indices per segment (per side)
def theta_out_locked(s):
    # Pole anchors: tangent is derived from theta_circle, not independently scanned.
    if (s % N_NODES) in POLE_ANCHOR:
        return True
    if (s % N_NODES) in C1_NODES:              # C¹-tied to previous
        return True
    if (s, 'out') in HANDLE_LOCKED:            # user-pinned handle
        return True
    return False

def theta_in_locked(s):
    if (s, 'in') in HANDLE_LOCKED:
        return True
    return False

def w_out_locked(s): return (s, 'out') in HANDLE_LOCKED
def w_in_locked(s):  return (s, 'in')  in HANDLE_LOCKED

v0, gap0, worst0 = objective()
print(f"\nInitial: obj={v0:.1f}  area_gap={gap0:.1f}  min_buf_dist={worst0:.3f}")

for pass_idx in range(5):
    scale = 0.5 ** pass_idx
    d_xy    = 30.0 * scale
    d_theta = math.radians(20) * scale

    # theta_circle scan for unlocked pole anchors (slides anchor along buffer).
    for i in POLE_ANCHOR:
        if (i, 'out') in HANDLE_LOCKED:  # locked by user
            continue
        t0 = THETA_CIRCLE[i]
        def set_theta_c(v, i=i):
            THETA_CIRCLE[i] = v
            pos[i][0], pos[i][1] = pole_pos(i, v)
            theta_out[i] = pole_tangent(i, v)
        d_theta_c = math.radians(45) * scale   # full 90° sweep at pass 0
        cd_scan(set_theta_c, t0 - d_theta_c, t0 + d_theta_c, t0)

    # floater (x, y)
    for i in FLOATERS:
        x0 = pos[i][0]
        def setx(v, i=i): pos[i][0] = v
        cd_scan(setx, x0-d_xy, x0+d_xy, x0)
        y0 = pos[i][1]
        def sety(v, i=i): pos[i][1] = v
        cd_scan(sety, y0-d_xy, y0+d_xy, y0)

    # handle widths and angles per tunable segment.
    # Scan window for widths is adaptive: proportional to current w (so a
    # handle that's 150 mm long can scale to 75 or 300 in one pass; a 40 mm
    # handle scans ±20 mm only).
    for s in TUNABLE_SEGS:
        if not theta_out_locked(s):
            t0 = theta_out[s]
            def sett(v, s=s): theta_out[s] = v
            cd_scan(sett, t0-d_theta, t0+d_theta, t0)
        if not w_out_locked(s):
            wo0 = w_out[s]
            d_w = max(15.0, 0.5 * wo0) * scale
            def setwo(v, s=s): w_out[s] = max(W_MIN, v)
            cd_scan(setwo, max(W_MIN, wo0-d_w), wo0+d_w, wo0)
        if not theta_in_locked(s):
            t0 = theta_in[s]
            def sett(v, s=s): theta_in[s] = v
            cd_scan(sett, t0-d_theta, t0+d_theta, t0)
        if not w_in_locked(s):
            wi0 = w_in[s]
            d_w = max(15.0, 0.5 * wi0) * scale
            def setwi(v, s=s): w_in[s] = max(W_MIN, v)
            cd_scan(setwi, max(W_MIN, wi0-d_w), wi0+d_w, wi0)

    v, gap, worst = objective()
    print(f"pass {pass_idx}: obj={v:.1f}  area_gap={gap:.1f}  min_buf_dist={worst:.3f}")


# ---------- emit ----------
Hfinal = rebuild_handles()

def trans(p): return (p[0] - INKSCAPE_DX, p[1] - INKSCAPE_DY)

d_parts = []
P0 = trans(Hfinal[0][1])
d_parts.append(f"M {P0[0]:.3f},{P0[1]:.3f}")
for s in Hfinal:
    if s[0] == 'L':
        q = trans(s[2])
        d_parts.append(f"L {q[0]:.3f},{q[1]:.3f}")
    else:
        t1 = trans(s[2]); t2 = trans(s[3]); t3 = trans(s[4])
        d_parts.append(f"C {t1[0]:.3f},{t1[1]:.3f} {t2[0]:.3f},{t2[1]:.3f} {t3[0]:.3f},{t3[1]:.3f}")
brown_d_new = " ".join(d_parts)

hdr = re.search(r'(<svg\b[^>]*?>)', jc_text, re.S).group(1)
out_parts = [
    '<?xml version="1.0" encoding="UTF-8" standalone="no"?>',
    hdr,
    f'<path d="{brown_d_new}" fill="none" stroke="#8b4513" stroke-width="1.6"/>',
]
for tag in re.findall(r'<circle\b[^/]*/>', jc_text, re.S):
    out_parts.append(tag)
for tag in re.findall(r'<text\b[^<]*</text>', jc_text, re.S):
    out_parts.append(tag)
for tag in re.findall(r'<path[^>]*?stroke="#ff69b4"[^>]*?/>', jc_text, re.S):
    out_parts.append(tag)
out_parts.append("</svg>")

with open(DST, "w") as fh:
    fh.write("\n".join(out_parts))
# Snapshot: subsequent runs diff the DST against this to detect user edits.
import shutil
shutil.copyfile(DST, SNAP)

# Persist locks so every subsequent pass respects every historical user edit.
locks_out = {
    "pinned_nodes": sorted(USER_PINNED),
    "pinned_positions": {str(i): [pos[i][0], pos[i][1]] for i in USER_PINNED},
    "c1_nodes": sorted(C1_NODES),
    "handle_locks": sorted([list(h) for h in HANDLE_LOCKED]),
    "theta_circle": {str(k): v for k, v in THETA_CIRCLE.items()},
}
with open(LOCKS, "w") as fh:
    json.dump(locks_out, fh, indent=2)

print(f"\nwrote {DST}  (snapshot: {SNAP}, locks: {LOCKS})")
print(f"final: area_gap={gap:.1f} mm^2  min_buf_dist={worst:.3f} mm")
print(f"brown signed area: {shoelace(sample_brown(Hfinal)):.1f}   pink: {A_pink:.1f}")
print(f"\nFloater movement from hand-drawn:")
orig = [tuple(n) for n in nodes]
for i in FLOATERS:
    dx = pos[i][0] - orig[i][0]
    dy = pos[i][1] - orig[i][1]
    d  = math.hypot(dx, dy)
    print(f"  n{i}: ({orig[i][0]:8.3f},{orig[i][1]:8.3f}) -> "
          f"({pos[i][0]:8.3f},{pos[i][1]:8.3f})   delta=({dx:+7.3f},{dy:+7.3f})  |d|={d:.3f}")
