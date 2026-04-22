"""
neck_geodesic.py
================

Compute the neck outline as a geodesic (shortest-path-around-obstacles)
for each leg:
  - Leg 1: NB -> ST, outline on SOUTH side of sharp buffers
  - Leg 2: ST -> NT, outline on NORTH side of flat buffers (via reversed list)
  - Leg 3: NT -> NB, straight line down column

Algorithm (funnel/string-pull method):
  1. Pick a side (south for leg 1, north for leg 2).
  2. Start with a straight line from start to end.
  3. For any buffer that crosses this line on the wrong side, the line must
     wrap around it. Iteratively "pull" the string tight around violating
     buffers.

Practical implementation using the rotating-calipers / incremental convex hull
approach:
  - Build the ordered list of buffer centers between start and end.
  - Compute the outer "half-hull" of {start, all buffer boundaries, end}
    — the curve of tangent lines and arcs on the chosen side.

The outer half-hull of a chain of circles (all equal radius) is:
  - For consecutive circles that don't overlap: the outer common tangent line.
  - Where the tangent sequence creates concavities, circles are skipped
    (no contact) and tangent jumps directly to a farther circle.

This is Graham-scan-style for circles: maintain a stack of "active" circles
currently forming the outer boundary. For each new circle, check whether
adding it would create a concave turn; if so, pop previous circles until
convex again.
"""

import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_harp as bh

R = bh.R_BUFFER
NB = bh.NB
NT = bh.NT
ST = bh.ST


# ---------------------------------------------------------------------------
# Primitives
# ---------------------------------------------------------------------------

def tangent_from_point(P, C, r, side):
    """Tangent point on circle (C, r) from external point P, on chosen side.
    side = 'south' (pick tangent with larger y) or 'north' (smaller y).
    Returns the tangent point (x, y) or None if P is inside the circle.
    """
    dx = C[0] - P[0]
    dy = C[1] - P[1]
    d = math.hypot(dx, dy)
    if d <= r:
        return None
    phi = math.atan2(dy, dx)
    beta = math.acos(-r / d)
    t1 = (C[0] + r * math.cos(phi + beta), C[1] + r * math.sin(phi + beta))
    t2 = (C[0] + r * math.cos(phi - beta), C[1] + r * math.sin(phi - beta))
    return max([t1, t2], key=lambda p: p[1]) if side == 'south' else \
           min([t1, t2], key=lambda p: p[1])


def outer_tangent_circles(c1, r1, c2, r2, side):
    """Return (p1, p2) = tangent points of the outer common tangent on the
    chosen side. For equal-radius circles, this tangent is parallel to the
    line between centers."""
    dx = c2[0] - c1[0]
    dy = c2[1] - c1[1]
    d = math.hypot(dx, dy)
    if d == 0 or abs(r1 - r2) > d:
        return None
    phi = math.atan2(dy, dx)
    beta = math.asin((r1 - r2) / d) if r1 != r2 else 0.0
    results = []
    for sign in (+1, -1):
        theta = phi + sign * (math.pi / 2 - beta)
        p1 = (c1[0] + r1 * math.cos(theta), c1[1] + r1 * math.sin(theta))
        p2 = (c2[0] + r2 * math.cos(theta), c2[1] + r2 * math.sin(theta))
        results.append((p1, p2))
    if side == 'south':
        return max(results, key=lambda pair: (pair[0][1] + pair[1][1]) / 2)
    else:
        return min(results, key=lambda pair: (pair[0][1] + pair[1][1]) / 2)


def cross(o, a, b):
    """2D cross product (a - o) x (b - o). Positive = CCW, negative = CW."""
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


# ---------------------------------------------------------------------------
# The geodesic algorithm
# ---------------------------------------------------------------------------

def geodesic_outline(start, end, circles, side):
    """Compute the shortest-path outline from `start` to `end`, staying on the
    `side` side of `circles`. Each circle is (center, radius).

    Returns a list of (kind, data) entries:
      - ('line', (p1, p2)): straight tangent segment
      - ('arc',  (center, r, p_start, p_end)): arc along the outer side of
         a circle, from p_start to p_end.

    Uses a Graham-scan-like approach: walk left-to-right (bass-to-treble in x),
    maintain a stack of active circles forming the outer boundary; when a
    new circle would create a concave turn, pop until convex.
    """
    # Represent elements as (type, center, radius, label). Start/end are
    # radius-0 points.
    elems = [('point', start, 0.0)] + \
            [('circ', c, R) for c in circles] + \
            [('point', end, 0.0)]

    # Stack will hold indices into elems that are currently on the outer
    # boundary. For each such index, we also cache (enter_pt, exit_pt) where
    # the boundary arrives/leaves the circle.
    # We'll process elements in order and maintain convexity.

    # Represent the "tangent line going OUT from element i to element j" as
    # the pair (p_i_out, p_j_in). For a point, p_*_out = p_*_in = the point.
    # For a circle, they are tangent points on its perimeter.

    def tangent(i, j):
        """Return (p_i_out, p_j_in) for the outer tangent between elems[i] and
        elems[j]."""
        t_i, c_i, r_i = elems[i]
        t_j, c_j, r_j = elems[j]
        if r_i == 0 and r_j == 0:
            return (c_i, c_j)
        if r_i == 0:
            pj = tangent_from_point(c_i, c_j, r_j, side)
            return (c_i, pj)
        if r_j == 0:
            pi = tangent_from_point(c_j, c_i, r_i, side)
            return (pi, c_j)
        ot = outer_tangent_circles(c_i, r_i, c_j, r_j, side)
        return ot if ot else (None, None)

    def is_convex_turn(i, j, k):
        """Is the turn at element j (coming from i, going to k) convex for
        the chosen side? For south side in SVG y-down, we traverse left-to-right;
        a convex (outer-side) turn means the sequence i->j->k bends DOWNWARD
        (increasing y then outward) — cross product of (j-i, k-j) has the right
        sign."""
        # Get the relevant points: exit of i, (j_enter, j_exit), and enter of k.
        # But for testing convexity we can use representative points: the
        # tangent points themselves.
        p_i_out, p_j_in = tangent(i, j)
        p_j_out, p_k_in = tangent(j, k)
        if any(p is None for p in (p_i_out, p_j_in, p_j_out, p_k_in)):
            return True  # can't resolve; keep the element
        # Direction of travel arriving at j: p_j_in - p_i_out
        # Direction of travel leaving j: p_k_in - p_j_out
        v_in = (p_j_in[0] - p_i_out[0], p_j_in[1] - p_i_out[1])
        v_out = (p_k_in[0] - p_j_out[0], p_k_in[1] - p_j_out[1])
        # Cross product v_in x v_out in 2D:
        c = v_in[0] * v_out[1] - v_in[1] * v_out[0]
        # For south side in SVG y-down coords traversing bass->treble (x increasing):
        #   outer side is south (larger y below). A convex turn on the south side
        #   bends DOWNWARD: v_in turns toward +y, meaning the cross product is
        #   POSITIVE (in y-down frame).
        # For north side (traversing treble->bass in our leg 2), also x decreases;
        #   convex there means cross product is NEGATIVE in y-down frame.
        # Implement by checking the sign directly per side:
        if side == 'south':
            return c >= 0  # convex on south
        else:
            return c <= 0  # convex on north

    # Greedy algorithm: walk through elements, maintaining a stack. For each
    # new element, pop back elements from the stack while the turn at the
    # top of the stack (prev, top, new) is concave.
    # Kiss every buffer: don't skip any. The stack is all elements in order.
    stack = list(range(len(elems)))

    # Validation pass still runs but should be a no-op since we include all
    all_circle_indices = [i for i, (t, c, r) in enumerate(elems) if t == 'circ']
    for _pass in range(50):  # safety cap
        changed = False
        new_stack = [stack[0]]
        for k in range(len(stack) - 1):
            i, j = stack[k], stack[k + 1]
            p_i_out, p_j_in = tangent(i, j)
            if p_i_out is None or p_j_in is None:
                new_stack.append(j)
                continue
            # Find any buffer (not in stack, between i and j) whose interior
            # is crossed by the segment p_i_out -> p_j_in
            intruder = None
            intruder_depth = 0.0
            for bi in all_circle_indices:
                if bi in stack or bi <= i or bi >= j:
                    continue
                _, c_b, r_b = elems[bi]
                # Distance from segment to c_b
                ax, ay = p_i_out
                bx, by = p_j_in
                dx = bx - ax
                dy = by - ay
                L2 = dx * dx + dy * dy
                if L2 < 1e-12:
                    continue
                t = ((c_b[0] - ax) * dx + (c_b[1] - ay) * dy) / L2
                t = max(0.0, min(1.0, t))
                closest = (ax + t * dx, ay + t * dy)
                d = math.hypot(closest[0] - c_b[0], closest[1] - c_b[1])
                if d < r_b - 0.01:
                    depth = r_b - d
                    if depth > intruder_depth:
                        intruder_depth = depth
                        intruder = bi
            if intruder is not None:
                new_stack.append(intruder)
                changed = True
            new_stack.append(j)
        stack = new_stack
        if not changed:
            break

    # De-duplicate consecutive duplicates
    dedup = [stack[0]]
    for idx in stack[1:]:
        if idx != dedup[-1]:
            dedup.append(idx)
    stack = dedup

    # Now construct the path from the stack.
    # For each consecutive pair (stack[k], stack[k+1]): straight tangent line.
    # For each middle stack entry (stack[k] where 0 < k < len-1):
    #   arc from (tangent(prev, this))[1] to (tangent(this, next))[0].
    segments = []
    for k in range(len(stack) - 1):
        i, j = stack[k], stack[k + 1]
        p_i_out, p_j_in = tangent(i, j)
        if p_i_out is None or p_j_in is None:
            continue
        segments.append(('line', (p_i_out, p_j_in)))
        if k + 1 < len(stack) - 1:
            # Arc on element j between its enter point (p_j_in) and its exit
            # toward the next element.
            j_next = stack[k + 2]
            p_j_out, _ = tangent(j, j_next)
            if p_j_out is None:
                continue
            _, c_j, r_j = elems[j]
            if r_j > 0:
                segments.append(('arc', (c_j, r_j, p_j_in, p_j_out)))
    return segments


# ---------------------------------------------------------------------------
# SVG emission
# ---------------------------------------------------------------------------

def segments_to_svg_d(segments, side):
    """Convert segments list to SVG path `d` attribute."""
    if not segments:
        return ""
    parts = []
    # Start: move to first segment's start point
    first = segments[0]
    if first[0] == 'line':
        start_pt = first[1][0]
    else:
        _, _, start_pt, _ = first[1]
    parts.append(f"M {start_pt[0]:.3f} {start_pt[1]:.3f}")

    for seg in segments:
        if seg[0] == 'line':
            p1, p2 = seg[1]
            parts.append(f"L {p2[0]:.3f} {p2[1]:.3f}")
        else:
            c, r, p_s, p_e = seg[1]
            # Arc on outer side. Compute sweep/large by angle math.
            a_s = math.atan2(p_s[1] - c[1], p_s[0] - c[0])
            a_e = math.atan2(p_e[1] - c[1], p_e[0] - c[0])
            ccw_delta = (a_e - a_s) % (2 * math.pi)
            cw_delta = (a_s - a_e) % (2 * math.pi)
            a_mid_ccw = a_s + ccw_delta / 2
            a_mid_cw = a_s - cw_delta / 2
            mp_ccw = (c[0] + r * math.cos(a_mid_ccw),
                      c[1] + r * math.sin(a_mid_ccw))
            mp_cw = (c[0] + r * math.cos(a_mid_cw),
                     c[1] + r * math.sin(a_mid_cw))
            if side == 'south':
                want_ccw = mp_ccw[1] > mp_cw[1]
            else:
                want_ccw = mp_ccw[1] < mp_cw[1]
            if want_ccw:
                delta = ccw_delta
                sweep = 1
            else:
                delta = cw_delta
                sweep = 0
            large = 1 if delta > math.pi else 0
            # Move to arc start (in case line didn't end exactly there)
            parts.append(f"L {p_s[0]:.3f} {p_s[1]:.3f}")
            parts.append(
                f"A {r:.3f} {r:.3f} 0 {large} {sweep} "
                f"{p_e[0]:.3f} {p_e[1]:.3f}"
            )
    return " ".join(parts)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    strings = bh.build_strings()
    # BT = east end of bulge tip locus at the NECK's ST horizontal plane
    # (y = bh.ST[1]). Binary-search s_p > S_PEAK such that
    # bulge_tip_y(s_p) = ST[1]; the tip x at that station is BT.x.
    # soundbox/geometry.py's baked-in S_TREBLE_CLEAR is for the old ST
    # y=481.94, so we can't use it directly once ST has been lowered.
    import sys as _sys, os as _os
    _sb_dir = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), 'soundbox')
    if _sb_dir not in _sys.path:
        _sys.path.insert(0, _sb_dir)
    import geometry as _sbg  # type: ignore
    _target_y = ST[1]
    _lo, _hi = _sbg.S_PEAK, _sbg.S_TREBLE_FINAL
    for _ in range(60):
        _mid = 0.5 * (_lo + _hi)
        if _sbg.bulge_tip_point(_mid)[1] < _target_y:
            _hi = _mid
        else:
            _lo = _mid
    _tip = _sbg.bulge_tip_point(0.5 * (_lo + _hi))
    BT = (_tip[0], _tip[1])

    # The polyline's job is ONLY to wrap the buffer circles. ST, BT, NTI,
    # NTO etc. are fixed anchors for the brown Bezier neck; they sit OUTSIDE
    # the polyline area and are handled by the optimizer, not here.
    #
    # Leg 1 ends at the east pole of the G7 sharp buffer (last sharp on the
    # treble side); Leg 2 starts at the east pole of the G7 flat buffer.
    # A short connector line links the two east poles at the treble end.
    # G7 is INCLUDED in both chains so its buffer gets wrapped.
    G7 = next(s for s in strings if s.get('note') == 'G7')
    G7sb_east = (G7['sharp'][0] + R, G7['sharp'][1])
    G7fb_east = (G7['flat_buffer'][0] + R, G7['flat_buffer'][1])

    def _terminate_at_east_pole(segs, circle_center):
        """Drop the final tangent line and clip the last arc to end at
        (circle_center + (R, 0))."""
        while segs and segs[-1][0] == 'line':
            segs = segs[:-1]
        if segs and segs[-1][0] == 'arc':
            c, r, p_s, _ = segs[-1][1]
            if math.hypot(c[0] - circle_center[0], c[1] - circle_center[1]) < 1e-6:
                east = (c[0] + r, c[1])
                segs = segs[:-1] + [('arc', (c, r, p_s, east))]
        return segs

    def _start_at_east_pole(segs, circle_center):
        """Drop the leading tangent line and clip the first arc to start at
        (circle_center + (R, 0))."""
        while segs and segs[0][0] == 'line':
            segs = segs[1:]
        if segs and segs[0][0] == 'arc':
            c, r, _, p_e = segs[0][1]
            if math.hypot(c[0] - circle_center[0], c[1] - circle_center[1]) < 1e-6:
                east = (c[0] + r, c[1])
                segs = [('arc', (c, r, east, p_e))] + segs[1:]
        return segs

    # Leg 1: NB -> sharp buffers (including G7) -> east pole of G7sb.
    sharps = [s['sharp'] for s in strings if s['has_sharp_buffer']]
    segs1 = geodesic_outline(NB, BT, sharps, side='south')
    segs1 = _terminate_at_east_pole(segs1, G7['sharp'])
    d1 = segments_to_svg_d(segs1, side='south')

    # Connector: G7sb east pole -> G7fb east pole (short near-vertical line
    # at the treble "beak"). The brown Bezier neck engulfs this region
    # externally via its BT anchor.
    d_connector = f"M {G7sb_east[0]:.3f} {G7sb_east[1]:.3f} L {G7fb_east[0]:.3f} {G7fb_east[1]:.3f}"

    # Leg 2: east pole of G7fb -> flat buffers (including G7) -> NT, north side.
    flats = [s['flat_buffer'] for s in reversed(strings) if s['has_flat_buffer']]
    segs2 = geodesic_outline(BT, NT, flats, side='north')
    segs2 = _start_at_east_pole(segs2, G7['flat_buffer'])
    _SKIP_SB_OVERRIDE = True  # keep the natural geodesic tangent on G7fb

    # Apply ST exit handle constraint: first segment leaving ST should be
    # PARALLEL to the soundboard slope. On the G7 flat buffer, the tangent
    # point where the incoming tangent line is parallel to slope is the
    # point whose RADIUS is perpendicular to the slope. There are two such
    # points (on opposite sides of the circle); pick the one on the "north"
    # (outer) side of G7 — i.e. on the outside of the harmonic curve.
    sb_dir = bh._SOUNDBOARD_DIR  # unit vector along slope
    if not _SKIP_SB_OVERRIDE and len(segs2) >= 2 and segs2[0][0] == 'line' and segs2[1][0] == 'arc':
        _, (p_start, _old_end) = segs2[0]
        _, (c_first, r_first, _old_enter, arc_exit) = segs2[1]
        # Perpendicular to slope: rotate sb_dir by 90°.
        # Two candidates: +90° and -90°
        perp_pos = (-sb_dir[1], sb_dir[0])    # rotate +90°
        perp_neg = ( sb_dir[1], -sb_dir[0])   # rotate -90°
        cand_pos = (c_first[0] + r_first * perp_pos[0],
                    c_first[1] + r_first * perp_pos[1])
        cand_neg = (c_first[0] + r_first * perp_neg[0],
                    c_first[1] + r_first * perp_neg[1])
        # Pick the "north" one (smaller y = upper in SVG)
        new_tangent = cand_pos if cand_pos[1] < cand_neg[1] else cand_neg
        # Replace segment 0 (ST->old tangent) and segment 1 (arc).
        # New structure: single tangent line ST->new_tangent (parallel to slope),
        # then a possibly longer arc on G7 from new_tangent to arc_exit.
        segs2 = ([
            ('line', (p_start, new_tangent)),
            ('arc', (c_first, r_first, new_tangent, arc_exit)),
        ] + segs2[2:])

    d2 = segments_to_svg_d(segs2, side='north')

    # Leg 3: NT -> NB straight line
    d3 = f"M {NT[0]:.3f} {NT[1]:.3f} L {NB[0]:.3f} {NB[1]:.3f}"

    # Write into SVG
    with open(bh.OUTPUT_SVG) as f:
        content = f.read()
    content = re.sub(r'<(path|line|circle)[^>]*"#ff69b4"[^>]*/>\s*', '', content)
    pink = (
        f'<path d="{d1}" fill="none" stroke="#ff69b4" stroke-width="1.6"/>\n'
        f'<path d="{d_connector}" fill="none" stroke="#ff69b4" stroke-width="1.6"/>\n'
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

    n1_arcs = sum(1 for s in segs1 if s[0] == 'arc')
    n1_lines = sum(1 for s in segs1 if s[0] == 'line')
    n2_arcs = sum(1 for s in segs2 if s[0] == 'arc')
    n2_lines = sum(1 for s in segs2 if s[0] == 'line')
    print(f"Leg 1 (NB->BT south): {n1_lines} lines + {n1_arcs} arcs  "
          f"(kissed {n1_arcs} buffers, skipped {len(sharps) - n1_arcs})")
    print(f"Leg 2 (BT->NT north): {n2_lines} lines + {n2_arcs} arcs  "
          f"(kissed {n2_arcs} buffers, skipped {len(flats) - n2_arcs})")

    # ------------------------------------------------------------------
    # Nat-buffer feasibility check.
    #
    # Nat (clicky-pen) buffers sit between the pin and sharp-pitch points on
    # each string and are NOT part of the pink polyline's obstacle chain
    # (they're topologically interior to the envelope formed by flats on the
    # north side and sharps on the south side). The polyline's job is the
    # outer envelope only. We still want to verify that each nat buffer
    # circle lies strictly inside that envelope — if one doesn't, the neck
    # Bezier will have to be locally widened or the nat point relocated.
    # ------------------------------------------------------------------
    def _flatten(segments, n_arc=24):
        pts = []
        for seg in segments:
            if seg[0] == 'line':
                p1, p2 = seg[1]
                if not pts:
                    pts.append(p1)
                pts.append(p2)
            else:
                c, r, p_s, p_e = seg[1]
                a_s = math.atan2(p_s[1] - c[1], p_s[0] - c[0])
                a_e = math.atan2(p_e[1] - c[1], p_e[0] - c[0])
                # Pick shorter sweep direction matching the earlier SVG logic
                ccw_delta = (a_e - a_s) % (2 * math.pi)
                cw_delta = (a_s - a_e) % (2 * math.pi)
                if ccw_delta <= cw_delta:
                    delta = ccw_delta
                    step = delta / n_arc
                    angles = [a_s + step * k for k in range(n_arc + 1)]
                else:
                    delta = cw_delta
                    step = -delta / n_arc
                    angles = [a_s + step * k for k in range(n_arc + 1)]
                if not pts:
                    pts.append(p_s)
                for a in angles[1:]:
                    pts.append((c[0] + r * math.cos(a),
                                c[1] + r * math.sin(a)))
        return pts

    poly = []
    poly += _flatten(segs1)                                     # NB -> G7sb east
    poly.append(G7fb_east)                                      # connector
    poly += _flatten(segs2)[1:]                                 # G7fb east -> NT
    poly.append(NB)                                             # Leg 3: NT -> NB

    def _point_in_poly(pt, polygon):
        x, y = pt
        inside = False
        n = len(polygon)
        j = n - 1
        for i in range(n):
            xi, yi = polygon[i]
            xj, yj = polygon[j]
            if ((yi > y) != (yj > y)) and \
               (x < (xj - xi) * (y - yi) / (yj - yi + 1e-18) + xi):
                inside = not inside
            j = i
        return inside

    N_SAMPLE = 32
    offenders = []
    for s in strings:
        if not s.get('has_nat_buffer'):
            continue
        cx, cy = s['nat_buffer']
        ok = True
        # Check center + perimeter samples at R
        for k in range(N_SAMPLE):
            theta = 2 * math.pi * k / N_SAMPLE
            px = cx + R * math.cos(theta)
            py = cy + R * math.sin(theta)
            if not _point_in_poly((px, py), poly):
                ok = False
                break
        if not _point_in_poly((cx, cy), poly):
            ok = False
        if not ok:
            offenders.append(s['note'])

    if not offenders:
        print(f"Nat-buffer feasibility: all {sum(1 for s in strings if s.get('has_nat_buffer'))} nat buffers inside polyline envelope.")
    else:
        print(f"Nat-buffer feasibility: {len(offenders)} nat buffer(s) NOT strictly inside polyline envelope:")
        print(f"  offenders: {offenders}")
        print(f"  (neck material may need local adjustment, or add (i,'nat') to SKIPPED_BUFFERS)")


if __name__ == '__main__':
    main()
