"""
fitneck8.py
===========

Bezier chain with half-plane corridor constraints derived from the geodesic
polyline.  Much smaller / better-conditioned constraint set than the 76 buffer
inequalities of fitneck6.

Corridor constraint:
  For each leg, the geodesic polyline (from neck_geodesic.py) marks the
  innermost feasible boundary -- the curve tangent-kissing the buffer stack.
  Any point STRICTLY OUTSIDE the geodesic (on the south side for leg 1,
  north side for leg 2) is feasible.

  For each Bezier sample P we compute its signed perpendicular distance to
  the NEAREST geodesic polyline segment.  Sign is positive when P is on
  the outer side.  We require signed_dist >= 0 for every Bezier sample.

Objective (same shape as fitneck6 but on the outer corridor):
  Minimise sum of signed distances -- pulls the Bezier tight onto the
  geodesic (hugging the buffer stack).

Fixed structure and handle constraints identical to fitneck6.
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

N_SAMPLES = 20


# ---------------------------------------------------------------------------
# Bezier
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
    if not segs: return ""
    parts = [f"M {segs[0][0][0]:.3f} {segs[0][0][1]:.3f}"]
    for (P0, P1, P2, P3) in segs:
        parts.append(f"C {P1[0]:.3f} {P1[1]:.3f} "
                     f"{P2[0]:.3f} {P2[1]:.3f} "
                     f"{P3[0]:.3f} {P3[1]:.3f}")
    return " ".join(parts)


# ---------------------------------------------------------------------------
# Geodesic polyline + corridor constraint
# ---------------------------------------------------------------------------

def geodesic_polyline(start, end, circles, side, step=2.0):
    """Dense polyline along the feasible geodesic; arcs tesselated at ~step mm."""
    segments = ng.geodesic_outline(start, end, circles, side)
    pts = []
    for kind, data in segments:
        if kind == 'line':
            p1, p2 = data
            if not pts: pts.append(tuple(p1))
            pts.append(tuple(p2))
        else:
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
    out = [pts[0]]
    for p in pts[1:]:
        if math.hypot(p[0] - out[-1][0], p[1] - out[-1][1]) > 0.1:
            out.append(p)
    return np.array(out)


def corridor_signed_distance(samples, polyline, side):
    """For each sample P, return the signed perpendicular distance to the
    nearest polyline segment, positive on the OUTER side (south for leg 1,
    north for leg 2).  All N_samples returned values must be >= 0 for feasibility.

    Convention: walking along polyline from index 0 to -1, outer side = the
    side whose cross product (segB - segA) x (P - segA) is positive when
    'side' == 'south' (walking bass->treble, outer = south = larger y in SVG
    y-down => cross positive).  For 'north' (polyline goes treble->bass in
    leg 2), outer = north = smaller y; the cross product sign flips with
    reversed walking direction, but since the polyline IS already in that
    walking order, cross positive = outer for both legs."""
    res = np.zeros(len(samples))
    seg_A = polyline[:-1]
    seg_B = polyline[1:]
    seg_AB = seg_B - seg_A               # (N_seg, 2)
    seg_len2 = np.sum(seg_AB ** 2, axis=1)
    seg_len2 = np.maximum(seg_len2, 1e-12)
    for i, P in enumerate(samples):
        AP = P - seg_A                   # (N_seg, 2)
        t = (AP[:, 0] * seg_AB[:, 0] + AP[:, 1] * seg_AB[:, 1]) / seg_len2
        t = np.clip(t, 0.0, 1.0)
        closest = seg_A + t[:, None] * seg_AB
        dist = np.linalg.norm(P - closest, axis=1)
        nearest = int(np.argmin(dist))
        # signed distance via cross product with the nearest segment
        cross = (seg_AB[nearest, 0] * (P[1] - seg_A[nearest, 1])
                 - seg_AB[nearest, 1] * (P[0] - seg_A[nearest, 0]))
        sign = 1.0 if cross >= 0 else -1.0
        res[i] = sign * dist[nearest]
    return res


# ---------------------------------------------------------------------------
# Leg 1
# ---------------------------------------------------------------------------

def optimize_leg1(sharps, C1sbs, G7sbs):
    poly = geodesic_polyline(NB, ST, sharps, 'south')

    N_INTERIOR = 3
    N_VARS = 3 + 5 * N_INTERIOR + 3
    SAMPLE_INIT = [None] * N_INTERIOR

    # Warm-start interior node positions from 3 equally-spaced polyline samples
    d = np.linalg.norm(np.diff(poly, axis=0), axis=1)
    s = np.concatenate([[0.0], np.cumsum(d)])
    total = s[-1]
    for k in range(N_INTERIOR):
        target = total * (k + 1) / (N_INTERIOR + 1)
        i = int(np.searchsorted(s, target))
        i = max(1, min(len(s) - 1, i))
        frac = (target - s[i - 1]) / max(s[i] - s[i - 1], 1e-9)
        pt = poly[i - 1] * (1 - frac) + poly[i] * frac
        tan = poly[i] - poly[i - 1]
        tan /= max(np.linalg.norm(tan), 1e-9)
        SAMPLE_INIT[k] = (pt, tan)

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
        segs = decode(x)
        samples = sample_segs(segs)
        sd = corridor_signed_distance(samples, poly, 'south')
        # Hug: minimise sum of positive signed distances
        return float(np.sum(np.clip(sd, 0, None)))

    def con(x):
        segs = decode(x)
        samples = sample_segs(segs)
        sd = corridor_signed_distance(samples, poly, 'south')
        return sd  # all >= 0 for feasibility

    x0 = np.zeros(N_VARS)
    x0[0] = 40.0; x0[1] = 30.0; x0[2] = 30.0
    for k, (pt, tan) in enumerate(SAMPLE_INIT):
        base = 3 + k * 5
        x0[base] = pt[0]; x0[base + 1] = pt[1]
        x0[base + 2] = math.atan2(tan[1], tan[0])
        x0[base + 3] = 40.0; x0[base + 4] = 40.0
    x0[3 + 5 * N_INTERIOR] = 30.0
    x0[3 + 5 * N_INTERIOR + 1] = 30.0
    x0[3 + 5 * N_INTERIOR + 2] = 40.0

    init_con = con(x0)
    print(f"  Leg 1 warm-start infeasible: {int(np.sum(init_con < 0))}/{len(init_con)}  "
          f"obj={obj(x0):.3f}")

    constraint = NonlinearConstraint(con, lb=0, ub=np.inf)
    t0 = time.time()
    res = minimize(obj, x0, method='trust-constr',
                   constraints=[constraint],
                   options={'maxiter': 1500, 'verbose': 0,
                            'xtol': 1e-6, 'gtol': 1e-6})
    fc = con(res.x)
    print(f"  Leg 1 solver: {time.time() - t0:.1f}s, iter {res.nit}, "
          f"success={res.success}, fun={res.fun:.3f}, "
          f"infeasible={int(np.sum(fc < 0))}/{len(fc)}")
    return decode(res.x)


# ---------------------------------------------------------------------------
# Leg 2
# ---------------------------------------------------------------------------

def optimize_leg2(flats, G7fbn):
    poly = geodesic_polyline(ST, NT, flats, 'north')

    N_INTERIOR = 3
    N_VARS = 2 + 5 * N_INTERIOR + 1
    SAMPLE_INIT = [None] * N_INTERIOR

    d = np.linalg.norm(np.diff(poly, axis=0), axis=1)
    s = np.concatenate([[0.0], np.cumsum(d)])
    total = s[-1]
    for k in range(N_INTERIOR):
        target = total * (k + 1) / (N_INTERIOR + 1)
        i = int(np.searchsorted(s, target))
        i = max(1, min(len(s) - 1, i))
        frac = (target - s[i - 1]) / max(s[i] - s[i - 1], 1e-9)
        pt = poly[i - 1] * (1 - frac) + poly[i] * frac
        tan = poly[i] - poly[i - 1]
        tan /= max(np.linalg.norm(tan), 1e-9)
        SAMPLE_INIT[k] = (pt, tan)

    def decode(x):
        L = x[0]; g7_hl_out = x[1]
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
        segs = decode(x)
        samples = sample_segs(segs)
        sd = corridor_signed_distance(samples, poly, 'north')
        return float(np.sum(np.clip(sd, 0, None)))

    def con(x):
        segs = decode(x)
        samples = sample_segs(segs)
        sd = corridor_signed_distance(samples, poly, 'north')
        return sd

    x0 = np.zeros(N_VARS)
    x0[0] = 60.0; x0[1] = 30.0
    for k, (pt, tan) in enumerate(SAMPLE_INIT):
        base = 2 + k * 5
        x0[base] = pt[0]; x0[base + 1] = pt[1]
        x0[base + 2] = math.atan2(tan[1], tan[0])
        x0[base + 3] = 40.0; x0[base + 4] = 40.0
    x0[2 + 5 * N_INTERIOR] = 40.0

    init_con = con(x0)
    print(f"  Leg 2 warm-start infeasible: {int(np.sum(init_con < 0))}/{len(init_con)}  "
          f"obj={obj(x0):.3f}")

    constraint = NonlinearConstraint(con, lb=0, ub=np.inf)
    t0 = time.time()
    res = minimize(obj, x0, method='trust-constr',
                   constraints=[constraint],
                   options={'maxiter': 1500, 'verbose': 0,
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

    C1_sharp = np.array(strings[0]['sharp'])
    G7_sharp = np.array(strings[-1]['sharp'])
    G7_flat = np.array(strings[-1]['flat_buffer'])
    C1sbs = np.array([C1_sharp[0], C1_sharp[1] + R])
    G7sbs = np.array([G7_sharp[0], G7_sharp[1] + R])
    G7fbn = np.array([G7_flat[0], G7_flat[1] - R])

    print("Leg 1...")
    segs1 = optimize_leg1(sharps, C1sbs, G7sbs)
    print("Leg 2...")
    segs2 = optimize_leg2(flats, G7fbn)

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
