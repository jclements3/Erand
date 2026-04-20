"""
fitneck7.py
===========

Same Bezier-chain structure as fitneck6, but:
  (A) Feasible warm start.  Interior nodes are initialised by sampling the
      geodesic polyline from neck_geodesic.py -- that polyline is a sequence
      of common tangent lines and circle arcs, so it is outside every buffer
      by construction.  Tangent angles at each warm-start node come from the
      direction of the geodesic at that sample.
  (B) Bilateral objective with a large violation penalty.  Every buffer
      penetration pays  PENALTY * depth^2  in the objective (in addition to
      the existing hard inequality constraint).  This fixes the bug in
      fitneck6 where the objective clipped negative misses to zero, giving
      the solver no gradient to push out of an already-infeasible region.
"""

import math
import os
import re
import sys
import time

import numpy as np
from scipy.optimize import minimize, NonlinearConstraint

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_harp as bh
import neck_geodesic as ng

R = bh.R_BUFFER
NB = np.array(bh.NB, dtype=float)
NT = np.array(bh.NT, dtype=float)
ST = np.array(bh.ST, dtype=float)
SOUNDBOARD_DIR = np.array(bh._SOUNDBOARD_DIR, dtype=float)

N_SAMPLES = 25
PENALTY = 5000.0
FEASIBLE_MARGIN = 0.1   # mm beyond R_BUFFER we consider "safely outside"


# ---------------------------------------------------------------------------
# Bezier helpers (same as fitneck6)
# ---------------------------------------------------------------------------

def cubic_samples(P0, P1, P2, P3, n=N_SAMPLES):
    t = np.linspace(0, 1, n)
    u = 1 - t
    return (u[:, None]**3 * P0
            + 3 * u[:, None]**2 * t[:, None] * P1
            + 3 * u[:, None] * t[:, None]**2 * P2
            + t[:, None]**3 * P3)


def build_segs(nodes):
    segs = []
    for i in range(len(nodes) - 1):
        a = nodes[i]; b = nodes[i + 1]
        P0 = a['pos']; P3 = b['pos']
        P1 = P0 + a['hl_out'] * a['tan_out']
        P2 = P3 - b['hl_in'] * b['tan_in']
        segs.append((P0, P1, P2, P3))
    return segs


def sample_segs(segs):
    all_pts = []
    for i, (P0, P1, P2, P3) in enumerate(segs):
        pts = cubic_samples(P0, P1, P2, P3)
        if i > 0:
            pts = pts[1:]
        all_pts.append(pts)
    return np.vstack(all_pts)


def segs_to_d(segs):
    if not segs:
        return ""
    parts = [f"M {segs[0][0][0]:.3f} {segs[0][0][1]:.3f}"]
    for (P0, P1, P2, P3) in segs:
        parts.append(f"C {P1[0]:.3f} {P1[1]:.3f} "
                     f"{P2[0]:.3f} {P2[1]:.3f} "
                     f"{P3[0]:.3f} {P3[1]:.3f}")
    return " ".join(parts)


# ---------------------------------------------------------------------------
# Geodesic warm-start helpers
# ---------------------------------------------------------------------------

def _geodesic_polyline(start, end, circles, side, step=3.0):
    """Dense polyline along the feasible geodesic outline.  Line segments are
    copied vertex-to-vertex; arcs are tesselated at ~step-mm spacing."""
    segments = ng.geodesic_outline(start, end, circles, side)
    pts = []
    for kind, data in segments:
        if kind == 'line':
            p1, p2 = data
            if not pts:
                pts.append(tuple(p1))
            pts.append(tuple(p2))
        else:  # arc
            C, r, p_s, p_e = data
            a_s = math.atan2(p_s[1] - C[1], p_s[0] - C[0])
            a_e = math.atan2(p_e[1] - C[1], p_e[0] - C[0])
            ccw = (a_e - a_s) % (2 * math.pi)
            cw = (a_s - a_e) % (2 * math.pi)
            mid_ccw_y = C[1] + r * math.sin(a_s + ccw / 2)
            mid_cw_y = C[1] + r * math.sin(a_s - cw / 2)
            if side == 'south':
                delta = ccw if mid_ccw_y > mid_cw_y else -cw
            else:
                delta = ccw if mid_ccw_y < mid_cw_y else -cw
            n_arc = max(2, int(abs(delta) * r / step))
            for k in range(1, n_arc + 1):
                a = a_s + delta * k / n_arc
                pts.append((C[0] + r * math.cos(a), C[1] + r * math.sin(a)))
    # Dedup
    out = [pts[0]]
    for p in pts[1:]:
        if math.hypot(p[0] - out[-1][0], p[1] - out[-1][1]) > 0.1:
            out.append(p)
    return np.array(out)


def _sample_along(polyline, n):
    """Return n equally-spaced samples by arc length, and the tangent direction
    at each sample (unit vector), excluding the first and last endpoints."""
    # cumulative arc length
    d = np.linalg.norm(np.diff(polyline, axis=0), axis=1)
    s = np.concatenate([[0.0], np.cumsum(d)])
    total = s[-1]
    samples = []
    for k in range(1, n + 1):
        target = total * k / (n + 1)
        i = int(np.searchsorted(s, target))
        if i <= 0:
            i = 1
        if i >= len(s):
            i = len(s) - 1
        t = (target - s[i - 1]) / max(s[i] - s[i - 1], 1e-9)
        pt = polyline[i - 1] * (1 - t) + polyline[i] * t
        tangent = polyline[i] - polyline[i - 1]
        tangent /= max(np.linalg.norm(tangent), 1e-9)
        samples.append((pt, tangent))
    return samples


# ---------------------------------------------------------------------------
# Objective / constraint
# ---------------------------------------------------------------------------

def _min_distances(segs, buf_arr):
    path = sample_segs(segs)
    diffs = path[:, None, :] - buf_arr[None, :, :]
    d = np.linalg.norm(diffs, axis=2)
    return d.min(axis=0)


def _objective(segs, buf_arr, penalty=PENALTY):
    d_min = _min_distances(segs, buf_arr)
    miss = d_min - R
    hug = np.sum(np.clip(miss, 0, None))            # positive miss = hug excess
    pen = np.sum(np.clip(-miss, 0, None) ** 2)      # negative miss = penetration
    return hug + penalty * pen


def _constraint(segs, buf_arr):
    return _min_distances(segs, buf_arr) - R - FEASIBLE_MARGIN


# ---------------------------------------------------------------------------
# Leg 1
# ---------------------------------------------------------------------------

def optimize_leg1(all_buffers, sharps, C1sbs, G7sbs):
    N_INTERIOR = 3
    N_VARS = 3 + 5 * N_INTERIOR + 3   # = 21

    buf_arr = np.array(all_buffers)

    def decode(x):
        nb_hl_out = x[0]
        c1_hl_in = x[1]; c1_hl_out = x[2]
        interior = []
        for k in range(N_INTERIOR):
            base = 3 + k * 5
            px = x[base]; py = x[base + 1]; ta = x[base + 2]
            hl_in = x[base + 3]; hl_out = x[base + 4]
            tv = np.array([math.cos(ta), math.sin(ta)])
            interior.append({'pos': np.array([px, py]),
                             'tan_in': tv, 'tan_out': tv,
                             'hl_in': hl_in, 'hl_out': hl_out})
        g7_hl_in = x[3 + 5 * N_INTERIOR]
        g7_hl_out = x[3 + 5 * N_INTERIOR + 1]
        st_hl_in = x[3 + 5 * N_INTERIOR + 2]

        st_entry_vec = ST - G7sbs
        st_entry_dir = st_entry_vec / np.linalg.norm(st_entry_vec)

        nodes = [
            {'pos': NB, 'tan_out': np.array([1.0, 0.0]), 'hl_out': nb_hl_out,
             'tan_in': np.array([0.0, 0.0]), 'hl_in': 0.0},
            {'pos': C1sbs, 'tan_in': np.array([1.0, 0.0]),
             'tan_out': np.array([1.0, 0.0]),
             'hl_in': c1_hl_in, 'hl_out': c1_hl_out},
        ] + interior + [
            {'pos': G7sbs, 'tan_in': np.array([1.0, 0.0]),
             'tan_out': np.array([1.0, 0.0]),
             'hl_in': g7_hl_in, 'hl_out': g7_hl_out},
            {'pos': ST, 'tan_in': st_entry_dir, 'hl_in': st_hl_in,
             'tan_out': np.array([0.0, 0.0]), 'hl_out': 0.0},
        ]
        return build_segs(nodes)

    def obj(x):
        return _objective(decode(x), buf_arr)

    def con(x):
        return _constraint(decode(x), buf_arr)

    # Feasible warm start: 3 samples along the geodesic polyline between C1sbs and G7sbs.
    poly = _geodesic_polyline(C1sbs, G7sbs, sharps, side='south')
    samples = _sample_along(poly, N_INTERIOR)

    x0 = np.zeros(N_VARS)
    x0[0] = 40.0        # NB hl_out
    x0[1] = 30.0        # C1 hl_in
    x0[2] = 30.0        # C1 hl_out
    for k, (pt, tan) in enumerate(samples):
        base = 3 + k * 5
        x0[base] = pt[0]
        x0[base + 1] = pt[1]
        x0[base + 2] = math.atan2(tan[1], tan[0])
        x0[base + 3] = 40.0
        x0[base + 4] = 40.0
    x0[3 + 5 * N_INTERIOR] = 30.0        # g7 hl_in
    x0[3 + 5 * N_INTERIOR + 1] = 30.0    # g7 hl_out
    x0[3 + 5 * N_INTERIOR + 2] = 40.0    # ST hl_in

    init_con = con(x0)
    print(f"  Leg 1 warm-start infeasible: {int(np.sum(init_con < 0))}/{len(init_con)}  "
          f"obj={obj(x0):.3f}")

    constraint = NonlinearConstraint(con, lb=0, ub=np.inf)
    t0 = time.time()
    res = minimize(obj, x0, method='trust-constr',
                   constraints=[constraint],
                   options={'maxiter': 2000, 'verbose': 0,
                            'xtol': 1e-6, 'gtol': 1e-6})
    fc = con(res.x)
    print(f"  Leg 1 solver: {time.time() - t0:.1f}s, iter {res.nit}, "
          f"success={res.success}, fun={res.fun:.3f}, "
          f"infeasible={int(np.sum(fc < 0))}/{len(fc)}")
    return decode(res.x)


# ---------------------------------------------------------------------------
# Leg 2
# ---------------------------------------------------------------------------

def optimize_leg2(all_buffers, flats, G7fbn):
    N_INTERIOR = 3
    N_VARS = 2 + 5 * N_INTERIOR + 1   # = 18

    buf_arr = np.array(all_buffers)

    def decode(x):
        L = x[0]
        g7_hl_out = x[1]
        interior = []
        for k in range(N_INTERIOR):
            base = 2 + k * 5
            px = x[base]; py = x[base + 1]; ta = x[base + 2]
            hl_in = x[base + 3]; hl_out = x[base + 4]
            tv = np.array([math.cos(ta), math.sin(ta)])
            interior.append({'pos': np.array([px, py]),
                             'tan_in': tv, 'tan_out': tv,
                             'hl_in': hl_in, 'hl_out': hl_out})
        nt_hl_in = x[2 + 5 * N_INTERIOR]

        nt_entry_vec = NT - interior[-1]['pos']
        nt_entry_dir = nt_entry_vec / np.linalg.norm(nt_entry_vec)

        nodes = [
            {'pos': ST, 'tan_out': SOUNDBOARD_DIR, 'hl_out': L,
             'tan_in': np.array([0.0, 0.0]), 'hl_in': 0.0},
            {'pos': G7fbn, 'tan_in': SOUNDBOARD_DIR, 'hl_in': L / 2,
             'tan_out': np.array([-1.0, 0.0]), 'hl_out': g7_hl_out},
        ] + interior + [
            {'pos': NT, 'tan_in': nt_entry_dir, 'hl_in': nt_hl_in,
             'tan_out': np.array([0.0, 0.0]), 'hl_out': 0.0},
        ]
        return build_segs(nodes)

    def obj(x):
        return _objective(decode(x), buf_arr)

    def con(x):
        return _constraint(decode(x), buf_arr)

    # Feasible warm start: 3 samples along the geodesic polyline between G7fbn and NT.
    poly = _geodesic_polyline(G7fbn, NT, flats, side='north')
    samples = _sample_along(poly, N_INTERIOR)

    x0 = np.zeros(N_VARS)
    x0[0] = 60.0    # L
    x0[1] = 30.0    # g7 hl_out
    for k, (pt, tan) in enumerate(samples):
        base = 2 + k * 5
        x0[base] = pt[0]
        x0[base + 1] = pt[1]
        x0[base + 2] = math.atan2(tan[1], tan[0])
        x0[base + 3] = 40.0
        x0[base + 4] = 40.0
    x0[2 + 5 * N_INTERIOR] = 40.0

    init_con = con(x0)
    print(f"  Leg 2 warm-start infeasible: {int(np.sum(init_con < 0))}/{len(init_con)}  "
          f"obj={obj(x0):.3f}")

    constraint = NonlinearConstraint(con, lb=0, ub=np.inf)
    t0 = time.time()
    res = minimize(obj, x0, method='trust-constr',
                   constraints=[constraint],
                   options={'maxiter': 2000, 'verbose': 0,
                            'xtol': 1e-6, 'gtol': 1e-6})
    fc = con(res.x)
    print(f"  Leg 2 solver: {time.time() - t0:.1f}s, iter {res.nit}, "
          f"success={res.success}, fun={res.fun:.3f}, "
          f"infeasible={int(np.sum(fc < 0))}/{len(fc)}")
    return decode(res.x)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    strings = bh.build_strings()
    sharps = [s['sharp'] for s in strings if s['has_sharp_buffer']]
    flats = [s['flat_buffer'] for s in reversed(strings) if s['has_flat_buffer']]
    all_buffers = []
    for s in strings:
        if s['has_flat_buffer']: all_buffers.append(s['flat_buffer'])
        if s['has_sharp_buffer']: all_buffers.append(s['sharp'])

    C1_sharp = np.array(strings[0]['sharp'])
    G7_sharp = np.array(strings[-1]['sharp'])
    G7_flat = np.array(strings[-1]['flat_buffer'])
    C1sbs = np.array([C1_sharp[0], C1_sharp[1] + R])
    G7sbs = np.array([G7_sharp[0], G7_sharp[1] + R])
    G7fbn = np.array([G7_flat[0], G7_flat[1] - R])

    print("Optimizing Leg 1 (NB -> C1sbs -> 3 interior -> G7sbs -> ST)...")
    segs1 = optimize_leg1(all_buffers, sharps, C1sbs, G7sbs)

    print("Optimizing Leg 2 (ST -> G7fbn -> 3 interior -> NT)...")
    segs2 = optimize_leg2(all_buffers, flats, G7fbn)

    d1 = segs_to_d(segs1)
    d2 = segs_to_d(segs2)
    d3 = f"M {NT[0]:.3f} {NT[1]:.3f} L {NB[0]:.3f} {NB[1]:.3f}"

    with open(bh.OUTPUT_SVG) as f:
        content = f.read()
    content = re.sub(r'<(path|line|circle)[^>]*"#ff69b4"[^>]*/>\s*', '', content)
    pink = (
        f'<path d="{d1}" fill="none" stroke="#ff69b4" stroke-width="1.6"/>\n'
        f'<path d="{d2}" fill="none" stroke="#ff69b4" stroke-width="1.6"/>\n'
        f'<path d="{d3}" fill="none" stroke="#ff69b4" stroke-width="1.6"/>\n'
    )
    for p, label in [(C1sbs, 'C1sbs'), (G7sbs, 'G7sbs'), (G7fbn, 'G7fbn')]:
        pink += f'<circle cx="{p[0]:.3f}" cy="{p[1]:.3f}" r="2.5" fill="#ff69b4"/>\n'
    content = content.replace('</svg>', pink + '</svg>')
    with open(bh.OUTPUT_SVG, 'w') as f:
        f.write(content)

    try:
        import subprocess
        subprocess.run(["rsvg-convert", "-w", str(bh.PNG_W), "-h", str(bh.PNG_H),
                        "-o", bh.OUTPUT_PNG, bh.OUTPUT_SVG], check=True)
    except Exception as e:
        print(f"PNG render failed: {e}")


if __name__ == '__main__':
    main()
