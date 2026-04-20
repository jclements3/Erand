"""
fitneck.py
==========

Per-contact Bezier-fit pipeline for the Erard 47-string harp neck outline.

Each CONTACT is a (point, tangent_direction) pair.  Between consecutive
contacts we fit a single cubic Bezier with BOTH endpoint tangents forced
to the prescribed directions:

  * Corner contacts (NB, ST, NT): tangent comes from HANDLE_CONSTRAINTS.
  * Circle contacts: tangent is perpendicular to the radius at that point.

Per-buffer classification (on each leg, in bass-to-treble order):
  * tight    : overlaps with a neighbor. Use the outer intersection point
               with each neighbor as entry/exit; the Bezier between them
               is a single arc-approximation on the circle.
  * loose    : isolated from both neighbors. Use outer common tangent
               points on each side; fit a straight Bezier from the prev
               circle's exit tangent to this circle's entry tangent,
               then an arc Bezier across this circle.
  * interior : skipped by Graham-scan convexity / validation pass; does
               not appear in the contact list.

After building the contact list we fit one cubic Bezier per segment.
Each segment is validated: sample it densely; if any sample is inside
any buffer, insert an extra contact (the deepest violator) and refit.
"""

import math
import os
import re
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_harp as bh
import bezierfit  # noqa: F401 (kept for reference; not used at top level)

R = bh.R_BUFFER
NB = np.array(bh.NB)
ST = np.array(bh.ST)
NT = np.array(bh.NT)


# ---------------------------------------------------------------------------
# Geometry primitives
# ---------------------------------------------------------------------------

def _unit(v):
    v = np.asarray(v, dtype=float)
    n = np.linalg.norm(v)
    return v / n if n > 0 else v


def _perp_tangent(center, point, walking_dir):
    """Given a point ON a circle of center `center`, return the unit tangent
    direction whose dot product with `walking_dir` is positive (i.e. pointing
    in the walking direction along the circle)."""
    r = np.asarray(point, dtype=float) - np.asarray(center, dtype=float)
    # Two perpendiculars to r:
    t1 = np.array([-r[1], r[0]])
    t2 = np.array([r[1], -r[0]])
    wd = np.asarray(walking_dir, dtype=float)
    return _unit(t1 if np.dot(t1, wd) > np.dot(t2, wd) else t2)


def tangent_from_point(P, C, r, side):
    """External tangent point on circle (C, r) from point P, chosen side."""
    P = np.asarray(P, dtype=float); C = np.asarray(C, dtype=float)
    dx = C[0] - P[0]; dy = C[1] - P[1]
    d = math.hypot(dx, dy)
    if d <= r:
        return None
    phi = math.atan2(dy, dx)
    beta = math.acos(-r / d)
    t1 = np.array([C[0] + r * math.cos(phi + beta), C[1] + r * math.sin(phi + beta)])
    t2 = np.array([C[0] + r * math.cos(phi - beta), C[1] + r * math.sin(phi - beta)])
    return (t1 if t1[1] > t2[1] else t2) if side == 'south' \
           else (t1 if t1[1] < t2[1] else t2)


def outer_tangent_circles(c1, r1, c2, r2, side):
    """Outer common tangent points for two circles, on the chosen side."""
    c1 = np.asarray(c1, dtype=float); c2 = np.asarray(c2, dtype=float)
    dx = c2[0] - c1[0]; dy = c2[1] - c1[1]
    d = math.hypot(dx, dy)
    if d == 0 or abs(r1 - r2) > d:
        return None
    phi = math.atan2(dy, dx)
    beta = math.asin((r1 - r2) / d) if r1 != r2 else 0.0
    results = []
    for sign in (+1, -1):
        theta = phi + sign * (math.pi / 2 - beta)
        p1 = np.array([c1[0] + r1 * math.cos(theta), c1[1] + r1 * math.sin(theta)])
        p2 = np.array([c2[0] + r2 * math.cos(theta), c2[1] + r2 * math.sin(theta)])
        results.append((p1, p2))
    if side == 'south':
        return max(results, key=lambda pair: (pair[0][1] + pair[1][1]) / 2)
    return min(results, key=lambda pair: (pair[0][1] + pair[1][1]) / 2)


def circle_intersections(c1, r1, c2, r2):
    c1 = np.asarray(c1, dtype=float); c2 = np.asarray(c2, dtype=float)
    dx = c2[0] - c1[0]; dy = c2[1] - c1[1]
    d = math.hypot(dx, dy)
    if d > r1 + r2 or d < abs(r1 - r2) or d == 0:
        return []
    a = (r1 * r1 - r2 * r2 + d * d) / (2 * d)
    h = math.sqrt(max(0.0, r1 * r1 - a * a))
    px = c1[0] + a * dx / d
    py = c1[1] + a * dy / d
    return [np.array([px + h * dy / d, py - h * dx / d]),
            np.array([px - h * dy / d, py + h * dx / d])]


def _pick_outer(pts, side):
    return max(pts, key=lambda p: p[1]) if side == 'south' \
           else min(pts, key=lambda p: p[1])


# ---------------------------------------------------------------------------
# Graham + validation pass: decide which buffers are on the envelope
# ---------------------------------------------------------------------------

def _envelope_buffers(start, end, circles, side):
    """Return the filtered list of buffer centers on the envelope, in order.
    Uses Graham-scan-style convexity + validation re-insertion of any buffer
    whose interior would be crossed."""
    elems = [('pt', tuple(start))] + [('circ', tuple(c)) for c in circles] + \
            [('pt', tuple(end))]

    def tangent_between(i, j):
        k1, c1 = elems[i]; k2, c2 = elems[j]
        if k1 == 'pt' and k2 == 'pt':
            return np.array(c1), np.array(c2)
        if k1 == 'pt':
            t = tangent_from_point(c1, c2, R, side)
            return np.array(c1), (t if t is not None else np.array(c2))
        if k2 == 'pt':
            t = tangent_from_point(c2, c1, R, side)
            return (t if t is not None else np.array(c1)), np.array(c2)
        d = math.hypot(c2[0] - c1[0], c2[1] - c1[1])
        if d > 2 * R:
            ot = outer_tangent_circles(c1, R, c2, R, side)
            if ot: return ot
        ints = circle_intersections(c1, R, c2, R)
        if ints:
            p = _pick_outer(ints, side)
            return p, p
        return np.array(c1), np.array(c2)

    def is_convex(i, j, k):
        p_i_out, p_j_in = tangent_between(i, j)
        p_j_out, p_k_in = tangent_between(j, k)
        v_in = p_j_in - p_i_out
        v_out = p_k_in - p_j_out
        cr = v_in[0] * v_out[1] - v_in[1] * v_out[0]
        return cr >= 0 if side == 'south' else cr <= 0

    stack = [0]
    for idx in range(1, len(elems)):
        while len(stack) >= 2:
            if is_convex(stack[-2], stack[-1], idx):
                break
            stack.pop()
        stack.append(idx)

    # Validation pass: re-insert any buffer the tangent crosses.
    all_circ = [i for i, (t, _) in enumerate(elems) if t == 'circ']
    for _pass in range(50):
        new_stack = [stack[0]]
        changed = False
        for k in range(len(stack) - 1):
            i, j = stack[k], stack[k + 1]
            pi, pj = tangent_between(i, j)
            dv = pj - pi
            L2 = float(np.dot(dv, dv))
            if L2 < 1e-9:
                new_stack.append(j); continue
            intruder, depth = None, 0.0
            for bi in all_circ:
                if bi in stack or bi <= i or bi >= j:
                    continue
                cb = np.array(elems[bi][1])
                t = float(np.dot(cb - pi, dv)) / L2
                t = max(0.0, min(1.0, t))
                cp = pi + t * dv
                d = float(np.linalg.norm(cp - cb))
                if d < R - 0.01 and (R - d) > depth:
                    depth = R - d; intruder = bi
            if intruder is not None:
                new_stack.append(intruder); changed = True
            new_stack.append(j)
        stack = new_stack
        if not changed:
            break

    dedup = [stack[0]]
    for idx in stack[1:]:
        if idx != dedup[-1]:
            dedup.append(idx)
    return [elems[i] for i in dedup]   # list of ('pt', xy) or ('circ', xy)


# ---------------------------------------------------------------------------
# Contact list: (point, tangent) pairs, plus segment-type metadata
# ---------------------------------------------------------------------------

def _build_contacts(start, start_tangent, end, end_tangent, circles, side):
    """Build the ordered contact list with tangent directions.

    Each element is a dict with keys:
      pt       : (x, y) contact point
      tan      : unit tangent at that point (direction of travel)
      next_seg : 'line' (straight tangent to next contact)
                 or ('arc', center, R) for an arc on a circle
                 or None for the terminal contact
    """
    env = _envelope_buffers(start, end, circles, side)

    # Helper: compute outer tangent point between two consecutive elems
    def tangent_point(elem_a, elem_b):
        ka, ca = elem_a; kb, cb = elem_b
        if ka == 'pt' and kb == 'pt':
            return None, None
        if ka == 'pt':
            tp = tangent_from_point(ca, cb, R, side)
            return np.array(ca), tp
        if kb == 'pt':
            tp = tangent_from_point(cb, ca, R, side)
            return tp, np.array(cb)
        d = math.hypot(cb[0] - ca[0], cb[1] - ca[1])
        if d > 2 * R:
            ot = outer_tangent_circles(ca, R, cb, R, side)
            if ot: return ot
        ints = circle_intersections(ca, R, cb, R)
        if ints:
            p = _pick_outer(ints, side)
            return p, p
        return None, None

    # For each envelope element, compute its entry & exit points with tangent dirs.
    n = len(env)
    contacts = []
    for i, (kind, xy) in enumerate(env):
        prev_ent, cur_ent = (None, None) if i == 0 else tangent_point(env[i - 1], env[i])
        cur_exit, next_ent = (None, None) if i == n - 1 else tangent_point(env[i], env[i + 1])

        if kind == 'pt':
            # Corner contact
            if i == 0:
                # start corner: its point is the contact; tangent is the forced
                # start_tangent; next_seg is a line to the next contact.
                contacts.append({'pt': np.asarray(xy, dtype=float),
                                 'tan': _unit(start_tangent),
                                 'next_seg': 'line'})
            else:
                # end corner: tangent is the reverse of end_tangent (end_tangent
                # points INTO the corner; travel direction is also INTO, so they
                # align — store as-is)
                contacts.append({'pt': np.asarray(xy, dtype=float),
                                 'tan': _unit(end_tangent),
                                 'next_seg': None})
            continue

        # Circle contact.  Use entry & exit tangent points, each with tangent
        # perpendicular to the radius at that point.  If entry==exit (circles
        # intersect or overlap fully), only one contact.
        C = np.asarray(xy, dtype=float)

        # entry tangent point:
        if cur_ent is None:
            # Shouldn't happen — treat as outer pole
            if side == 'south':
                ent_pt = np.array([C[0], C[1] + R])
            else:
                ent_pt = np.array([C[0], C[1] - R])
        else:
            ent_pt = np.asarray(cur_ent, dtype=float)

        # exit tangent point:
        if cur_exit is None:
            if side == 'south':
                ex_pt = np.array([C[0], C[1] + R])
            else:
                ex_pt = np.array([C[0], C[1] - R])
        else:
            ex_pt = np.asarray(cur_exit, dtype=float)

        # walking direction estimate: from ent_pt to ex_pt (or use neighbors)
        if np.linalg.norm(ex_pt - ent_pt) > 1e-3:
            walking = _unit(ex_pt - ent_pt)
        else:
            # entry == exit: walking direction comes from neighbor positions
            prev_xy = np.asarray(env[i - 1][1], dtype=float) if i > 0 else np.asarray(start)
            next_xy = np.asarray(env[i + 1][1], dtype=float) if i < n - 1 else np.asarray(end)
            walking = _unit(next_xy - prev_xy)

        # tangent at entry: perpendicular to (ent_pt - C), aligned with walking
        t_ent = _perp_tangent(C, ent_pt, walking)
        t_ex  = _perp_tangent(C, ex_pt,  walking)

        if np.linalg.norm(ex_pt - ent_pt) < 1e-3:
            # Single contact point (circles touch tangentially or intersect at
            # exactly one outer point).  Collapse to a single contact.
            contacts.append({'pt': ent_pt, 'tan': _unit(t_ent + t_ex),
                             'next_seg': 'line'})
            continue

        # Two contacts on this circle, with an arc between them.
        contacts.append({'pt': ent_pt, 'tan': t_ent, 'next_seg': ('arc', C, R)})
        contacts.append({'pt': ex_pt,  'tan': t_ex,  'next_seg': 'line'})

    return contacts


# ---------------------------------------------------------------------------
# Per-segment cubic Bezier with forced endpoint tangents
# ---------------------------------------------------------------------------

def _bezier_line_segment(P0, T0, P3, T3):
    """Cubic Bezier with both endpoint tangents forced.  Handle length =
    chord / 3 — standard choice for a straight-ish segment."""
    P0 = np.asarray(P0, dtype=float); P3 = np.asarray(P3, dtype=float)
    T0 = _unit(T0); T3 = _unit(T3)
    chord = np.linalg.norm(P3 - P0)
    h = chord / 3.0
    P1 = P0 + T0 * h
    P2 = P3 - T3 * h
    return np.array([P0, P1, P2, P3])


def _bezier_arc_segment(P0, T0, P3, T3, center, r):
    """Cubic Bezier approximation of a circular arc from P0 to P3 on circle
    (center, r), with tangents T0 at start and T3 at end (both pre-computed
    to be perpendicular to radii).  Handle length = (4/3)*tan(theta/4)*r
    where theta is the subtended angle."""
    P0 = np.asarray(P0, dtype=float); P3 = np.asarray(P3, dtype=float)
    T0 = _unit(T0); T3 = _unit(T3)
    v0 = P0 - np.asarray(center, dtype=float)
    v3 = P3 - np.asarray(center, dtype=float)
    cos_theta = float(np.clip(np.dot(v0, v3) / (np.linalg.norm(v0) * np.linalg.norm(v3)), -1, 1))
    theta = math.acos(cos_theta)
    if theta < 1e-6:
        # Degenerate: tiny arc, fallback to straight chord
        return _bezier_line_segment(P0, T0, P3, T3)
    h = (4.0 / 3.0) * math.tan(theta / 4.0) * r
    P1 = P0 + T0 * h
    P2 = P3 - T3 * h
    return np.array([P0, P1, P2, P3])


def _fit_segment(A, B):
    """Fit a cubic Bezier between two contacts A and B, using A['next_seg']
    to decide the segment type."""
    seg_type = A['next_seg']
    if seg_type == 'line':
        return _bezier_line_segment(A['pt'], A['tan'], B['pt'], B['tan'])
    if isinstance(seg_type, tuple) and seg_type[0] == 'arc':
        _, center, r = seg_type
        return _bezier_arc_segment(A['pt'], A['tan'], B['pt'], B['tan'], center, r)
    raise ValueError(f"unknown segment type {seg_type!r}")


def _sample_bezier(bez, n=30):
    """Sample a cubic Bezier at n points along t in [0, 1]."""
    ts = np.linspace(0, 1, n)
    pts = np.zeros((n, 2))
    for k, t in enumerate(ts):
        mt = 1.0 - t
        pts[k] = (mt ** 3) * bez[0] + 3 * mt * mt * t * bez[1] \
                + 3 * mt * t * t * bez[2] + (t ** 3) * bez[3]
    return pts


def _validate_segments(segments, circles, tol=0.05):
    """For each Bezier segment, sample densely and confirm every sample is
    outside every buffer.  Return list of (seg_idx, circle_xy, penetration)
    for violations."""
    violations = []
    for si, bez in enumerate(segments):
        pts = _sample_bezier(bez, 40)
        for cxy in circles:
            cxy = np.asarray(cxy, dtype=float)
            dists = np.linalg.norm(pts - cxy, axis=1)
            min_d = float(dists.min())
            if min_d < R - tol:
                violations.append((si, tuple(cxy), R - min_d))
    return violations


# ---------------------------------------------------------------------------
# Leg builder (full pipeline)
# ---------------------------------------------------------------------------

def build_leg(start, start_tangent, end, end_tangent, circles, side):
    contacts = _build_contacts(start, start_tangent, end, end_tangent, circles, side)
    segments = []
    for a, b in zip(contacts[:-1], contacts[1:]):
        segments.append(_fit_segment(a, b))
    viols = _validate_segments(segments, circles)
    return contacts, segments, viols


# ---------------------------------------------------------------------------
# SVG output
# ---------------------------------------------------------------------------

def beziers_to_d(beziers):
    if not beziers:
        return ""
    P0 = beziers[0][0]
    parts = [f"M {P0[0]:.3f} {P0[1]:.3f}"]
    for bez in beziers:
        _, P1, P2, P3 = bez
        parts.append(f"C {P1[0]:.3f} {P1[1]:.3f} "
                     f"{P2[0]:.3f} {P2[1]:.3f} "
                     f"{P3[0]:.3f} {P3[1]:.3f}")
    return " ".join(parts)


def main():
    strings = bh.build_strings()
    sharps = [s['sharp'] for s in strings if s['has_sharp_buffer']]
    flats  = [s['flat_buffer'] for s in reversed(strings) if s['has_flat_buffer']]

    # -- Leg 1: NB -> sharps -> ST, south side --
    nb_exit = bh.HANDLE_CONSTRAINTS['NB']['exit_dir']
    st_entry = bh.HANDLE_CONSTRAINTS['ST']['entry_dir']
    st_entry_dir = bh.HANDLE_CONSTRAINTS['ST']['exit_dir'] if st_entry is None else st_entry
    # Travel direction INTO ST on leg 1: point toward ST from previous contact.
    # We flip `exit_dir` because it points OUT from ST; walking-in is the reverse.
    end_tan_leg1 = np.array(st_entry_dir)  # we let the fit use this as direction of motion
    if st_entry is None:
        # No explicit entry constraint: use -exit_dir to align tangent with travel dir into ST.
        end_tan_leg1 = -np.array(st_entry_dir)

    contacts1, segs1, viols1 = build_leg(NB, nb_exit, ST, end_tan_leg1, sharps, 'south')
    print(f"Leg 1: {len(contacts1)} contacts, {len(segs1)} Bezier segments, {len(viols1)} violations")

    # -- Leg 2: ST -> flats -> NT, north side --
    st_exit = bh.HANDLE_CONSTRAINTS['ST']['exit_dir']
    # Flip: Leg 2 leaves ST in the REVERSE direction of st_exit (soundboard goes
    # the other way going up the neck).  Actually st_exit was defined as the
    # direction ST points outward toward the neck — we head in that direction.
    start_tan_leg2 = np.array(st_exit)
    nt_entry = bh.HANDLE_CONSTRAINTS['NT']['entry_dir']
    if nt_entry is None:
        # Flip the NT exit (exit is 'down the column', but leg 2 arrives from the
        # south, so travel direction INTO NT is downward-ish toward the column).
        end_tan_leg2 = -np.array(bh.HANDLE_CONSTRAINTS['NT']['exit_dir'])
    else:
        end_tan_leg2 = np.array(nt_entry)

    contacts2, segs2, viols2 = build_leg(ST, start_tan_leg2, NT, end_tan_leg2, flats, 'north')
    print(f"Leg 2: {len(contacts2)} contacts, {len(segs2)} Bezier segments, {len(viols2)} violations")

    d1 = beziers_to_d(segs1)
    d2 = beziers_to_d(segs2)
    d3 = f"M {NT[0]:.3f} {NT[1]:.3f} L {NB[0]:.3f} {NB[1]:.3f}"

    # Inject into SVG
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

    if viols1 or viols2:
        print(f"  Total violations: leg1={len(viols1)}  leg2={len(viols2)}")
        for si, c, depth in (viols1 + viols2)[:5]:
            print(f"    seg {si} at {c} depth {depth:.2f} mm")
    else:
        print("  All Bezier segments stay outside every buffer circle.")


if __name__ == '__main__':
    main()
