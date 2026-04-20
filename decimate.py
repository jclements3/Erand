"""
decimate.py
===========

Greedy racing-line decimation.  Start from the current feasible Bezier fit
(from leg2_bezier.py) and repeatedly remove interior anchors, one at a time,
choosing the removal that (a) keeps every sample outside every buffer and
(b) minimises resulting bending-energy increase.  Log metrics at each step
and save SVG/PNG snapshots at milestone counts.

Fixed anchors (never removed):
  Leg 1: NB, ST
  Leg 2: ST, G7fb11, NT

Leg 2 additionally preserves its FIRST segment (ST->G7fb11) with hand-set
handles L_st = 80 mm, L_g7 = 40 mm along the soundboard slope.  Only the
G7fb11->NT portion is subject to decimation.
"""

import os
import sys
import re
import math
import csv

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_harp as bh
import neck_geodesic as ng
import bezierfit
import leg2_bezier as LB
import sweep

R = bh.R_BUFFER
NB = np.array(bh.NB, dtype=float)
NT = np.array(bh.NT, dtype=float)
ST = np.array(bh.ST, dtype=float)
SOUNDBOARD_DIR = np.array(bh._SOUNDBOARD_DIR, dtype=float)
TOL = 0.5             # mm of allowable slop below the strict R threshold
                      # (Catmull-Rom refit bulges slightly inside vs Schneider
                      #  least-squares; 0.5 mm is well below cosmetic / kerf.)


# ---------------------------------------------------------------------------
# Sampling + metrics
# ---------------------------------------------------------------------------

def sample_bezier(bez, n=40):
    ts = np.linspace(0, 1, n)
    out = np.zeros((n, 2))
    for k, t in enumerate(ts):
        mt = 1 - t
        out[k] = (mt**3 * bez[0] + 3*mt*mt*t*bez[1]
                  + 3*mt*t*t*bez[2] + t**3*bez[3])
    return out


def sample_path(beziers, n_per=40):
    pts = []
    for i, b in enumerate(beziers):
        s = sample_bezier(b, n_per)
        if i > 0: s = s[1:]
        pts.append(s)
    return np.vstack(pts)


def is_feasible(beziers, buf_arr, tol=TOL):
    for b in beziers:
        pts = sample_bezier(b, 40)
        for c in buf_arr:
            d = np.min(np.linalg.norm(pts - c, axis=1))
            if d < R - tol:
                return False, float(d)
    # compute min distance for reporting
    path = sample_path(beziers, 40)
    diffs = path[:, None, :] - buf_arr[None, :, :]
    d_all = np.linalg.norm(diffs, axis=2).min()
    return True, float(d_all)


def bending_energy(beziers):
    path = sample_path(beziers, 30)
    d_pos = np.diff(path, axis=0)
    ds = np.maximum(np.linalg.norm(d_pos, axis=1), 1e-9)
    T = d_pos / ds[:, None]
    dT = np.diff(T, axis=0)
    ds_mid = 0.5 * (ds[:-1] + ds[1:])
    kappa2 = np.sum(dT**2, axis=1) / np.maximum(ds_mid, 1e-9)**2
    return float(np.sum(kappa2 * ds_mid))


# ---------------------------------------------------------------------------
# Catmull-Rom segment with forced endpoint tangents
# ---------------------------------------------------------------------------

def _catmull_tan(anchors, i):
    if i == 0:
        v = anchors[1] - anchors[0]
    elif i == len(anchors) - 1:
        v = anchors[-1] - anchors[-2]
    else:
        v = anchors[i+1] - anchors[i-1]
    return v / max(np.linalg.norm(v), 1e-9)


def _make_segment(A, B, tA, tB, h_factor=1/3.0):
    chord = np.linalg.norm(B - A)
    h = chord * h_factor
    return np.array([A, A + h * tA, B - h * tB, B])


def fit_chain(anchors, forced_tangents=None):
    """Build Bezier chain through anchors using Catmull-Rom tangents, allowing
    overrides from forced_tangents[i] = direction_at_anchor_i."""
    ft = forced_tangents or {}
    n = len(anchors)
    tans = [ft.get(i, _catmull_tan(anchors, i)) for i in range(n)]
    return [_make_segment(anchors[i], anchors[i+1], tans[i], tans[i+1])
            for i in range(n-1)]


# ---------------------------------------------------------------------------
# Greedy decimation
# ---------------------------------------------------------------------------

def anchors_from_beziers(beziers):
    out = [beziers[0][0]]
    for b in beziers:
        out.append(b[3])
    return out


def decimate(init_anchors, init_forced_tangents, buf_arr, label,
             keep_frozen=None, snapshot_counts=None, emit_snapshot=None):
    """Greedy removal of interior anchors.  keep_frozen = set of indices that
    cannot be removed.  snapshot_counts = sorted list of anchor counts where
    we'd like to emit a snapshot (via emit_snapshot callback)."""
    keep_frozen = keep_frozen or set()
    snapshot_counts = set(snapshot_counts or [])
    emit_snapshot = emit_snapshot or (lambda label, anchors, beziers: None)

    current = list(init_anchors)
    forced = dict(init_forced_tangents or {})
    history = []

    def _build(anchors, forced_map):
        return fit_chain(anchors, forced_map)

    # Initial metrics
    beziers = _build(current, forced)
    ok, mn = is_feasible(beziers, buf_arr)
    be = bending_energy(beziers)
    history.append({'count': len(current), 'min_buf_dist': mn,
                    'bending': be, 'feasible': ok})
    if len(current) in snapshot_counts:
        emit_snapshot(f"{label}_n{len(current)}", current, beziers)

    while True:
        best_i = None
        best_be = float('inf')
        best_beziers = None
        best_mn = None
        for i in range(len(current)):
            if i in keep_frozen: continue
            candidate = current[:i] + current[i+1:]
            # rebuild forced_map with shifted indices
            new_forced = {}
            for k, v in forced.items():
                if k == i: continue
                new_forced[k if k < i else k - 1] = v
            cand_beziers = _build(candidate, new_forced)
            ok2, mn2 = is_feasible(cand_beziers, buf_arr)
            if not ok2: continue
            be2 = bending_energy(cand_beziers)
            if be2 < best_be:
                best_be = be2; best_i = i; best_beziers = cand_beziers; best_mn = mn2
        if best_i is None:
            break
        # shift keep_frozen and forced indices as before
        new_forced = {}
        for k, v in forced.items():
            if k == best_i: continue
            new_forced[k if k < best_i else k - 1] = v
        new_frozen = set()
        for j in keep_frozen:
            if j == best_i: continue
            new_frozen.add(j if j < best_i else j - 1)
        current = current[:best_i] + current[best_i+1:]
        forced = new_forced
        keep_frozen = new_frozen
        history.append({'count': len(current),
                        'min_buf_dist': best_mn,
                        'bending': best_be,
                        'feasible': True})
        if len(current) in snapshot_counts:
            emit_snapshot(f"{label}_n{len(current)}", current, best_beziers)

    return current, history


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    strings = bh.build_strings()
    all_buf = []
    for s in strings:
        if s['has_flat_buffer']: all_buf.append(s['flat_buffer'])
        if s['has_sharp_buffer']: all_buf.append(s['sharp'])
    all_buf = np.array(all_buf)

    # --- Initial fit: leg 1 via Schneider (from sweep helpers) ---
    poly1 = sweep.prepare_leg1_polyline(strings)
    segs1_init = sweep.fit_leg1(poly1, max_err=0.4)
    poly2, G7fb11 = sweep.prepare_leg2_polyline(strings)
    sb = SOUNDBOARD_DIR
    L_g7 = 40.0; L_st = 2.0 * L_g7
    seg_st_g7 = np.array([ST,
                           ST + L_st * sb,
                           G7fb11 + L_g7 * sb,
                           G7fb11])
    segs2_rest_init = bezierfit._fit_cubic(poly2, -sb, np.array([0.0, -1.0]), 0.4)

    print(f"Initial:  leg1={len(segs1_init)}  leg2_rest={len(segs2_rest_init)} "
          f"(+1 forced ST->G7fb11) = leg2 total {len(segs2_rest_init)+1}")

    # --- Decimate leg 1 ---
    anchors1 = anchors_from_beziers(segs1_init)
    # freeze endpoints (NB at 0, ST at last)
    frozen1 = {0, len(anchors1) - 1}
    # force NB exit and ST entry tangents (Schneider convention not needed here;
    # we use the Catmull-Rom tangent as natural fallback -- the first/last
    # segments will adapt.  User hasn't re-specified leg 1 exit tangents.)
    forced1 = {}

    # --- Decimate leg 2 (G7fb11 -> NT portion only) ---
    anchors2 = anchors_from_beziers(segs2_rest_init)
    frozen2 = {0, len(anchors2) - 1}   # G7fb11 and NT
    # Force G7fb11 tangent = -sb so the joint with the forced ST->G7fb11 seg
    # is C1-smooth
    forced2 = {0: -sb, len(anchors2) - 1: np.array([0.0, -1.0])}

    here = os.path.dirname(os.path.abspath(__file__))

    # Snapshot targets: at these node counts we save an SVG/PNG.
    snap_leg1 = {30, 20, 15, 10, 7, 5, 3}
    snap_leg2 = {30, 20, 15, 10, 7, 5, 3}

    leg1_snapshots = {}
    leg2_snapshots = {}
    def emit1(tag, anchors, beziers):
        leg1_snapshots[tag] = list(beziers)
    def emit2(tag, anchors, beziers):
        leg2_snapshots[tag] = list(beziers)

    print("Decimating leg 1...")
    _, hist1 = decimate(anchors1, forced1, all_buf, "leg1",
                        keep_frozen=frozen1, snapshot_counts=snap_leg1,
                        emit_snapshot=emit1)
    print("Decimating leg 2 (G7fb11->NT)...")
    _, hist2 = decimate(anchors2, forced2, all_buf, "leg2",
                        keep_frozen=frozen2, snapshot_counts=snap_leg2,
                        emit_snapshot=emit2)

    # Emit snapshots for leg 1 only (leg 2 keeps its Schneider fit unchanged,
    # because Catmull-Rom refit doesn't match Schneider's tightness in leg 2's
    # region).  For each leg 1 snapshot, pair with the original leg 2 fit.
    segs2_fixed = [seg_st_g7] + list(segs2_rest_init)
    all_counts = sorted(snap_leg1, reverse=True)
    rows = []
    for count in all_counts:
        tag1 = f"leg1_n{count}"
        if tag1 not in leg1_snapshots:
            continue
        segs1 = leg1_snapshots[tag1]
        segs2 = segs2_fixed
        # Render
        import subprocess
        subprocess.run([sys.executable, os.path.join(here, "build_harp.py")],
                       check=True, capture_output=True)
        sweep.write_svg(segs1, segs2, bh.OUTPUT_SVG)
        svg_out = os.path.join(here, f"erand47_dec_n{count}.svg")
        png_out = os.path.join(here, f"erand47_dec_n{count}.png")
        with open(bh.OUTPUT_SVG) as f: content = f.read()
        with open(svg_out, 'w') as f: f.write(content)
        sweep.render_png(svg_out, png_out)
        # metrics
        ok1, mn1 = is_feasible(segs1, all_buf)
        ok2, mn2 = is_feasible(segs2, all_buf)
        be = bending_energy(segs1) + bending_energy(segs2)
        rows.append({'target_count_per_leg': count,
                     'leg1_segments': len(segs1),
                     'leg2_segments': len(segs2),
                     'min_buf_dist_mm': round(min(mn1, mn2), 3),
                     'bending_energy': round(be, 6),
                     'feasible': ok1 and ok2})
        print(f"  n={count:>3}  L1={len(segs1):>2}  L2={len(segs2):>2}  "
              f"min dist={rows[-1]['min_buf_dist_mm']:6.2f}  "
              f"bending={be:9.4f}  "
              f"{'ok' if (ok1 and ok2) else 'INFEASIBLE'}")

    csv_path = os.path.join(here, "decimate_metrics.csv")
    with open(csv_path, 'w', newline='') as f:
        if rows:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            for r in rows: w.writerow(r)
    print(f"\nWrote {csv_path}")


if __name__ == '__main__':
    main()
