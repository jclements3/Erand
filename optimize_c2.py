#!/usr/bin/env python3
"""Build a C² (curvature-continuous) clamped cubic spline from NKT through N1..Nk
to SBT, then optimize the Nk positions so every pin is >=24 mm from the curve,
minimizing the excess beyond 24 mm.  Writes neck_anchors.json."""
import json, math
import numpy as np
from scipy.optimize import minimize, differential_evolution
from scipy.interpolate import CubicSpline
import ezdxf

IN = 25.4
doc = ezdxf.readfile('/home/james.clements/projects/erand/erand.dxf')
msp = doc.modelspace()
strings = [L for L in msp.query('LINE')
           if abs(math.degrees(math.atan2(L.dxf.end.y-L.dxf.start.y,
                                           L.dxf.end.x-L.dxf.start.x))-90)<1
           and math.hypot(L.dxf.end.y-L.dxf.start.y,L.dxf.end.x-L.dxf.start.x)>2]
strings.sort(key=lambda L: L.dxf.start.x)
BASS_X_IN = strings[0].dxf.start.x
COL_LEFT_IN = (BASS_X_IN*IN - 50.0 - 39.0) / IN
all_y = [y*IN for L in strings for y in [min(L.dxf.start.y,L.dxf.end.y),
                                         max(L.dxf.start.y,L.dxf.end.y),
                                         max(L.dxf.start.y,L.dxf.end.y)+1.497]]
COL_TOP_IN = (max(all_y) + 60) / IN
xs_all = [L.dxf.start.x for L in strings]
ys_hi = [max(L.dxf.start.y,L.dxf.end.y)+2 for L in strings]
x0c = min(COL_LEFT_IN, min(xs_all)) - 0.5
y1c = max(max(ys_hi), COL_TOP_IN) + 0.5 + 1.0
def tx(xi): return (xi - x0c) * IN
def ty(yi): return (y1c - yi) * IN
bass_r = strings[0]; treble_r = strings[-1]
nkt_x = tx(COL_LEFT_IN); nkt_y = ty(max(bass_r.dxf.start.y, bass_r.dxf.end.y) - 50.0/IN)
SEMITONE_R = 2.0 ** (-1.0/12.0)
treble_yg = min(treble_r.dxf.start.y, treble_r.dxf.end.y)
treble_yf = max(treble_r.dxf.start.y, treble_r.dxf.end.y)
g7_sharp_y = treble_yg + (treble_yf - treble_yg) * SEMITONE_R * SEMITONE_R
bx_in = strings[0].dxf.start.x; by_in = min(strings[0].dxf.start.y,strings[0].dxf.end.y)
tx_in = strings[-1].dxf.start.x; ty_in = min(strings[-1].dxf.start.y,strings[-1].dxf.end.y)
sb_slope = (ty_in - by_in) / (tx_in - bx_in)
x_end = bx_in + (g7_sharp_y - by_in)/sb_slope
sbt_x = tx(x_end); sbt_y = ty(g7_sharp_y)
pins = np.array([(tx(L.dxf.start.x-0.319), ty(max(L.dxf.start.y,L.dxf.end.y)+1.497))
                  for L in strings])

THRESH = 24.0
NK = 4  # internal anchors

# Endpoint tangent DIRECTIONS (unit vectors in SVG coords):
#   NKT: straight UP -> (0, -1)
#   SBT: along soundboard slope, pointing up-right -> (1/|v|, -sb_slope/|v|) reversed
#        Actually the SBT tangent direction here is the direction OF TRAVEL into SBT.
#        We want the curve's tangent at SBT to be along the soundboard.  Using
#        (-1, sb_slope) (lower-left -> upper-right along soundboard).
sbL = math.hypot(1.0, sb_slope)
t_nkt = (0.0, -1.0)
t_sbt = (-1.0/sbL, sb_slope/sbL)

def sample_spline(internal, N=300):
    """C² clamped cubic spline through [NKT, *internal, SBT] parametrized by
    cumulative chord length.  Endpoint tangent MAGNITUDES set so the implicit
    cubic-Bezier handles at NKT and SBT match H1=2x, H2=1.5x of segment_length/3.
    That requires first-derivative magnitude = 2 (for H1) and 1.5 (for H2) in
    chord-length parametrization."""
    pts = [(nkt_x, nkt_y)] + list(internal) + [(sbt_x, sbt_y)]
    pts = np.array(pts)
    segs = np.hypot(np.diff(pts[:,0]), np.diff(pts[:,1]))
    t = np.concatenate([[0], np.cumsum(segs)])
    L_total = t[-1]
    # H1 and H2 LOCKED at 50 mm physical length.  In chord-length parametrization
    # handle length = seg_length * |derivative| / 3, so |derivative| = 3*50/seg_length.
    # H1 and H2 LOCKED at 100 mm physical length (handle = seg * |derivative|/3).
    seg_first = segs[0]; seg_last = segs[-1]
    H1_MAG = 300.0 / seg_first
    H2_MAG = 300.0 / seg_last
    dx_start = t_nkt[0] * H1_MAG
    dy_start = t_nkt[1] * H1_MAG
    dx_end   = t_sbt[0] * H2_MAG
    dy_end   = t_sbt[1] * H2_MAG
    try:
        csx = CubicSpline(t, pts[:,0], bc_type=((1, dx_start), (1, dx_end)))
        csy = CubicSpline(t, pts[:,1], bc_type=((1, dy_start), (1, dy_end)))
    except Exception:
        return None
    ts = np.linspace(0, L_total, N)
    return np.column_stack([csx(ts), csy(ts)])

def curve_y_at_x(pts, px):
    """Linear-interp curve y at given x (assumes monotone x)."""
    i = int(np.searchsorted(pts[:,0], px))
    if i <= 0: return pts[0,1]
    if i >= len(pts): return pts[-1,1]
    x0p, y0p = pts[i-1]; x1p, y1p = pts[i]
    return y0p if x1p == x0p else y0p + (y1p-y0p)*(px-x0p)/(x1p-x0p)

def bending_energy(pts):
    dx = np.diff(pts[:,0]); dy = np.diff(pts[:,1])
    ds = np.hypot(dx, dy)
    T = np.stack([dx/np.maximum(ds,1e-9), dy/np.maximum(ds,1e-9)], axis=1)
    dT = np.diff(T, axis=0)
    ds_mid = 0.5*(ds[:-1]+ds[1:])
    k2 = np.sum(dT**2, axis=1) / np.maximum(ds_mid, 1e-9)
    return float(np.sum(k2))

def obj(params):
    """Objective: minimize the MIN pin-to-curve distance past 24 mm.
    Hard constraints: every pin >=24 mm; every pin on the "above" side of curve."""
    internal = [(params[2*i], params[2*i+1]) for i in range(NK)]
    xs = [a[0] for a in internal]
    ys = [a[1] for a in internal]
    if xs != sorted(xs): return 1e12
    if not all(nkt_x+20 < x < sbt_x-20 for x in xs): return 1e12
    if not all(-50 < y < 700 for y in ys): return 1e12     # sensible Y range
    pts = sample_spline(internal, N=300)
    if pts is None: return 1e12
    dx = np.diff(pts[:,0])
    backup = (-dx[dx<0]).sum()
    mono_pen = backup**2 * 100000
    below_pen = 0.0
    clearance_pen = 0.0
    min_d = 1e9
    for p in pins:
        cy = curve_y_at_x(pts, p[0])
        if cy > p[1]:
            below_pen += (cy - p[1])**2
        d = float(np.min(np.hypot(pts[:,0]-p[0], pts[:,1]-p[1])))
        if d < min_d: min_d = d
        if d < THRESH:
            clearance_pen += (THRESH - d)**2
    # Primary objective: closest pin should be exactly 24 mm (minimize excess
    # above 24 *for the tightest pin*).  Regularize with bending energy to keep
    # curve smooth and prevent runaway-far-away configurations.
    tight = max(0.0, min_d - THRESH)
    be = bending_energy(pts)
    return tight**2 + be * 0.1 + mono_pen + below_pen * 100000 + clearance_pen * 100000

# Smart seed: evenly-spaced stations along the pin arc, each offset 30 mm along the
# local normal (to give the optimizer room above every pin).
def pin_arc_seed_pts(nk, offset=30.0):
    anc = [tuple(p) for p in pins]
    pts_list = []
    for i in range(len(anc)-1):
        A = anc[i]; B = anc[i+1]
        for t in np.linspace(0, 1, 20):
            pts_list.append(((1-t)*A[0]+t*B[0], (1-t)*A[1]+t*B[1]))
    pts_arr = np.array(pts_list)
    ds = np.hypot(np.diff(pts_arr[:,0]), np.diff(pts_arr[:,1]))
    s = np.concatenate([[0], np.cumsum(ds)])
    total = s[-1]
    seeds = []
    for k in range(1, nk+1):
        tgt = total * k / (nk+1)
        idx = int(np.searchsorted(s, tgt))
        if idx <= 0: idx = 1
        if idx >= len(s): idx = len(s)-1
        s0, s1 = s[idx-1], s[idx]
        tt = (tgt-s0)/(s1-s0) if s1>s0 else 0
        bx = pts_arr[idx-1,0]*(1-tt) + pts_arr[idx,0]*tt
        by = pts_arr[idx-1,1]*(1-tt) + pts_arr[idx,1]*tt
        # local normal
        i0 = max(0, idx-5); i1 = min(len(pts_arr)-1, idx+5)
        dx = pts_arr[i1,0]-pts_arr[i0,0]; dy = pts_arr[i1,1]-pts_arr[i0,1]
        L = math.hypot(dx,dy) or 1.0
        nxu, nyu = dy/L, -dx/L
        if nyu > 0: nxu, nyu = -nxu, -nyu   # up-side normal
        seeds.append((bx + offset*nxu, by + offset*nyu))
    return seeds
best = None
for off in [30, 40, 50, 60, 80]:
    seed = pin_arc_seed_pts(NK, offset=off)
    x0 = []
    for (a,b) in seed: x0 += [a, b]
    r = minimize(obj, x0, method='Nelder-Mead',
                 options={'xatol':0.1,'fatol':0.5,'maxiter':20000,'adaptive':True})
    print(f"  seed offset={off}  obj={r.fun:.2f}", flush=True)
    if best is None or r.fun < best.fun:
        best = r
res = best
print(f"Best NM obj: {res.fun:.2f}", flush=True)
internal = [(res.x[2*i], res.x[2*i+1]) for i in range(NK)]
pts = sample_spline(internal, N=1000)
dists = np.array([float(np.min(np.hypot(pts[:,0]-p[0], pts[:,1]-p[1]))) for p in pins])
print(f"min d = {dists.min():.3f}   max d = {dists.max():.3f}")
print(f"pins under 24: {(dists<THRESH).sum()}")
print(f"mean(d-24) for d>24: {np.mean((dists-THRESH)[dists>THRESH]):.2f}")
for i, a in enumerate(internal):
    print(f"  N{i+1} = ({a[0]:.2f}, {a[1]:.2f})")
with open('/home/james.clements/projects/erand/neck_anchors.json','w') as f:
    json.dump({'anchors':[list(a) for a in internal], 'use_c2': True}, f, indent=2)
print("Wrote neck_anchors.json")
