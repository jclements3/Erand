"""
solve_curve_fit.py — solve the two instances of CURVE_FITTING_PROBLEM.md.

Strategy:
  - Parse f anchors from CURVE_FITTING_PROBLEM.md.
  - Parametrize p with 16 numbers (3 interior anchor (x,y), 5 angles, 5 widths).
  - Warm start: sample f at quartile arc-length points, offset normally.
  - Optimize with L-BFGS-B under coarse sampling (fast gradient FD), then a
    final refine under full sampling for area accuracy.
  - Penalty continuation: area + lam * penalty for increasing lam.
  - Multistart on offset side (+/-) and magnitude.
  - Validate with the spec's full sampling (128 per p seg, 64 per f seg)
    before reporting feasible.
"""
import os
import math
import json
import time
import numpy as np
from scipy.optimize import minimize

HERE = os.path.dirname(os.path.abspath(__file__))
SPEC = os.path.join(HERE, "CURVE_FITTING_PROBLEM.md")

W_MIN = 2.0
D_MIN = 0.1
EPS_END = 1.0
# Full spec-required sampling (used for final validation).
N_P_FULL = 128
N_F_FULL = 64
# Coarse sampling for fast optimization.
N_P_OPT = 32
N_F_OPT = 16


# ---------- parsing ----------

def parse_instances(text):
    instances = {}
    current = None
    for line in text.splitlines():
        if line.startswith("INSTANCE 1"):
            current = []
            instances[1] = current
            continue
        if line.startswith("INSTANCE 2"):
            current = []
            instances[2] = current
            continue
        if current is None:
            continue
        parts = line.split()
        if len(parts) < 7:
            if line and line[0].isalpha() and not line[0].isdigit():
                current = None
            continue
        try:
            int(parts[0])
        except ValueError:
            continue
        x, y = float(parts[1]), float(parts[2])
        incoming = None if parts[3] == '-' else (float(parts[3]), float(parts[4]))
        outgoing = None if parts[5] == '-' else (float(parts[5]), float(parts[6]))
        current.append((x, y, incoming, outgoing))
    return instances


def build_f_segments(anchors):
    segs = []
    for i in range(len(anchors) - 1):
        P0 = np.array([anchors[i][0], anchors[i][1]])
        P1 = np.array(anchors[i][3], dtype=float)
        P2 = np.array(anchors[i + 1][2], dtype=float)
        P3 = np.array([anchors[i + 1][0], anchors[i + 1][1]])
        segs.append(np.stack([P0, P1, P2, P3]))
    return segs


# ---------- Bezier utilities ----------

def sample_segment(seg, ts):
    ts = np.asarray(ts).reshape(-1)
    mt = 1.0 - ts
    P0, P1, P2, P3 = seg
    return ((mt ** 3)[:, None] * P0
            + (3 * mt * mt * ts)[:, None] * P1
            + (3 * mt * ts * ts)[:, None] * P2
            + (ts ** 3)[:, None] * P3)


def bezier_deriv(seg, t):
    mt = 1.0 - t
    P0, P1, P2, P3 = seg
    return 3.0 * (mt * mt * (P1 - P0) + 2.0 * mt * t * (P2 - P1) + t * t * (P3 - P2))


def J_seg(seg):
    x0, y0 = seg[0]
    x1, y1 = seg[1]
    x2, y2 = seg[2]
    x3, y3 = seg[3]
    return (1.0 / 20.0) * (
        x0 * (-10.0 * y0 - 6.0 * y1 - 3.0 * y2 - y3)
        + x1 * (6.0 * y0 - 3.0 * y2 - 3.0 * y3)
        + x2 * (3.0 * y0 + 3.0 * y1 - 6.0 * y3)
        + x3 * (y0 + 3.0 * y1 + 6.0 * y2 + 10.0 * y3)
    )


def reverse_seg(seg):
    return np.stack([seg[3], seg[2], seg[1], seg[0]])


# ---------- p construction ----------

def build_p(params, a0, a4):
    a1 = np.array([params[0], params[1]])
    a2 = np.array([params[2], params[3]])
    a3 = np.array([params[4], params[5]])
    anchors = [a0, a1, a2, a3, a4]
    alphas = params[6:11]
    ws = params[11:16]
    segs = []
    for i in range(4):
        P0 = anchors[i]
        P3 = anchors[i + 1]
        d_out = ws[i] * np.array([np.cos(alphas[i]), np.sin(alphas[i])])
        d_in = ws[i + 1] * np.array([np.cos(alphas[i + 1]), np.sin(alphas[i + 1])])
        P1 = P0 + d_out
        P2 = P3 - d_in
        segs.append(np.stack([P0, P1, P2, P3]))
    return segs


# ---------- objective / constraints ----------

def A_signed(p_segs, f_segs_J):
    """f_segs_J is precomputed sum J over f segments."""
    total = f_segs_J
    for seg in reversed(p_segs):
        total += J_seg(reverse_seg(seg))
    return -total


def sum_J_f(f_segs):
    return sum(J_seg(s) for s in f_segs)


def sample_path(segs, n_per_seg):
    ts = np.linspace(0.0, 1.0, n_per_seg)
    all_pts = []
    all_arc = []
    cum = 0.0
    for seg in segs:
        pts = sample_segment(seg, ts)
        diffs = np.diff(pts, axis=0)
        lens = np.linalg.norm(diffs, axis=1)
        cumlens = np.concatenate([[0.0], np.cumsum(lens)])
        all_pts.append(pts)
        all_arc.append(cum + cumlens)
        cum += cumlens[-1]
    return np.vstack(all_pts), np.concatenate(all_arc), cum


def sample_path_with_tangents(segs, n_per_seg):
    ts = np.linspace(0.0, 1.0, n_per_seg)
    all_pts = []
    all_tan = []
    all_arc = []
    cum = 0.0
    for seg in segs:
        pts = sample_segment(seg, ts)
        # Derivative for tangents
        tans = np.array([bezier_deriv(seg, float(t)) for t in ts])
        tnorms = np.linalg.norm(tans, axis=1, keepdims=True)
        tans = tans / np.maximum(tnorms, 1e-9)
        diffs = np.diff(pts, axis=0)
        lens = np.linalg.norm(diffs, axis=1)
        cumlens = np.concatenate([[0.0], np.cumsum(lens)])
        all_pts.append(pts)
        all_tan.append(tans)
        all_arc.append(cum + cumlens)
        cum += cumlens[-1]
    return np.vstack(all_pts), np.vstack(all_tan), np.concatenate(all_arc), cum


def precompute_f_samples(f_segs, n_per_seg):
    f_pts, f_tan, f_arc, f_total = sample_path_with_tangents(f_segs, n_per_seg)
    f_ok = (f_arc >= EPS_END) & (f_total - f_arc >= EPS_END)
    return f_pts[f_ok], f_tan[f_ok], f_total, f_ok


def signed_side_penalty(p_segs, f_ok_pts, f_ok_tan, n_p_per_seg, desired_sign,
                         d_target=None):
    """For each non-endpoint p-sample, find nearest f-sample; compute signed
    perpendicular distance using f's tangent. Require
    desired_sign * signed_d >= d_target (defaults to D_MIN).

    Using d_target > D_MIN during optimization creates a safety buffer so
    the optimizer doesn't oscillate right at the spec's constraint boundary.
    """
    if d_target is None:
        d_target = D_MIN
    p_pts, p_arc, p_total = sample_path(p_segs, n_p_per_seg)
    p_ok = (p_arc >= EPS_END) & (p_total - p_arc >= EPS_END)
    P = p_pts[p_ok]
    if len(P) == 0 or len(f_ok_pts) == 0:
        return 0.0, float('inf')
    diffs = P[:, None, :] - f_ok_pts[None, :, :]
    dists2 = (diffs * diffs).sum(axis=2)
    nearest = dists2.argmin(axis=1)
    dvec = P - f_ok_pts[nearest]
    tan = f_ok_tan[nearest]
    nx = -tan[:, 1]
    ny = tan[:, 0]
    signed_d = dvec[:, 0] * nx + dvec[:, 1] * ny
    violation = d_target - desired_sign * signed_d
    violation_pos = np.maximum(0.0, violation)
    pen = float(np.sum(violation_pos * violation_pos))
    min_signed = float((desired_sign * signed_d).min())
    return pen, min_signed


def symmetric_dist(p_segs, f_ok_pts, n_p_per_seg):
    """Plain minimum Euclidean distance for reporting only."""
    p_pts, p_arc, p_total = sample_path(p_segs, n_p_per_seg)
    p_ok = (p_arc >= EPS_END) & (p_total - p_arc >= EPS_END)
    P = p_pts[p_ok]
    if len(P) == 0 or len(f_ok_pts) == 0:
        return float('inf')
    diffs = P[:, None, :] - f_ok_pts[None, :, :]
    return float(np.sqrt((diffs * diffs).sum(axis=2)).min())


def p_self_intersect_penalty(p_segs, n_per_seg=32, arc_skip=5.0):
    """Penalize any two p-samples with arc-length separation >= arc_skip that
    come within D_MIN of each other. Without this, the |A_signed| objective
    has trivial minima via p self-crossings that cancel signed area.
    arc_skip excludes samples that are close in arc length (the near-neighbor
    false positives); it must be larger than typical handle-length curvature."""
    pts, arc, total = sample_path(p_segs, n_per_seg)
    # Pairwise euclidean & pairwise arc-length
    diffs = pts[:, None, :] - pts[None, :, :]
    dists = np.sqrt((diffs * diffs).sum(axis=2))
    arc_diff = np.abs(arc[:, None] - arc[None, :])
    # Mask: consider pairs with arc-length separation >= arc_skip
    mask = arc_diff >= arc_skip
    if not mask.any():
        return 0.0, float('inf')
    masked_dists = dists[mask]
    min_d = float(masked_dists.min())
    viol = np.maximum(0.0, D_MIN - masked_dists)
    pen = float(np.sum(viol * viol))
    return pen, min_d


def objective(params, a0, a4, f_segs_J, f_ok_pts, f_ok_tan, n_p, pw,
              desired_sign, d_target):
    p_segs = build_p(params, a0, a4)
    area = abs(A_signed(p_segs, f_segs_J))
    pen_f, _ = signed_side_penalty(p_segs, f_ok_pts, f_ok_tan, n_p,
                                    desired_sign, d_target)
    pen_self, _ = p_self_intersect_penalty(p_segs)
    return area + pw * (pen_f + pen_self)


# ---------- initialization ----------

def arclen_table(f_segs, n_per_seg=100):
    pts_list, arcs_list, tslist = [], [], []
    cum = 0.0
    ts = np.linspace(0, 1, n_per_seg)
    for i, seg in enumerate(f_segs):
        pts = sample_segment(seg, ts)
        diffs = np.diff(pts, axis=0)
        lens = np.linalg.norm(diffs, axis=1)
        cumlens = np.concatenate([[0.0], np.cumsum(lens)])
        pts_list.append(pts)
        arcs_list.append(cum + cumlens)
        tslist.extend([(i, float(t)) for t in ts])
        cum += cumlens[-1]
    return np.vstack(pts_list), np.concatenate(arcs_list), tslist, cum


def init_params(f_segs, offset_sign=+1, offset_mag=20.0):
    pts, arcs, tslist, total = arclen_table(f_segs)
    interior = []
    tans = []
    for frac in (0.25, 0.5, 0.75):
        target = frac * total
        k = int(np.searchsorted(arcs, target))
        k = max(0, min(len(tslist) - 1, k))
        seg_idx, t = tslist[k]
        pt = pts[k]
        d = bezier_deriv(f_segs[seg_idx], t)
        tan = d / max(np.linalg.norm(d), 1e-9)
        normal = np.array([-tan[1], tan[0]]) * offset_sign
        interior.append(pt + offset_mag * normal)
        tans.append(tan)
    d0 = bezier_deriv(f_segs[0], 0.0)
    t0 = d0 / np.linalg.norm(d0)
    d4 = bezier_deriv(f_segs[-1], 1.0)
    t4 = d4 / np.linalg.norm(d4)
    angles = [
        math.atan2(t0[1], t0[0]),
        math.atan2(tans[0][1], tans[0][0]),
        math.atan2(tans[1][1], tans[1][0]),
        math.atan2(tans[2][1], tans[2][0]),
        math.atan2(t4[1], t4[0]),
    ]
    seg_len = total / 4.0
    widths = [seg_len / 3.0] * 5
    return np.array([
        interior[0][0], interior[0][1],
        interior[1][0], interior[1][1],
        interior[2][0], interior[2][1],
        *angles,
        *widths,
    ])


# ---------- solver ----------

def solve_instance(f_anchors, label):
    f_segs = build_f_segments(f_anchors)
    a0 = np.array([f_anchors[0][0], f_anchors[0][1]])
    a4 = np.array([f_anchors[-1][0], f_anchors[-1][1]])
    f_segs_J = sum_J_f(f_segs)
    f_ok_pts_opt, f_ok_tan_opt, _, _ = precompute_f_samples(f_segs, N_F_OPT)
    f_ok_pts_full, f_ok_tan_full, _, _ = precompute_f_samples(f_segs, N_F_FULL)
    t_start = time.time()

    best = None
    attempts = []
    bounds = [(None, None)] * 11 + [(W_MIN, 1000.0)] * 5

    # offset_sign == +1 corresponds to initial p on the CCW-normal side of f.
    # The signed_side_penalty uses desired_sign = +offset_sign (same convention).
    for offset_sign in (+1, -1):
        for offset_mag in (15.0, 40.0):
            x0 = init_params(f_segs, offset_sign=offset_sign, offset_mag=offset_mag)
            cur = x0
            desired = float(offset_sign)
            # Margin schedule: wider safety during opt, tighten for validation.
            # d_target schedule gives the optimizer slack so it doesn't oscillate
            # right at the spec's D_MIN=0.1 boundary (where finite-difference
            # gradient noise dominates).
            for pw, d_target in ((1e4, 0.5), (1e6, 0.3), (1e7, 0.2)):
                res = minimize(
                    objective, cur,
                    args=(a0, a4, f_segs_J, f_ok_pts_opt, f_ok_tan_opt, N_P_OPT,
                          pw, desired, d_target),
                    method='L-BFGS-B', bounds=bounds,
                    options={'maxiter': 120, 'ftol': 1e-9, 'gtol': 1e-6},
                )
                cur = res.x
                p_tmp = build_p(cur, a0, a4)
                area_tmp = abs(A_signed(p_tmp, f_segs_J))
                pen_tmp, min_sd = signed_side_penalty(
                    p_tmp, f_ok_pts_opt, f_ok_tan_opt, N_P_OPT, desired, D_MIN
                )
                print(f"  {label} s={offset_sign:+d} m={offset_mag:5.1f} "
                      f"pw={pw:.0e} dt={d_target:.2f}: "
                      f"A={area_tmp:.1f} pen(D_MIN)={pen_tmp:.4f} min_sd={min_sd:.3f}",
                      flush=True)
            # Validate at full sampling with spec D_MIN.
            p_segs = build_p(cur, a0, a4)
            pen, min_sd = signed_side_penalty(
                p_segs, f_ok_pts_full, f_ok_tan_full, N_P_FULL, desired, D_MIN
            )
            min_eucl = symmetric_dist(p_segs, f_ok_pts_full, N_P_FULL)
            pen_self, self_md = p_self_intersect_penalty(p_segs, n_per_seg=64)
            area = abs(A_signed(p_segs, f_segs_J))
            feasible = (pen < 1e-9) and (min_sd >= D_MIN) and (pen_self < 1e-9) and (self_md >= D_MIN)
            attempts.append((offset_sign, offset_mag, area, pen, min_sd, feasible))
            status = "FEAS" if feasible else f"infeas sd={min_sd:.3f} eucl={min_eucl:.3f} self={self_md:.3f}"
            print(f"  {label} s={offset_sign:+d} m={offset_mag:5.1f} FINAL: "
                  f"A={area:14.4f}  pen_f={pen:10.4f} pen_s={pen_self:10.4f}  [{status}]", flush=True)
            if feasible and (best is None or area < best[0]):
                best = (area, cur, p_segs, min_sd)
    print(f"  {label} solve time: {time.time() - t_start:.1f}s", flush=True)
    return best, f_segs, a0, a4, attempts


# ---------- SVG ----------

def bbox_of_controls(f_segs):
    all_pts = np.vstack([seg for seg in f_segs])
    return all_pts.min(axis=0), all_pts.max(axis=0)


def write_svg(path, f_segs, p_segs, A_value):
    mins, maxs = bbox_of_controls(f_segs)
    m = 20.0
    x0, y0 = mins[0] - m, mins[1] - m
    w = (maxs[0] - mins[0]) + 2 * m
    h = (maxs[1] - mins[1]) + 2 * m

    def c(seg):
        return f"C {seg[1][0]:.4f},{seg[1][1]:.4f} {seg[2][0]:.4f},{seg[2][1]:.4f} {seg[3][0]:.4f},{seg[3][1]:.4f}"

    f_d = [f"M {f_segs[0][0][0]:.4f},{f_segs[0][0][1]:.4f}"] + [c(s) for s in f_segs]
    p_d = [f"M {p_segs[0][0][0]:.4f},{p_segs[0][0][1]:.4f}"] + [c(s) for s in p_segs]
    loop_d = list(f_d)
    for s in reversed(p_segs):
        loop_d.append(f"C {s[2][0]:.4f},{s[2][1]:.4f} {s[1][0]:.4f},{s[1][1]:.4f} {s[0][0]:.4f},{s[0][1]:.4f}")
    loop_d.append("Z")

    anchors = [p_segs[0][0]] + [p_segs[i][3] for i in range(4)]
    dots = "\n".join(
        f'  <circle cx="{a[0]:.4f}" cy="{a[1]:.4f}" r="3" fill="#d62728" />'
        for a in anchors
    )
    cap_x = x0 + 5
    cap_y = y0 + 5 + 3

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x0:.4f} {y0:.4f} {w:.4f} {h:.4f}" width="{w:.4f}mm" height="{h:.4f}mm">
  <path d="{' '.join(loop_d)}" fill="#d62728" fill-opacity="0.25" stroke="none" />
  <path d="{' '.join(f_d)}" fill="none" stroke="#1f77b4" stroke-width="1.0" />
  <path d="{' '.join(p_d)}" fill="none" stroke="#d62728" stroke-width="1.0" />
{dots}
  <text x="{cap_x:.4f}" y="{cap_y:.4f}" font-size="3" fill="black">A = {A_value:.6g} mm^2</text>
</svg>
'''
    with open(path, 'w') as fh:
        fh.write(svg)


def print_params(params, area, label):
    print(f"\n=== {label} RESULTS ===")
    print(f"A = {area:.6g} mm^2")
    print(f"anchor 1: x={params[0]:.6f}, y={params[1]:.6f}")
    print(f"anchor 2: x={params[2]:.6f}, y={params[3]:.6f}")
    print(f"anchor 3: x={params[4]:.6f}, y={params[5]:.6f}")
    print(f"angles  a_0={params[6]:.6f}  a_1={params[7]:.6f}  a_2={params[8]:.6f}  "
          f"a_3={params[9]:.6f}  a_4={params[10]:.6f}   (radians)")
    print(f"widths  w_0={params[11]:.6f}  w_1={params[12]:.6f}  w_2={params[13]:.6f}  "
          f"w_3={params[14]:.6f}  w_4={params[15]:.6f}   (mm)")


def main():
    with open(SPEC) as fh:
        text = fh.read()
    instances = parse_instances(text)
    results = {}
    for idx in (1, 2):
        print(f"\n====== Instance {idx} ======", flush=True)
        anchors = instances[idx]
        print(f"f has {len(anchors)} anchors / {len(anchors) - 1} segments.", flush=True)
        best, f_segs, a0, a4, attempts = solve_instance(anchors, f"I{idx}")
        if best is None:
            print(f"Instance {idx}: NO FEASIBLE SOLUTION from any multistart.", flush=True)
            results[idx] = {"status": "infeasible", "attempts": [list(a) for a in attempts]}
            continue
        area, x, p_segs, md = best
        print_params(x, area, f"Instance {idx}")
        svg_path = os.path.join(HERE, f"instance{idx}.svg")
        write_svg(svg_path, f_segs, p_segs, area)
        print(f"Wrote {svg_path}", flush=True)
        results[idx] = {
            "A": area,
            "min_dist_mm": md,
            "params": x.tolist(),
            "attempts": [list(a) for a in attempts],
        }
    with open(os.path.join(HERE, "curve_fit_results.json"), 'w') as fh:
        json.dump(results, fh, indent=2, default=float)
    print("\nDone.", flush=True)


if __name__ == '__main__':
    main()
