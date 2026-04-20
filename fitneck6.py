"""
fitneck6.py
===========

Final structured Bezier outline.

Leg 1 (one continuous Bezier from NB to ST):
  Anchors:
    N0 = NB (corner, horizontal exit handle)
    N1 = C1sbs (C1 sharp buffer south pole), horizontal tangent
    N2..N4 = 3 interior optimization nodes (free position + tangent angle)
    N5 = G7sbs (G7 sharp buffer south pole), horizontal tangent
    N6 = ST (corner, entry free)

Leg 2 (Bezier from ST to NT):
  Anchors:
    N0 = ST (exit along soundboard slope, length = L)
    N1 = G7fbn (G7 flat buffer north pole), entry handle along soundboard
         slope with length = L/2
    N2..N4 = 3 interior optimization nodes
    N5 = NT (corner, entry free)

Leg 3: NT -> NB straight line.

Hard constraints:
  - No Bezier sample point within R of any buffer center.
  - Corner positions and tangent directions fixed.
  - C1sbs, G7sbs horizontal tangents (direction along chain).
  - G7fbn entry handle parallel to ST exit handle with length = L/2.

Objective: minimize sum of outward miss distances (closest distance from
curve to each buffer, minus R) so the curve hugs the buffer cluster.
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

R = bh.R_BUFFER
NB = np.array(bh.NB, dtype=float)
NT = np.array(bh.NT, dtype=float)
ST = np.array(bh.ST, dtype=float)
SOUNDBOARD_DIR = np.array(bh._SOUNDBOARD_DIR, dtype=float)

N_SAMPLES = 25
OUTSIDE_OFFSET = 80.0


# ---------------------------------------------------------------------------
# Bezier sampling
# ---------------------------------------------------------------------------

def cubic_samples(P0, P1, P2, P3, n=N_SAMPLES):
    t = np.linspace(0, 1, n)
    u = 1 - t
    return (u[:, None]**3 * P0 +
            3 * u[:, None]**2 * t[:, None] * P1 +
            3 * u[:, None] * t[:, None]**2 * P2 +
            t[:, None]**3 * P3)


def build_segs(nodes):
    """nodes: list of dicts with 'pos', 'tan_out' (exit unit vector), 'tan_in' (entry unit vector),
    'hl_out' (exit handle length), 'hl_in' (entry handle length)."""
    segs = []
    for i in range(len(nodes) - 1):
        a = nodes[i]; b = nodes[i + 1]
        P0 = a['pos']
        P3 = b['pos']
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
    P0 = segs[0][0]
    parts = [f"M {P0[0]:.3f} {P0[1]:.3f}"]
    for (P0, P1, P2, P3) in segs:
        parts.append(f"C {P1[0]:.3f} {P1[1]:.3f} "
                     f"{P2[0]:.3f} {P2[1]:.3f} "
                     f"{P3[0]:.3f} {P3[1]:.3f}")
    return " ".join(parts)


# ---------------------------------------------------------------------------
# Leg 1 optimizer
# ---------------------------------------------------------------------------

def optimize_leg1(all_buffers, C1sbs, G7sbs):
    """
    Variables (17 total):
      0:  NB exit handle length
      1:  C1sbs incoming handle length
      2:  C1sbs outgoing handle length
      3,4,5,6,7:  interior node 1 (px, py, tan_angle, hl_in, hl_out)
      8,9,10,11,12:  interior node 2
      13,14,15,16,17:  interior node 3
      18: G7sbs incoming handle length
      19: G7sbs outgoing handle length
      20: ST entry handle length
    """
    N_INTERIOR = 3
    N_VARS = 3 + 5 * N_INTERIOR + 2 + 1  # = 21

    def decode(x):
        nb_hl_out = x[0]
        c1_hl_in = x[1]
        c1_hl_out = x[2]
        interior = []
        for k in range(N_INTERIOR):
            base = 3 + k * 5
            px = x[base]; py = x[base+1]; ta = x[base+2]
            hl_in = x[base+3]; hl_out = x[base+4]
            interior.append({
                'pos': np.array([px, py]),
                'tan_in': np.array([math.cos(ta), math.sin(ta)]),
                'tan_out': np.array([math.cos(ta), math.sin(ta)]),
                'hl_in': hl_in, 'hl_out': hl_out,
            })
        g7_hl_in = x[3 + 5 * N_INTERIOR]
        g7_hl_out = x[3 + 5 * N_INTERIOR + 1]
        st_hl_in = x[3 + 5 * N_INTERIOR + 2]

        # ST entry direction: unconstrained. We'll let it align with 
        # direction from G7sbs toward ST.
        st_entry_vec = ST - G7sbs
        st_entry_dir = st_entry_vec / np.linalg.norm(st_entry_vec)

        nodes = [
            {'pos': NB, 'tan_out': np.array([1.0, 0.0]), 'hl_out': nb_hl_out,
             'tan_in': np.array([0.0, 0.0]), 'hl_in': 0.0},
            {'pos': C1sbs, 'tan_in': np.array([1.0, 0.0]), 'tan_out': np.array([1.0, 0.0]),
             'hl_in': c1_hl_in, 'hl_out': c1_hl_out},
        ]
        nodes.extend(interior)
        nodes.append({
            'pos': G7sbs, 'tan_in': np.array([1.0, 0.0]), 'tan_out': np.array([1.0, 0.0]),
            'hl_in': g7_hl_in, 'hl_out': g7_hl_out,
        })
        nodes.append({
            'pos': ST, 'tan_in': st_entry_dir, 'hl_in': st_hl_in,
            'tan_out': np.array([0.0, 0.0]), 'hl_out': 0.0,
        })
        return build_segs(nodes)

    buf_arr = np.array(all_buffers)

    def min_dists(x):
        segs = decode(x)
        path = sample_segs(segs)
        diffs = path[:, None, :] - buf_arr[None, :, :]
        d = np.linalg.norm(diffs, axis=2)
        return d.min(axis=0)

    def obj(x):
        d_min = min_dists(x)
        miss = d_min - R
        return float(np.sum(np.clip(miss, 0, None)))

    def con(x):
        return min_dists(x) - R - 0.1

    # Initial guess: interior nodes OUTSIDE buffer cluster (south)
    x0 = np.zeros(N_VARS)
    x0[0] = 30.0   # NB hl_out
    x0[1] = 30.0   # c1 hl_in
    x0[2] = 30.0   # c1 hl_out
    mid_x = (C1sbs[0] + G7sbs[0]) / 2
    mid_y = max(C1sbs[1], G7sbs[1]) + OUTSIDE_OFFSET
    # 3 interior nodes evenly spaced between C1sbs and G7sbs, offset south
    for k in range(N_INTERIOR):
        t = (k + 1) / (N_INTERIOR + 1)
        px = C1sbs[0] + t * (G7sbs[0] - C1sbs[0])
        py = max(C1sbs[1], G7sbs[1]) + OUTSIDE_OFFSET
        base = 3 + k * 5
        x0[base] = px
        x0[base+1] = py
        x0[base+2] = 0.0  # horizontal tangent initially
        x0[base+3] = 40.0
        x0[base+4] = 40.0
    x0[3 + 5 * N_INTERIOR] = 30.0     # g7 hl_in
    x0[3 + 5 * N_INTERIOR + 1] = 30.0  # g7 hl_out
    x0[3 + 5 * N_INTERIOR + 2] = 40.0  # ST hl_in

    initial_con = con(x0)
    print(f"  Leg 1 initial infeasible: {int(np.sum(initial_con < 0))}/{len(initial_con)}")

    constraint = NonlinearConstraint(con, lb=0, ub=np.inf)

    t0 = time.time()
    res = minimize(obj, x0, method='trust-constr',
                   constraints=[constraint],
                   options={'maxiter': 2000, 'verbose': 0,
                            'xtol': 1e-5, 'gtol': 1e-5})
    print(f"  Leg 1 solver: {time.time()-t0:.1f}s, iter {res.nit}, "
          f"success={res.success}, fun={res.fun:.3f}")
    final_con = con(res.x)
    print(f"  Leg 1 final infeasible: {int(np.sum(final_con < 0))}/{len(final_con)}")

    return decode(res.x)


# ---------------------------------------------------------------------------
# Leg 2 optimizer
# ---------------------------------------------------------------------------

def optimize_leg2(all_buffers, G7fbn):
    """
    Leg 2: ST -> G7fbn -> 3 interior -> NT

    The key constraint: G7fbn entry handle is parallel to ST exit handle,
    with length = ST_hl_out / 2. So we have ONE free parameter L = ST_hl_out;
    G7fbn.hl_in = L/2 and both directions = soundboard slope.

    Variables:
      0: L (ST exit handle length, also determines G7fbn hl_in = L/2)
      1: G7fbn hl_out
      2..6:   interior 1 (px, py, tan_angle, hl_in, hl_out)
      7..11:  interior 2
      12..16: interior 3
      17: NT hl_in
    """
    N_INTERIOR = 3
    N_VARS = 2 + 5 * N_INTERIOR + 1  # = 18

    def decode(x):
        L = x[0]
        g7_hl_out = x[1]
        interior = []
        for k in range(N_INTERIOR):
            base = 2 + k * 5
            px = x[base]; py = x[base+1]; ta = x[base+2]
            hl_in = x[base+3]; hl_out = x[base+4]
            interior.append({
                'pos': np.array([px, py]),
                'tan_in': np.array([math.cos(ta), math.sin(ta)]),
                'tan_out': np.array([math.cos(ta), math.sin(ta)]),
                'hl_in': hl_in, 'hl_out': hl_out,
            })
        nt_hl_in = x[2 + 5 * N_INTERIOR]

        # NT entry direction: from last interior node toward NT
        nt_entry_vec = NT - interior[-1]['pos']
        nt_entry_dir = nt_entry_vec / np.linalg.norm(nt_entry_vec)

        nodes = [
            {'pos': ST,
             'tan_out': SOUNDBOARD_DIR,    # along soundboard slope
             'hl_out': L,
             'tan_in': np.array([0.0, 0.0]), 'hl_in': 0.0},
            {'pos': G7fbn,
             'tan_in': SOUNDBOARD_DIR,     # parallel to ST handle
             'hl_in': L / 2,                # half the length of ST's handle
             'tan_out': np.array([-1.0, 0.0]),  # leaving heading west (arbitrary init)
             'hl_out': g7_hl_out},
        ]
        nodes.extend(interior)
        nodes.append({
            'pos': NT, 'tan_in': nt_entry_dir, 'hl_in': nt_hl_in,
            'tan_out': np.array([0.0, 0.0]), 'hl_out': 0.0,
        })
        return build_segs(nodes)

    buf_arr = np.array(all_buffers)

    def min_dists(x):
        segs = decode(x)
        path = sample_segs(segs)
        diffs = path[:, None, :] - buf_arr[None, :, :]
        d = np.linalg.norm(diffs, axis=2)
        return d.min(axis=0)

    def obj(x):
        return float(np.sum(np.clip(min_dists(x) - R, 0, None)))

    def con(x):
        return min_dists(x) - R - 0.1

    x0 = np.zeros(N_VARS)
    x0[0] = 60.0   # L = ST handle length
    x0[1] = 30.0   # g7 hl_out
    # 3 interior nodes between G7fbn and NT, offset north
    for k in range(N_INTERIOR):
        t = (k + 1) / (N_INTERIOR + 1)
        px = G7fbn[0] + t * (NT[0] - G7fbn[0])
        py = min(G7fbn[1], NT[1]) - OUTSIDE_OFFSET
        base = 2 + k * 5
        x0[base] = px
        x0[base+1] = py
        x0[base+2] = math.pi  # pointing west
        x0[base+3] = 40.0
        x0[base+4] = 40.0
    x0[2 + 5 * N_INTERIOR] = 40.0  # NT hl_in

    initial_con = con(x0)
    print(f"  Leg 2 initial infeasible: {int(np.sum(initial_con < 0))}/{len(initial_con)}")

    constraint = NonlinearConstraint(con, lb=0, ub=np.inf)
    t0 = time.time()
    res = minimize(obj, x0, method='trust-constr',
                   constraints=[constraint],
                   options={'maxiter': 2000, 'verbose': 0,
                            'xtol': 1e-5, 'gtol': 1e-5})
    print(f"  Leg 2 solver: {time.time()-t0:.1f}s, iter {res.nit}, "
          f"success={res.success}, fun={res.fun:.3f}")
    final_con = con(res.x)
    print(f"  Leg 2 final infeasible: {int(np.sum(final_con < 0))}/{len(final_con)}")

    return decode(res.x)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    strings = bh.build_strings()
    all_buffers = []
    for s in strings:
        if s['has_flat_buffer']:
            all_buffers.append(s['flat_buffer'])
        if s['has_sharp_buffer']:
            all_buffers.append(s['sharp'])

    # Anchor points on buffer edges
    C1_sharp = np.array(strings[0]['sharp'])
    G7_sharp = np.array(strings[-1]['sharp'])
    G7_flat = np.array(strings[-1]['flat_buffer'])
    C1sbs = np.array([C1_sharp[0], C1_sharp[1] + R])  # south pole
    G7sbs = np.array([G7_sharp[0], G7_sharp[1] + R])
    G7fbn = np.array([G7_flat[0], G7_flat[1] - R])    # north pole

    print(f"C1sbs = {C1sbs}")
    print(f"G7sbs = {G7sbs}")
    print(f"G7fbn = {G7fbn}")

    print("Optimizing Leg 1 (NB -> C1sbs -> 3 interior -> G7sbs -> ST)...")
    segs1 = optimize_leg1(all_buffers, C1sbs, G7sbs)

    print("Optimizing Leg 2 (ST -> G7fbn -> 3 interior -> NT)...")
    segs2 = optimize_leg2(all_buffers, G7fbn)

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
    # Mark fixed anchor points
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
