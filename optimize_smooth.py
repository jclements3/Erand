#!/usr/bin/env python3
"""Optimize 3 internal neck anchors for ≥24 mm pin clearance + SMOOTHNESS.
Adds a bending-energy penalty (integral of |kappa|² * ds) so the curve prefers
low curvature variation (no wobbles, no sharp direction changes)."""
import json, math
import numpy as np
from scipy.optimize import minimize
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
NK = 3

def tang(anc, i):
    if i == 0: dx = anc[1][0]-anc[0][0]; dy = anc[1][1]-anc[0][1]
    elif i == len(anc)-1: dx = anc[i][0]-anc[i-1][0]; dy = anc[i][1]-anc[i-1][1]
    else: dx = anc[i+1][0]-anc[i-1][0]; dy = anc[i+1][1]-anc[i-1][1]
    L = math.hypot(dx,dy) or 1.0
    return (dx/L, dy/L)

def build(internal, N=250):
    anc = [(nkt_x, nkt_y)] + list(internal) + [(sbt_x, sbt_y)]
    seg_len = [math.hypot(anc[i+1][0]-anc[i][0], anc[i+1][1]-anc[i][1])
               for i in range(len(anc)-1)]
    handle_len = []
    for j in range(len(anc)):
        if j == 0: handle_len.append(seg_len[0]/3.0*2.0)
        elif j == len(anc)-1: handle_len.append(seg_len[-1]/3.0*3.0)
        else: handle_len.append((seg_len[j-1]+seg_len[j])/6.0)
    pts = []
    for i in range(len(anc)-1):
        A = anc[i]; B = anc[i+1]
        tA = tang(anc, i); tB = tang(anc, i+1)
        if i == 0: tA = (0.0, -1.0)
        if i+1 == len(anc)-1:
            sb_dx, sb_dy = -1.0, sb_slope
            sbL = math.hypot(sb_dx, sb_dy); tB = (sb_dx/sbL, sb_dy/sbL)
        HA = (A[0]+tA[0]*handle_len[i],   A[1]+tA[1]*handle_len[i])
        HB = (B[0]-tB[0]*handle_len[i+1], B[1]-tB[1]*handle_len[i+1])
        ts = np.linspace(0,1,N)
        mt = 1-ts
        sx = mt**3*A[0]+3*mt*mt*ts*HA[0]+3*mt*ts*ts*HB[0]+ts**3*B[0]
        sy = mt**3*A[1]+3*mt*mt*ts*HA[1]+3*mt*ts*ts*HB[1]+ts**3*B[1]
        for j in range(N): pts.append((sx[j], sy[j]))
    return np.array(pts)

def bending_energy(pts):
    """Integral of |d²P/ds²|² ds along the curve (discrete approximation).
    Measures total 'stress' in the curve — higher = more wiggly/kinky."""
    dx = np.diff(pts[:,0]); dy = np.diff(pts[:,1])
    ds = np.hypot(dx, dy)
    # unit tangents
    T = np.stack([dx/np.maximum(ds, 1e-9), dy/np.maximum(ds, 1e-9)], axis=1)
    # dT between successive points
    dT = np.diff(T, axis=0)
    ds_mid = 0.5 * (ds[:-1] + ds[1:])
    kappa2 = np.sum(dT**2, axis=1) / np.maximum(ds_mid, 1e-9)
    return float(np.sum(kappa2))

def obj(params, smoothness_weight=500.0):
    internal = [(params[2*i], params[2*i+1]) for i in range(NK)]
    xs = [a[0] for a in internal]
    ys = [a[1] for a in internal]
    if xs != sorted(xs): return 1e12
    if not all(nkt_x+20 < x < sbt_x-20 for x in xs): return 1e12
    if not all(0 < y < 700 for y in ys): return 1e12     # keep inside canvas
    pts = build(internal, N=250)
    tot = 0.0
    for p in pins:
        d = float(np.min(np.hypot(pts[:,0]-p[0], pts[:,1]-p[1])))
        if d < THRESH:
            tot += (THRESH - d)**2 * 10000
        else:
            tot += (d - THRESH)**2
    # bending energy
    be = bending_energy(pts)
    return tot + smoothness_weight * be

# Seed from 3-anchor prior solution (last optimization)
seed = [(289.37, 92.07), (370.24, 223.60), (532.64, 508.24)]
x0 = []
for (a,b) in seed: x0 += [a, b]
print(f"Seed objective: {obj(x0):.2f}", flush=True)
res = minimize(obj, x0, method='Nelder-Mead',
               options={'xatol':0.1,'fatol':0.5,'maxiter':50000,'adaptive':True})
print(f"Optimized objective: {res.fun:.2f}", flush=True)
internal = [(res.x[2*i], res.x[2*i+1]) for i in range(NK)]
pts = build(internal, N=800)
dists = np.array([float(np.min(np.hypot(pts[:,0]-p[0], pts[:,1]-p[1]))) for p in pins])
print(f"\nmin d = {dists.min():.3f}   max d = {dists.max():.3f}")
print(f"pins under 24: {(dists<THRESH).sum()}")
print(f"mean(d-24) for d>24: {np.mean((dists-THRESH)[dists>THRESH]):.2f}")
be = bending_energy(pts)
print(f"Bending energy: {be:.6f}")
for i, a in enumerate(internal):
    print(f"  N{i+1} = ({a[0]:.2f}, {a[1]:.2f})")
with open('/home/james.clements/projects/erand/neck_anchors.json','w') as f:
    json.dump({'anchors':[list(a) for a in internal]}, f, indent=2)
print("Wrote neck_anchors.json")
