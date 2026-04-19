#!/usr/bin/env python3
"""Optimize 5 internal neck-anchor positions so every pin is ≥25 mm from the
cubic-Bezier neck curve, minimizing the excess beyond 25 mm.  Writes
neck_anchors.json for make_svg.py to consume."""
import json, math
import numpy as np
from scipy.optimize import minimize, differential_evolution
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

def build_curve(internal, N=250):
    anchors = [(nkt_x, nkt_y)] + list(internal) + [(sbt_x, sbt_y)]
    def tang(i):
        if i == 0:
            dx = anchors[1][0]-anchors[0][0]; dy = anchors[1][1]-anchors[0][1]
        elif i == len(anchors)-1:
            dx = anchors[i][0]-anchors[i-1][0]; dy = anchors[i][1]-anchors[i-1][1]
        else:
            dx = anchors[i+1][0]-anchors[i-1][0]; dy = anchors[i+1][1]-anchors[i-1][1]
        Ll = math.hypot(dx,dy) or 1.0
        return (dx/Ll, dy/Ll)
    pts = []
    for i in range(len(anchors)-1):
        A = anchors[i]; B = anchors[i+1]
        tA = tang(i); tB = tang(i+1)
        if i == 0: tA = (0.0, -1.0)
        if i+1 == len(anchors)-1:
            sb_dx, sb_dy = -1.0, sb_slope
            sbL = math.hypot(sb_dx, sb_dy)
            tB = (sb_dx/sbL, sb_dy/sbL)
        segL = math.hypot(B[0]-A[0], B[1]-A[1])
        k = segL/3.0
        kA = k*2.0 if i==0 else k
        kB = k*3.0 if i+1==len(anchors)-1 else k
        HA = (A[0]+tA[0]*kA, A[1]+tA[1]*kA)
        HB = (B[0]-tB[0]*kB, B[1]-tB[1]*kB)
        ts = np.linspace(0,1,N)
        mt = 1-ts
        sx = mt**3*A[0]+3*mt*mt*ts*HA[0]+3*mt*ts*ts*HB[0]+ts**3*B[0]
        sy = mt**3*A[1]+3*mt*mt*ts*HA[1]+3*mt*ts*ts*HB[1]+ts**3*B[1]
        for j in range(N): pts.append((sx[j],sy[j]))
    return np.array(pts)

def obj(params):
    internal = [(params[2*i], params[2*i+1]) for i in range(5)]
    xs = [a[0] for a in internal]
    if xs != sorted(xs): return 1e12
    if not all(nkt_x+20 < x < sbt_x-20 for x in xs): return 1e12
    pts = build_curve(internal, N=250)
    tot = 0.0
    for p in pins:
        d = float(np.min(np.hypot(pts[:,0]-p[0], pts[:,1]-p[1])))
        if d < 25.0:
            tot += (25.0 - d)**2 * 5000
        else:
            tot += (d - 25.0)**2
    return tot

print("Building initial seed from pin arc offset by 25 mm along local normal...", flush=True)
# Seed: string #8, 16, 24, 32, 40 pins offset 25mm along local normal
from math import hypot
srows_len = sorted(range(len(strings)),
    key=lambda i: max(strings[i].dxf.start.y,strings[i].dxf.end.y)
                  - min(strings[i].dxf.start.y,strings[i].dxf.end.y))
string_num = {orig:k+1 for k,orig in enumerate(srows_len)}
target = [8,16,24,32,40]
raw = []
for i, L in enumerate(strings):
    if string_num[i] in target:
        raw.append((tx(L.dxf.start.x-0.319),
                    ty(max(L.dxf.start.y,L.dxf.end.y)+1.497),
                    string_num[i]))
raw.sort(key=lambda a: a[0])
seed_pts = []
for i, (px,py,_) in enumerate(raw):
    prv = raw[i-1] if i>0 else raw[0]
    nxt = raw[i+1] if i<len(raw)-1 else raw[-1]
    dx = nxt[0]-prv[0]; dy = nxt[1]-prv[1]
    Lnorm = hypot(dx,dy) or 1.0
    nxu, nyu = dy/Lnorm, -dx/Lnorm
    seed_pts.append((px + 25*nxu, py + 25*nyu))
x0 = []
for (a,b) in seed_pts: x0.extend([a,b])
print(f"Seed objective: {obj(x0):.3f}", flush=True)
res2 = minimize(obj, x0, method='Nelder-Mead',
                options={'xatol':0.1,'fatol':0.05,'maxiter':30000,'adaptive':True})
print(f"NM obj: {res2.fun:.3f}", flush=True)
internal = [(res2.x[2*i], res2.x[2*i+1]) for i in range(5)]
pts = build_curve(internal, N=600)
dists = np.array([float(np.min(np.hypot(pts[:,0]-p[0], pts[:,1]-p[1]))) for p in pins])
print(f"min={dists.min():.3f}  max={dists.max():.3f}  under25={(dists<25).sum()}  mean(d-25)={np.mean(dists-25):.2f}", flush=True)
for i, (nx, ny) in enumerate(internal):
    print(f"  N{i+1} = ({nx:.2f}, {ny:.2f})", flush=True)
with open('/home/james.clements/projects/erand/neck_anchors.json','w') as f:
    json.dump({'anchors':[list(a) for a in internal]}, f, indent=2)
print("Wrote neck_anchors.json", flush=True)
