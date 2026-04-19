#!/usr/bin/env python3
"""Compare 2, 3, and 4 internal anchor nodes. For each count, optimize the anchor
positions so every pin is >=24 mm from the Bezier curve, minimizing the delta
beyond 24 mm. Reports which configuration wins."""
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

def make_obj(nK):
    def obj(params):
        internal = [(params[2*i], params[2*i+1]) for i in range(nK)]
        xs = [a[0] for a in internal]
        if xs != sorted(xs): return 1e12
        if not all(nkt_x+20 < x < sbt_x-20 for x in xs): return 1e12
        pts = build(internal, N=250)
        tot = 0.0
        for p in pins:
            d = float(np.min(np.hypot(pts[:,0]-p[0], pts[:,1]-p[1])))
            if d < THRESH:
                tot += (THRESH - d)**2 * 5000   # hard-ish
            else:
                tot += (d - THRESH)**2
        return tot
    return obj

def pin_arc_seed(nK):
    """Seed nK equally-spaced anchors along a Catmull-Rom through all pins,
    offset THRESH mm along local normal."""
    anc = [tuple(p) for p in pins]
    pts = []
    for i in range(len(anc)-1):
        A = anc[i]; B = anc[i+1]
        def tan_here(j):
            if j == 0: dx = anc[1][0]-anc[0][0]; dy = anc[1][1]-anc[0][1]
            elif j == len(anc)-1: dx = anc[j][0]-anc[j-1][0]; dy = anc[j][1]-anc[j-1][1]
            else: dx = anc[j+1][0]-anc[j-1][0]; dy = anc[j+1][1]-anc[j-1][1]
            L = math.hypot(dx,dy) or 1.0
            return (dx/L, dy/L)
        tA = tan_here(i); tB = tan_here(i+1)
        segL = math.hypot(B[0]-A[0], B[1]-A[1]); k = segL/3.0
        HA = (A[0]+tA[0]*k, A[1]+tA[1]*k)
        HB = (B[0]-tB[0]*k, B[1]-tB[1]*k)
        ts = np.linspace(0,1,200); mt = 1-ts
        sx = mt**3*A[0]+3*mt*mt*ts*HA[0]+3*mt*ts*ts*HB[0]+ts**3*B[0]
        sy = mt**3*A[1]+3*mt*mt*ts*HA[1]+3*mt*ts*ts*HB[1]+ts**3*B[1]
        for j in range(200): pts.append((sx[j], sy[j]))
    pts = np.array(pts)
    ds = np.hypot(np.diff(pts[:,0]), np.diff(pts[:,1]))
    s = np.concatenate([[0], np.cumsum(ds)]); total = s[-1]
    seed = []
    for k in range(1, nK+1):
        tgt = total * k / (nK+1)
        idx = int(np.searchsorted(s, tgt))
        if idx <= 0: idx = 1
        if idx >= len(s): idx = len(s)-1
        s0, s1 = s[idx-1], s[idx]
        t = (tgt - s0)/(s1 - s0) if s1>s0 else 0
        bx = pts[idx-1,0]*(1-t) + pts[idx,0]*t
        by = pts[idx-1,1]*(1-t) + pts[idx,1]*t
        # local normal
        i0 = max(0, idx-5); i1 = min(len(pts)-1, idx+5)
        dx = pts[i1,0]-pts[i0,0]; dy = pts[i1,1]-pts[i0,1]
        L = math.hypot(dx,dy) or 1.0
        nxu, nyu = dy/L, -dx/L
        if nyu > 0: nxu, nyu = -nxu, -nyu
        seed.append((bx + THRESH*nxu, by + THRESH*nyu))
    return seed

results = {}
for nK in (2, 3, 4):
    seed = pin_arc_seed(nK)
    x0 = []
    for (a,b) in seed: x0 += [a, b]
    obj = make_obj(nK)
    res = minimize(obj, x0, method='Nelder-Mead',
                   options={'xatol':0.1,'fatol':0.1,'maxiter':30000,'adaptive':True})
    internal = [(res.x[2*i], res.x[2*i+1]) for i in range(nK)]
    pts = build(internal, N=800)
    dists = np.array([float(np.min(np.hypot(pts[:,0]-p[0], pts[:,1]-p[1]))) for p in pins])
    under = (dists < THRESH).sum()
    excess = dists - THRESH
    mean_excess = np.mean(excess[excess>0]) if (excess>0).any() else 0
    max_excess = excess.max()
    sum_sq_excess = np.sum(excess[excess>0]**2)
    results[nK] = {
        'anchors': [list(a) for a in internal],
        'obj': float(res.fun),
        'min_dist': float(dists.min()),
        'max_dist': float(dists.max()),
        'pins_under_24': int(under),
        'mean_excess_above_24': float(mean_excess),
        'max_excess_above_24': float(max_excess),
        'sum_sq_excess': float(sum_sq_excess),
    }
    print(f"\n---- {nK} internal anchors ----")
    print(f"  obj = {res.fun:.2f}")
    print(f"  min d = {dists.min():.2f}   max d = {dists.max():.2f}")
    print(f"  pins under 24 mm: {under}")
    print(f"  mean excess above 24 (over violating): {mean_excess:.2f}")
    print(f"  max  excess above 24: {max_excess:.2f}")
    print(f"  sum (d-24)^2 for d>24: {sum_sq_excess:.1f}")
    for i, a in enumerate(internal):
        print(f"    N{i+1} = ({a[0]:.2f}, {a[1]:.2f})")

print("\n=== Summary ===")
for nK, r in results.items():
    tag = "OK" if r['pins_under_24'] == 0 else f"VIOLATES ({r['pins_under_24']} pins)"
    print(f"  {nK} nodes: mean-excess={r['mean_excess_above_24']:6.2f}  "
          f"max-excess={r['max_excess_above_24']:6.2f}  {tag}")

# Pick best
valid = {n: r for n, r in results.items() if r['pins_under_24'] == 0}
if valid:
    best = min(valid, key=lambda n: valid[n]['mean_excess_above_24'])
    print(f"\nBEST (all pins >=24, min mean-excess): {best} internal anchors")
else:
    best = min(results, key=lambda n: results[n]['pins_under_24'])
    print(f"\nNo config meets the strict constraint. Fewest violations: {best}")

with open('/home/james.clements/projects/erand/neck_compare.json','w') as f:
    json.dump(results, f, indent=2)
print("Wrote neck_compare.json")
