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
NK = 6  # number of internal anchors (more nodes = more flexibility for C²)

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
    H1_MAG = 2.0     # locked: H1 length = 2 * first_seg / 3
    H2_MAG = 1.5     # locked: H2 length = 1.5 * last_seg / 3
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

def obj(params):
    internal = [(params[2*i], params[2*i+1]) for i in range(NK)]
    xs = [a[0] for a in internal]
    if xs != sorted(xs): return 1e12
    if not all(nkt_x+20 < x < sbt_x-20 for x in xs): return 1e12
    pts = sample_spline(internal, N=300)
    if pts is None: return 1e12
    tot = 0.0
    for p in pins:
        d = float(np.min(np.hypot(pts[:,0]-p[0], pts[:,1]-p[1])))
        if d < THRESH:
            tot += (THRESH - d)**2 * 10000
        else:
            tot += (d - THRESH)**2
    return tot

bounds = [(nkt_x+20, sbt_x-20), (50, 650)] * NK
print("DE global search (constrained bounds)...", flush=True)
best = None
for seed_id in [7, 42, 101]:
    resg = differential_evolution(obj, bounds, seed=seed_id, maxiter=300, popsize=30,
                                   tol=0.001, polish=False)
    if best is None or resg.fun < best.fun:
        best = resg
print(f"Best DE obj: {best.fun:.2f}", flush=True)
res = minimize(obj, best.x, method='Nelder-Mead',
               options={'xatol':0.05,'fatol':0.05,'maxiter':50000,'adaptive':True})
print(f"NM obj: {res.fun:.2f}", flush=True)
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
