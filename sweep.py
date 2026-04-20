"""
sweep.py
========

Speed-dial sweep for the neck outline.  At each speed tier (Schneider
max-error tolerance), fit both legs, render SVG+PNG, and log metrics.

Speed semantics:
  max_err=0.5  => slow  (tight hug, many segments, scalloped)
  max_err=5    => medium
  max_err=50   => fast  (few segments, smooth, racing-line feel)
Larger max_err lets Schneider merge more polyline points per Bezier,
producing a smoother, fewer-noded curve -- but it can also push the
curve inside a buffer at high speeds.  Feasibility is reported per tier;
infeasible tiers are written to the SVG anyway so you can see the
consequence of speeding up past the safe limit.

Outputs (all in project directory):
  erand47_s{N}_e{max_err}.svg, .png    -- one per speed tier
  sweep_metrics.csv                    -- one row per tier
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

R = bh.R_BUFFER
NB = np.array(bh.NB, dtype=float)
NT = np.array(bh.NT, dtype=float)
ST = np.array(bh.ST, dtype=float)
SOUNDBOARD_DIR = np.array(bh._SOUNDBOARD_DIR, dtype=float)


# ---------------------------------------------------------------------------
# Polyline utilities
# ---------------------------------------------------------------------------

def offset_poly(poly, side, offset=0.6):
    off = np.zeros_like(poly)
    for i, P in enumerate(poly):
        if i == 0: tan = poly[1] - poly[0]
        elif i == len(poly)-1: tan = poly[-1] - poly[-2]
        else: tan = poly[i+1] - poly[i-1]
        tan = tan / max(np.linalg.norm(tan), 1e-9)
        nx, ny = -tan[1], tan[0]
        if (side == 'north' and ny > 0) or (side == 'south' and ny < 0):
            nx, ny = -nx, -ny
        off[i] = P + offset * np.array([nx, ny])
    return off


def prepare_leg1_polyline(strings):
    sharps = [s['sharp'] for s in strings if s['has_sharp_buffer']]
    segs = ng.geodesic_outline(NB, ST, sharps, side='south')
    poly = LB.densify(segs, step=1.5, side='south')
    poly = offset_poly(poly, 'south', 0.6)
    poly[0] = NB; poly[-1] = ST
    return poly


def compute_G7fb11(strings):
    G7fb = np.array(strings[-1]['flat_buffer'], dtype=float)
    sb = SOUNDBOARD_DIR
    r_opt1 = np.array([-sb[1], sb[0]])
    r_opt2 = np.array([ sb[1], -sb[0]])
    r_dir = r_opt1 if (r_opt1[0] < 0 and r_opt1[1] < 0) else r_opt2
    return G7fb + R * r_dir


def prepare_leg2_polyline(strings):
    flats = [s['flat_buffer'] for s in reversed(strings) if s['has_flat_buffer']]
    G7fb11 = compute_G7fb11(strings)
    segs = ng.geodesic_outline(G7fb11, NT, flats[1:], side='north')
    poly = LB.densify(segs, step=1.5, side='north')
    poly = offset_poly(poly, 'north', 0.6)
    poly[0] = G7fb11; poly[-1] = NT
    return poly, G7fb11


# ---------------------------------------------------------------------------
# Bezier fitting at a given max_err
# ---------------------------------------------------------------------------

def fit_leg1(poly, max_err):
    """Schneider fit through polyline with natural tangents."""
    left = poly[1] - poly[0]; left /= np.linalg.norm(left)
    right = poly[-2] - poly[-1]; right /= np.linalg.norm(right)
    return bezierfit._fit_cubic(poly, left, right, max_err)


def fit_leg2(poly, G7fb11, max_err, L_g7=40.0):
    """Forced ST->G7fb11 segment + Schneider fit G7fb11->NT."""
    sb = SOUNDBOARD_DIR
    L_st = 2.0 * L_g7
    seg_st = np.array([ST,
                       ST + L_st * sb,
                       G7fb11 + L_g7 * sb,
                       G7fb11])
    left = -sb
    right = np.array([0.0, -1.0])
    rest = bezierfit._fit_cubic(poly, left, right, max_err)
    return [seg_st] + list(rest)


# ---------------------------------------------------------------------------
# Metrics
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


def compute_metrics(beziers, buf_arr, reference_poly):
    path = sample_path(beziers, 40)
    # Min distance from any path sample to any buffer center
    diffs = path[:, None, :] - buf_arr[None, :, :]
    dists = np.linalg.norm(diffs, axis=2)
    min_buf_dist = float(dists.min())
    # Excess over reference: for each path sample, distance to nearest reference polyline segment
    seg_A = reference_poly[:-1]
    seg_B = reference_poly[1:]
    seg_AB = seg_B - seg_A
    L2 = np.sum(seg_AB**2, axis=1); L2 = np.maximum(L2, 1e-9)
    max_excess = 0.0
    for P in path:
        AP = P - seg_A
        t = (AP[:, 0]*seg_AB[:, 0] + AP[:, 1]*seg_AB[:, 1]) / L2
        t = np.clip(t, 0, 1)
        closest = seg_A + t[:, None] * seg_AB
        d = np.linalg.norm(P - closest, axis=1).min()
        if d > max_excess: max_excess = d
    # Bending energy: integral of kappa^2 ds approximated by discrete differences
    # kappa = |dT/ds| where T = unit tangent
    d_pos = np.diff(path, axis=0)
    ds = np.linalg.norm(d_pos, axis=1)
    ds = np.maximum(ds, 1e-9)
    T = d_pos / ds[:, None]
    dT = np.diff(T, axis=0)
    ds_mid = 0.5 * (ds[:-1] + ds[1:])
    kappa2 = np.sum(dT**2, axis=1) / np.maximum(ds_mid, 1e-9)**2
    bending = float(np.sum(kappa2 * ds_mid))
    return {
        'segments': len(beziers),
        'min_buf_dist_mm': round(min_buf_dist, 3),
        'max_excess_mm': round(max_excess, 3),
        'bending_energy': round(bending, 6),
        'infeasible': bool(min_buf_dist < R - 0.05),
    }


# ---------------------------------------------------------------------------
# SVG output
# ---------------------------------------------------------------------------

def beziers_to_d(beziers):
    if not beziers: return ""
    parts = [f"M {beziers[0][0][0]:.3f} {beziers[0][0][1]:.3f}"]
    for _, P1, P2, P3 in beziers:
        parts.append(f"C {P1[0]:.3f} {P1[1]:.3f} "
                     f"{P2[0]:.3f} {P2[1]:.3f} "
                     f"{P3[0]:.3f} {P3[1]:.3f}")
    return " ".join(parts)


def write_svg(segs1, segs2, out_svg):
    d1 = beziers_to_d(segs1)
    d2 = beziers_to_d(segs2)
    d3 = f"M {NT[0]:.3f} {NT[1]:.3f} L {NB[0]:.3f} {NB[1]:.3f}"
    # Start from a fresh build_harp output
    with open(bh.OUTPUT_SVG) as f:
        content = f.read()
    content = re.sub(r'<(path|line|circle)[^>]*"#ff69b4"[^>]*/>\s*', '', content)
    pink = (
        f'<path d="{d1}" fill="none" stroke="#ff69b4" stroke-width="1.6"/>\n'
        f'<path d="{d2}" fill="none" stroke="#ff69b4" stroke-width="1.6"/>\n'
        f'<path d="{d3}" fill="none" stroke="#ff69b4" stroke-width="1.6"/>\n'
    )
    # anchor dots
    anchors = []
    for seg in list(segs1) + list(segs2):
        for pt in (seg[0], seg[3]):
            if not anchors or math.hypot(pt[0]-anchors[-1][0],
                                          pt[1]-anchors[-1][1]) > 0.05:
                anchors.append(pt)
    for pt in anchors:
        pink += f'<circle cx="{pt[0]:.3f}" cy="{pt[1]:.3f}" r="2" fill="#000"/>\n'
    content = content.replace('</svg>', pink + '</svg>')
    with open(out_svg, 'w') as f:
        f.write(content)


def render_png(svg_path, png_path):
    try:
        import subprocess
        subprocess.run(["rsvg-convert", "-w", str(bh.PNG_W), "-h", str(bh.PNG_H),
                        "-o", png_path, svg_path], check=True)
    except Exception as e:
        print(f"PNG render failed for {svg_path}: {e}")


# ---------------------------------------------------------------------------
# Sweep driver
# ---------------------------------------------------------------------------

SPEED_TIERS = [
    ("slow",      0.8),
    ("medslow",   2.0),
    ("medium",    5.0),
    ("medfast",  12.0),
    ("fast",     30.0),
    ("fastest",  80.0),
]


def main():
    strings = bh.build_strings()
    all_buf = []
    for s in strings:
        if s['has_flat_buffer']: all_buf.append(s['flat_buffer'])
        if s['has_sharp_buffer']: all_buf.append(s['sharp'])
    all_buf = np.array(all_buf)

    poly1 = prepare_leg1_polyline(strings)
    poly2, G7fb11 = prepare_leg2_polyline(strings)

    here = os.path.dirname(os.path.abspath(__file__))
    rows = []
    for label, max_err in SPEED_TIERS:
        segs1 = fit_leg1(poly1, max_err)
        segs2 = fit_leg2(poly2, G7fb11, max_err)
        m1 = compute_metrics(segs1, all_buf, poly1)
        m2 = compute_metrics(segs2, all_buf, poly2)
        total = {
            'label': label,
            'max_err': max_err,
            'leg1_segments': m1['segments'],
            'leg2_segments': m2['segments'],
            'total_segments': m1['segments'] + m2['segments'],
            'min_buf_dist_mm': round(min(m1['min_buf_dist_mm'], m2['min_buf_dist_mm']), 3),
            'max_excess_mm': round(max(m1['max_excess_mm'], m2['max_excess_mm']), 3),
            'bending_energy': round(m1['bending_energy'] + m2['bending_energy'], 6),
            'infeasible': m1['infeasible'] or m2['infeasible'],
        }
        rows.append(total)

        tag = f"erand47_{label}_e{max_err:.1f}"
        # Regenerate the fresh SVG for each tier
        import subprocess
        subprocess.run([sys.executable, os.path.join(here, "build_harp.py")],
                       check=True, capture_output=True)
        svg_out = os.path.join(here, f"{tag}.svg")
        png_out = os.path.join(here, f"{tag}.png")
        # Write neck into the fresh SVG, then save as tier-specific file
        write_svg(segs1, segs2, bh.OUTPUT_SVG)
        # Copy the SVG to tier-specific path
        with open(bh.OUTPUT_SVG) as f: content = f.read()
        with open(svg_out, 'w') as f: f.write(content)
        render_png(svg_out, png_out)
        print(f"  {label:>7} max_err={max_err:5.1f}  "
              f"L1 segs={m1['segments']:>3}  L2 segs={m2['segments']:>3}  "
              f"min buf dist={total['min_buf_dist_mm']:6.2f}  "
              f"max excess={total['max_excess_mm']:6.2f}  "
              f"bending={total['bending_energy']:9.4f}  "
              f"{'INFEASIBLE' if total['infeasible'] else 'ok'}")

    csv_path = os.path.join(here, "sweep_metrics.csv")
    with open(csv_path, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows: w.writerow(r)
    print(f"\nWrote {csv_path}")


if __name__ == '__main__':
    main()
