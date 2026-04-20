"""
fitneck5.py
===========

Proper constrained nonlinear optimization.

Variables: interior Bezier node positions + tangent angles + handle lengths.
Objective: sum of (closest distance - R) over all buffers — minimize miss
  distance while keeping every buffer kissed or barely missed.
Hard constraints (inequality):
  For each buffer c and each sample point p on the curve: |p - c| >= R
  Corner endpoints fixed at NB/ST/NT
  Corner tangent directions fixed

Solver: scipy.optimize.minimize with method='trust-constr', which honors
inequality constraints properly.
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
NB = np.array(bh.NB)
NT = np.array(bh.NT)
ST = np.array(bh.ST)

N_INTERIOR = 5            # interior Bezier nodes per leg
N_SAMPLES = 30            # samples per segment for constraint eval
MARGIN = 0.1              # safety margin so constraints are slightly beyond R


# ---------------------------------------------------------------------------
# Path construction
# ---------------------------------------------------------------------------

def build_path(x, start_pos, start_tan, end_pos, end_tan):
    """Decode x -> path sample points.
    x layout per interior node: [px, py, tan_angle, handle_len_in, handle_len_out]
    That's 5 numbers per interior node.
    Start and end nodes have fixed positions and tangent directions; handle
    lengths are free (1 per corner).
    
    Full x: [start_hlen_out,
             interior_1: px, py, tan, hl_in, hl_out,
             interior_2: ...,
             ...,
             end_hlen_in]
    """
    # Unpack
    start_hlen_out = x[0]
    end_hlen_in = x[-1]
    interior = []
    for i in range(N_INTERIOR):
        idx = 1 + i * 5
        px = x[idx]; py = x[idx + 1]; ta = x[idx + 2]
        hl_in = x[idx + 3]; hl_out = x[idx + 4]
        interior.append({
            'pos': np.array([px, py]),
            'tan': np.array([math.cos(ta), math.sin(ta)]),
            'hl_in': hl_in,
            'hl_out': hl_out,
        })

    # Build list of nodes
    nodes = [{'pos': start_pos, 'tan': np.array(start_tan),
              'hl_out': start_hlen_out}]
    nodes.extend(interior)
    nodes.append({'pos': end_pos, 'tan': np.array(end_tan),
                  'hl_in': end_hlen_in})

    # Build cubic Bezier segments between consecutive nodes
    segs = []
    for i in range(len(nodes) - 1):
        a = nodes[i]; b = nodes[i + 1]
        P0 = a['pos']
        P3 = b['pos']
        L_out = a.get('hl_out', 0.0)
        L_in = b.get('hl_in', 0.0)
        P1 = P0 + L_out * a['tan']
        P2 = P3 - L_in * b['tan']
        segs.append((P0, P1, P2, P3))

    # Sample path
    pts = []
    for (P0, P1, P2, P3) in segs:
        t = np.linspace(0, 1, N_SAMPLES)
        u = 1 - t
        seg = (u[:, None]**3 * P0 +
               3 * u[:, None]**2 * t[:, None] * P1 +
               3 * u[:, None] * t[:, None]**2 * P2 +
               t[:, None]**3 * P3)
        if pts:
            pts.append(seg[1:])
        else:
            pts.append(seg)
    return np.vstack(pts), segs


# ---------------------------------------------------------------------------
# Objective and constraints
# ---------------------------------------------------------------------------

def make_objective_and_constraints(start_pos, start_tan, end_pos, end_tan, buffers):
    buffers_arr = np.array(buffers)

    def min_distances(x):
        """Return array of shape (N_buffers,): min distance from path to each buffer."""
        path, _ = build_path(x, start_pos, start_tan, end_pos, end_tan)
        # Vectorize: distances from every path sample to every buffer
        # path: (M, 2), buffers_arr: (B, 2)
        diffs = path[:, None, :] - buffers_arr[None, :, :]  # (M, B, 2)
        d = np.linalg.norm(diffs, axis=2)                    # (M, B)
        return d.min(axis=0)                                  # (B,)

    def objective(x):
        d_min = min_distances(x)
        # Sum of outward miss distance only (penetrations constrained separately)
        miss = d_min - R
        # We want to minimize the sum where miss >= 0; for infeasible points
        # objective is still finite (constraints handle feasibility)
        return float(np.sum(np.clip(miss, 0, None)))

    def constraint_fn(x):
        """Each buffer: min_dist - R >= MARGIN. Returns array (B,)."""
        d_min = min_distances(x)
        return d_min - R - MARGIN  # must be >= 0

    return objective, constraint_fn


# ---------------------------------------------------------------------------
# Initial guess
# ---------------------------------------------------------------------------

def make_init(start_pos, start_tan, end_pos, end_tan, buffers, chain, side):
    """Generate FEASIBLE initial guess by placing interior nodes WAY outside
    the buffer cluster so the initial path has zero penetrations. The solver
    pulls them inward under the miss-distance objective, constrained by the
    no-penetration rule."""
    chain = np.array(chain)
    # Find the extent of the buffer cluster
    buf_arr = np.array(buffers)
    # "Outside" direction: south for side='south', north for side='north'
    # Offset = big enough to clear all buffers by a healthy margin
    OUTSIDE_OFFSET = 80.0  # well beyond R=12 and the cluster depth

    # Offset direction per node: push AWAY from buffer chain centroid
    chain_centroid = chain.mean(axis=0)

    init = []
    chord_total = np.linalg.norm(end_pos - start_pos)
    init.append(chord_total / (N_INTERIOR + 1) / 2)  # start handle length

    for k in range(1, N_INTERIOR + 1):
        t = k / (N_INTERIOR + 1)
        idx = int(t * (len(chain) - 1))
        anchor = chain[idx]
        # Offset perpendicular to the chain direction, pushing outside
        if side == 'south':
            pos = np.array([anchor[0], anchor[1] + OUTSIDE_OFFSET])
        else:
            pos = np.array([anchor[0], anchor[1] - OUTSIDE_OFFSET])
        # Initial tangent: direction along the chain
        if idx > 0 and idx < len(chain) - 1:
            tan_vec = chain[idx + 1] - chain[idx - 1]
        else:
            tan_vec = end_pos - start_pos
        tan_angle = math.atan2(tan_vec[1], tan_vec[0])
        hl = chord_total / (N_INTERIOR + 1) / 3
        init.extend([pos[0], pos[1], tan_angle, hl, hl])
    init.append(chord_total / (N_INTERIOR + 1) / 2)
    return np.array(init)


# ---------------------------------------------------------------------------
# Per-leg optimize
# ---------------------------------------------------------------------------

def optimize_leg(start_pos, start_tan, end_pos, end_tan, buffers, chain, side):
    obj, con_fn = make_objective_and_constraints(
        start_pos, start_tan, end_pos, end_tan, buffers
    )
    x0 = make_init(start_pos, start_tan, end_pos, end_tan, buffers, chain, side)

    # Sanity: check initial feasibility
    initial_con = con_fn(x0)
    infeas = np.sum(initial_con < 0)
    print(f"  Initial infeasible constraints: {infeas} / {len(initial_con)}")

    constraint = NonlinearConstraint(con_fn, lb=0, ub=np.inf)

    t0 = time.time()
    result = minimize(
        obj, x0,
        method='trust-constr',
        constraints=[constraint],
        options={'maxiter': 2000, 'verbose': 0, 'xtol': 1e-5, 'gtol': 1e-5},
    )
    t1 = time.time()
    print(f"  Solver: {t1 - t0:.1f}s, iterations: {result.nit}, "
          f"success: {result.success}, fun: {result.fun:.3f}")
    if not result.success:
        print(f"  Message: {result.message}")

    # Check final feasibility
    final_con = con_fn(result.x)
    final_infeas = np.sum(final_con < 0)
    print(f"  Final infeasible constraints: {final_infeas} / {len(final_con)}")

    return result.x


# ---------------------------------------------------------------------------
# SVG output
# ---------------------------------------------------------------------------

def x_to_d(x, start_pos, start_tan, end_pos, end_tan):
    _, segs = build_path(x, start_pos, start_tan, end_pos, end_tan)
    if not segs:
        return ""
    P0 = segs[0][0]
    parts = [f"M {P0[0]:.3f} {P0[1]:.3f}"]
    for (P0, P1, P2, P3) in segs:
        parts.append(f"C {P1[0]:.3f} {P1[1]:.3f} "
                     f"{P2[0]:.3f} {P2[1]:.3f} "
                     f"{P3[0]:.3f} {P3[1]:.3f}")
    return " ".join(parts)


def main():
    strings = bh.build_strings()
    all_buffers = []
    for s in strings:
        if s['has_flat_buffer']:
            all_buffers.append(s['flat_buffer'])
        if s['has_sharp_buffer']:
            all_buffers.append(s['sharp'])

    nb_exit = np.array(bh.HANDLE_CONSTRAINTS['NB']['exit_dir'], dtype=float)
    st_entry = bh.HANDLE_CONSTRAINTS['ST']['entry_dir']
    st_entry_norm = (np.array(st_entry, dtype=float) /
                     np.linalg.norm(st_entry) if st_entry else None)

    st_exit = np.array(bh.HANDLE_CONSTRAINTS['ST']['exit_dir'], dtype=float)
    nt_entry = bh.HANDLE_CONSTRAINTS['NT']['entry_dir']
    nt_entry_norm = (np.array(nt_entry, dtype=float) /
                     np.linalg.norm(nt_entry) if nt_entry else None)

    # ---- Leg 1 ----
    print("Optimizing Leg 1 (NB -> ST south)...")
    sharps = [s['sharp'] for s in strings if s['has_sharp_buffer']]
    # If ST entry tangent isn't set, use direction from last buffer to ST
    if st_entry_norm is None:
        v = ST - np.array(sharps[-1])
        st_entry_norm = v / np.linalg.norm(v)
    x1 = optimize_leg(NB, nb_exit, ST, st_entry_norm, all_buffers, sharps, 'south')

    # ---- Leg 2 ----
    print("Optimizing Leg 2 (ST -> NT north)...")
    flats_rev = [s['flat_buffer'] for s in reversed(strings) if s['has_flat_buffer']]
    if nt_entry_norm is None:
        v = NT - np.array(flats_rev[-1])
        nt_entry_norm = v / np.linalg.norm(v)
    x2 = optimize_leg(ST, st_exit, NT, nt_entry_norm, all_buffers, flats_rev, 'north')

    # ---- Write SVG ----
    d1 = x_to_d(x1, NB, nb_exit, ST, st_entry_norm)
    d2 = x_to_d(x2, ST, st_exit, NT, nt_entry_norm)
    d3 = f"M {NT[0]:.3f} {NT[1]:.3f} L {NB[0]:.3f} {NB[1]:.3f}"

    with open(bh.OUTPUT_SVG) as f:
        content = f.read()
    content = re.sub(r'<(path|line|circle)[^>]*"#ff69b4"[^>]*/>\s*', '', content)
    pink = (
        f'<path d="{d1}" fill="none" stroke="#ff69b4" stroke-width="1.6"/>\n'
        f'<path d="{d2}" fill="none" stroke="#ff69b4" stroke-width="1.6"/>\n'
        f'<path d="{d3}" fill="none" stroke="#ff69b4" stroke-width="1.6"/>\n'
    )
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
