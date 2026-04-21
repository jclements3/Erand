"""
leg2_bezier.py
==============

Replace Leg 2 of the neck outline with a smooth Bezier fit through the
geodesic polyline, keeping Leg 1 (scalloped geodesic) and Leg 3 (straight
column) unchanged.

Strategy:
  1. Run neck_geodesic to get the feasible polyline for Leg 2 (ST -> NT).
  2. Densify the polyline (tesselate arcs).
  3. Fit cubic Beziers through it using Schneider's bezierfit.
  4. Force tangents at ST (soundboard slope) and NT (vertical down the column).
  5. Verify no sample on any fitted Bezier enters a buffer circle; if any
     do, increase max_error tolerance so Schneider subdivides more.
  6. Emit SVG: Leg 1 as geodesic arcs+lines, Leg 2 as Bezier curves, Leg 3
     as straight line.
"""

import math
import os
import re
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_harp as bh
import neck_geodesic as ng
import bezierfit

R = bh.R_BUFFER
NB = np.array(bh.NB, dtype=float)
NT = np.array(bh.NT, dtype=float)
ST = np.array(bh.ST, dtype=float)
SOUNDBOARD_DIR = np.array(bh._SOUNDBOARD_DIR, dtype=float)


def densify(segments, step=2.0, side='north'):
    """Tesselate a geodesic segments list into a dense polyline.
    side='south' => outer = larger y.  side='north' => outer = smaller y."""
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


def bezier_samples(bez, n=40):
    ts = np.linspace(0, 1, n)
    out = np.zeros((n, 2))
    for k, t in enumerate(ts):
        mt = 1 - t
        out[k] = (mt**3 * bez[0] + 3 * mt * mt * t * bez[1]
                  + 3 * mt * t * t * bez[2] + t**3 * bez[3])
    return out


def _all_buffers():
    strings = bh.build_strings()
    all_buf = []
    for s in strings:
        if s['has_flat_buffer']: all_buf.append(s['flat_buffer'])
        if s['has_sharp_buffer']: all_buf.append(s['sharp'])
    return np.array(all_buf)


def _fit_leg(start, end, circles, side, left_tan, right_tan, label):
    all_buf = _all_buffers()
    segs = ng.geodesic_outline(start, end, circles, side=side)
    poly = densify(segs, step=1.5, side=side)
    OFFSET = 0.6
    off = np.zeros_like(poly)
    for i, P in enumerate(poly):
        if i == 0: tan = poly[1] - poly[0]
        elif i == len(poly)-1: tan = poly[-1] - poly[-2]
        else: tan = poly[i+1] - poly[i-1]
        tan = tan / max(np.linalg.norm(tan), 1e-9)
        nx = -tan[1]; ny = tan[0]
        if (side == 'north' and ny > 0) or (side == 'south' and ny < 0):
            nx, ny = -nx, -ny
        off[i] = P + OFFSET * np.array([nx, ny])
    poly = off
    poly[0] = start; poly[-1] = end
    print(f"  {label} polyline: {len(poly)} points")

    # If left_tan is None, use natural direction from polyline
    if left_tan is None:
        v = poly[1] - poly[0]; left_tan = v / np.linalg.norm(v)
    if right_tan is None:
        v = poly[-2] - poly[-1]; right_tan = v / np.linalg.norm(v)

    for max_err in (6.0, 4.0, 2.5, 1.5, 0.8, 0.4):
        beziers = bezierfit._fit_cubic(poly, left_tan, right_tan, max_err)
        violated = False; min_d = np.inf
        for b in beziers:
            pts = bezier_samples(b, 50)
            for c in all_buf:
                d = np.min(np.linalg.norm(pts - c, axis=1))
                if d < min_d: min_d = d
                if d < R - 0.05: violated = True
        print(f"    max_err={max_err}: {len(beziers)} segs, min dist {min_d:.2f}, "
              f"violation={'YES' if violated else 'no'}")
        if not violated:
            return beziers
    return beziers


def fit_leg1():
    """Leg 1 = [Bezier NB->C1sbs] + [Bezier chain C1sbs->ST].

    Symmetric with leg 2. NB->C1sbs is a single hand-built cubic with
    horizontal handles:
      - Tangent at NB         = east (+x), handle length = L_nb = 2 * L_c1
      - Tangent at C1sbs      = east (+x), handle length = L_c1
    C1sbs = south pole of the bass-most sharp buffer (the one whose south
    pole sits on y = NB[1], so the tangent line from NB is horizontal).
    Both anchors are at y = NB[1], so the segment is a straight horizontal
    line; the handles just set the Bezier's parameterization.

    After C1sbs the rest of Leg 1 is a Schneider fit through the remaining
    sharp buffers, with left_tangent locked to +x (continuing horizontally).
    """
    strings = bh.build_strings()
    sharps_all = [s['sharp'] for s in strings if s['has_sharp_buffer']]
    # First (bass-most) sharp buffer — its south pole defines NB's y.
    first_sharp = np.array(sharps_all[0], dtype=float)
    C1sbs = np.array([first_sharp[0], NB[1]], dtype=float)

    L_c1 = 40.0               # C1sbs entry handle
    L_nb = 2.0 * L_c1         # NB exit handle (mirrors L_st = 2*L_g7)
    east = np.array([1.0, 0.0])
    P0 = np.array(NB, dtype=float)
    P1 = P0 + L_nb * east
    P2 = C1sbs - L_c1 * east  # incoming tangent at C1sbs = +east
    P3 = C1sbs
    seg_nb_c1 = np.array([P0, P1, P2, P3])

    # Rest of leg 1: C1sbs -> ST, excluding the first sharp from the chain
    # (its tangency is already handled by the hand-built segment above).
    sharps_rest = sharps_all[1:]
    beziers_rest = _fit_leg(C1sbs, ST, sharps_rest, 'south',
                            east, None, "Leg 1 (C1sbs->ST)")
    return [seg_nb_c1] + list(beziers_rest)


def fit_leg2():
    """Leg 2 = [Bezier ST->G7fb11] + [Bezier chain G7fb11->NT].
    ST->G7fb11 segment is a single cubic Bezier with hand-set handles:
      - Tangent at ST  = SOUNDBOARD_DIR, handle length = 2*L (the ST exit handle)
      - Tangent at G7fb11 = SOUNDBOARD_DIR, handle length = L (the G7fb11 inbound)
    G7fb11 is the point on the G7 flat buffer where tangent to the circle
    is parallel to the soundboard slope, on the upper-left (~11 o'clock) side.
    Then the rest of leg 2 is a Schneider fit from G7fb11 to NT with the
    left_tangent locked to SOUNDBOARD_DIR."""
    strings = bh.build_strings()
    flats = [s['flat_buffer'] for s in reversed(strings) if s['has_flat_buffer']]
    all_buf = []
    for s in strings:
        if s['has_flat_buffer']: all_buf.append(s['flat_buffer'])
        if s['has_sharp_buffer']: all_buf.append(s['sharp'])
    all_buf = np.array(all_buf)

    # G7fb 11-o'clock: point on G7 flat buffer where circle tangent == soundboard_dir
    # (radius direction perpendicular to soundboard_dir, on upper-left side).
    G7fb = np.array(strings[-1]['flat_buffer'], dtype=float)
    sb = SOUNDBOARD_DIR
    # Two perpendicular radius options: (-sb.y, sb.x) and (sb.y, -sb.x). Pick
    # the one pointing toward upper-left of center (both components negative
    # in SVG y-down means up-left).
    r_opt1 = np.array([-sb[1], sb[0]])
    r_opt2 = np.array([ sb[1], -sb[0]])
    r_dir = r_opt1 if (r_opt1[0] < 0 and r_opt1[1] < 0) else r_opt2
    G7fb11 = G7fb + R * r_dir

    # --- First segment: ST -> G7fb11 with forced handles ---
    # ST exit handle = +sb (UP-RIGHT, along soundboard extension past ST).
    # G7fb10 handle = +sb from G7fb11 so tangent at G7fb11 = -sb, matching the
    # circle's natural tangent at the 10-o'clock position when traversed
    # from ST-side to NT-side on the north face of the circle.
    L_g7 = 40.0            # G7fb entry handle (reverted to the "better" length)
    L_st = 2.0 * L_g7      # ST exit handle = 2 * G7fb entry = 80
    P0 = ST
    P1 = ST + L_st * sb          # UP-RIGHT from ST
    P2 = G7fb11 + L_g7 * sb      # UP-RIGHT from G7fb11 (tangent at G7fb11 = -sb)
    P3 = G7fb11
    seg_st_g7 = np.array([P0, P1, P2, P3])

    # --- Rest of leg 2: G7fb11 -> NT using Schneider ---
    segs = ng.geodesic_outline(G7fb11, NT, flats[1:], side='north')   # skip G7fb itself
    poly = densify(segs, step=1.5, side='north')
    # Offset the polyline 0.6 mm outward (north = smaller SVG y) along the
    # local normal so Bezier corner-cutting has headroom and won't graze
    # into any buffer circle.
    OFFSET = 0.6
    off = np.zeros_like(poly)
    for i, P in enumerate(poly):
        if i == 0:
            tan = poly[1] - poly[0]
        elif i == len(poly) - 1:
            tan = poly[-1] - poly[-2]
        else:
            tan = poly[i + 1] - poly[i - 1]
        tan = tan / max(np.linalg.norm(tan), 1e-9)
        # Outer normal on the north side: rotate tangent -90 deg (cross with +z)
        # In SVG y-down, (tx, ty) -> (ty, -tx) is right-hand turn.  North is
        # smaller y, i.e., negative y offset from the tangent's perpendicular.
        # Walking ST->NT is LEFT in x (tan has -x component); right-hand
        # perp of (-1, 0) is (0, 1) = south.  So we need the LEFT-hand perp
        # = (-ty, tx).
        nx = -tan[1]; ny = tan[0]
        # Verify it points "north" (smaller y in SVG); if not, flip.
        if ny > 0:
            nx, ny = -nx, -ny
        off[i] = P + OFFSET * np.array([nx, ny])
    poly = off
    # Preserve the true endpoints (G7fb11 and NT) exactly for the Schneider fit.
    poly[0] = G7fb11
    poly[-1] = NT
    print(f"Leg 2 (G7fb11 -> NT) polyline: {len(poly)} points (offset {OFFSET} mm outward)")

    # Tangent at G7fb11: LOCKED to -soundboard_dir (continuing the tangent from
    # the ST->G7fb11 segment in the direction of travel).
    left_tangent = -sb
    # Tangent at NT: leg 2 arrives heading DOWN the column.
    right_tangent = np.array([0.0, -1.0])

    # Try tightening tolerance until no buffer violations.
    for max_err in (6.0, 4.0, 2.5, 1.5, 0.8):
        beziers = bezierfit._fit_cubic(poly, left_tangent, right_tangent, max_err)
        violated = False
        min_d = np.inf
        for b in beziers:
            pts = bezier_samples(b, 50)
            for c in all_buf:
                d = np.min(np.linalg.norm(pts - c, axis=1))
                if d < min_d: min_d = d
                if d < R - 0.05:
                    violated = True
        print(f"  max_err={max_err}: {len(beziers)} segments, "
              f"min pin-dist={min_d:.2f} mm, violation={'YES' if violated else 'no'}")
        if not violated:
            return [seg_st_g7] + list(beziers)
    return [seg_st_g7] + list(beziers)


def beziers_to_d(beziers):
    if not beziers: return ""
    P0 = beziers[0][0]
    parts = [f"M {P0[0]:.3f} {P0[1]:.3f}"]
    for _, P1, P2, P3 in beziers:
        parts.append(f"C {P1[0]:.3f} {P1[1]:.3f} "
                     f"{P2[0]:.3f} {P2[1]:.3f} "
                     f"{P3[0]:.3f} {P3[1]:.3f}")
    return " ".join(parts)


def main():
    # Leg 1: Bezier fit (smoothed geodesic).
    print("Leg 1:")
    beziers1 = fit_leg1()
    d1 = beziers_to_d(beziers1)

    # Leg 2: Bezier fit.
    print("Leg 2:")
    beziers2 = fit_leg2()
    d2 = beziers_to_d(beziers2)

    # Leg 3: column straight.
    d3 = f"M {NT[0]:.3f} {NT[1]:.3f} L {NB[0]:.3f} {NB[1]:.3f}"

    with open(bh.OUTPUT_SVG) as f:
        content = f.read()
    content = re.sub(r'<(path|line|circle)[^>]*"#ff69b4"[^>]*/>\s*', '', content)
    pink = (
        f'<path d="{d1}" fill="none" stroke="#ff69b4" stroke-width="1.6"/>\n'
        f'<path d="{d2}" fill="none" stroke="#ff69b4" stroke-width="1.6"/>\n'
        f'<path d="{d3}" fill="none" stroke="#ff69b4" stroke-width="1.6"/>\n'
    )
    BEZ = '#1060d0'
    # Combine both legs for handle/anchor rendering.  Skip endpoint-tangent
    # handles at each leg's endpoints (those are tangent artifacts).
    def _emit_handles(beziers, show_first_P1=False, show_last_P2=False):
        out = ""
        for i, seg in enumerate(beziers):
            P0, P1, P2, P3 = seg
            show_P1 = (i != 0) or show_first_P1
            show_P2 = (i != len(beziers) - 1) or show_last_P2
            if show_P1:
                out += (
                    f'<line x1="{P0[0]:.3f}" y1="{P0[1]:.3f}" '
                    f'x2="{P1[0]:.3f}" y2="{P1[1]:.3f}" '
                    f'stroke="{BEZ}" stroke-width="0.5" stroke-dasharray="2,1.5"/>\n'
                    f'<circle cx="{P1[0]:.3f}" cy="{P1[1]:.3f}" r="1.6" '
                    f'fill="#fff" stroke="{BEZ}" stroke-width="0.6"/>\n'
                )
            if show_P2:
                out += (
                    f'<line x1="{P3[0]:.3f}" y1="{P3[1]:.3f}" '
                    f'x2="{P2[0]:.3f}" y2="{P2[1]:.3f}" '
                    f'stroke="{BEZ}" stroke-width="0.5" stroke-dasharray="2,1.5"/>\n'
                    f'<circle cx="{P2[0]:.3f}" cy="{P2[1]:.3f}" r="1.6" '
                    f'fill="#fff" stroke="{BEZ}" stroke-width="0.6"/>\n'
                )
        return out
    pink += _emit_handles(beziers1, show_first_P1=True)              # show NB exit handle
    pink += _emit_handles(beziers2, show_first_P1=True, show_last_P2=True)  # show ST exit + NT entry handles
    # Stale-loop trigger block removed:
    for i, seg in enumerate([]):
        P0, P1, P2, P3 = seg
        show_P1 = (i != 0)
        show_P2 = (i != len(beziers2) - 1)
        if show_P1:
            pink += (
                f'<line x1="{P0[0]:.3f}" y1="{P0[1]:.3f}" '
                f'x2="{P1[0]:.3f}" y2="{P1[1]:.3f}" '
                f'stroke="{BEZ}" stroke-width="0.5" stroke-dasharray="2,1.5"/>\n'
                f'<circle cx="{P1[0]:.3f}" cy="{P1[1]:.3f}" r="1.6" '
                f'fill="#fff" stroke="{BEZ}" stroke-width="0.6"/>\n'
            )
        if show_P2:
            pink += (
                f'<line x1="{P3[0]:.3f}" y1="{P3[1]:.3f}" '
                f'x2="{P2[0]:.3f}" y2="{P2[1]:.3f}" '
                f'stroke="{BEZ}" stroke-width="0.5" stroke-dasharray="2,1.5"/>\n'
                f'<circle cx="{P2[0]:.3f}" cy="{P2[1]:.3f}" r="1.6" '
                f'fill="#fff" stroke="{BEZ}" stroke-width="0.6"/>\n'
            )
    # Anchors (endpoints of each segment, both legs, dedup by position)
    anchor_pts = []
    for seg in list(beziers1) + list(beziers2):
        for pt in (seg[0], seg[3]):
            if not anchor_pts or math.hypot(pt[0]-anchor_pts[-1][0],
                                            pt[1]-anchor_pts[-1][1]) > 0.05:
                anchor_pts.append(pt)
    for pt in anchor_pts:
        pink += (f'<circle cx="{pt[0]:.3f}" cy="{pt[1]:.3f}" r="2" fill="#000"/>\n')
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
