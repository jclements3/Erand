Fit the neck outline of the Clements 47 harp as a closed 12-segment piecewise
cubic Bezier curve around fixed buffer-circle obstacles, with every anchor
position AND every tangent direction pre-specified. Only per-side handle
lengths are tunable. Minimise bending energy while staying outside every
R_buffer = 12 mm buffer disk.

COORDINATE FRAME.
SVG convention: x increases to the right, y increases DOWNWARD. Lengths
in millimetres. Angles in radians: angle 0 = +x, angle +pi/2 = +y
(downward on screen).

PROBLEM.
Given the 13 named anchor positions below and their locked incoming /
outgoing tangent directions, construct 12 cubic Bezier segments joining
consecutive anchors (Leg 3 closes with a straight line, not a cubic).
Choose the per-side handle lengths (half-widths) so that the assembled
path stays outside every buffer circle in the obstacle set B, and
minimises bending energy. The anchor positions and tangent directions
are NOT tunable — only the handle lengths.

ANCHORS (traversal order, counterclockwise around the neck).
All positions are derivable from `build_harp.build_strings()` and the
soundbox geometry in `soundbox/geometry.py`. Let R = 12 mm and let
sb = unit(ST - CO) = SOUNDBOARD_DIR.

| # | Name   | Position                                                              |
|---|--------|-----------------------------------------------------------------------|
| 0 | NB     | (12.700, 323.844) — column outer, same y as C1 sharp south pole       |
| 1 | C1sbi  | (x_C1sb, 323.844) = south pole of bass-most sharp buffer              |
| 2 | E2s    | south pole of E2 sharp buffer (string 10)                             |
| 3 | A3s    | south pole of A3 sharp buffer (string 20)                             |
| 4 | E5s    | south pole of E5 sharp buffer (string 31)                             |
| 5 | G7sbi  | F7sb -> G7sb outer common tangent point on G7sb, south side           |
| 6 | G7sbo  | south pole of G7 sharp buffer                                         |
| 7 | BT     | bulge_tip_point(S_TREBLE_CLEAR) ~ (906.632, 481.877)                  |
| 8 | G7fbo  | G7fb -> F7fb outer common tangent point on G7fb, north side           |
| 9 | F5f    | north pole of F5 flat buffer (string 32)                              |
|10 | G2f    | north pole of G2 flat buffer (string 12)                              |
|11 | F1fbi  | north pole of F1 flat buffer (string 4)                               |
|12 | NT     | (12.700, 146.563) — column outer                                      |

Leg 3 closure: straight line NT -> NB. Not a Bezier.

TANGENT DIRECTIONS (locked).
Each anchor carries an incoming tangent `t_in` (used as the tangent at
P3 of the preceding segment) and an outgoing tangent `t_out` (tangent
at P0 of the following segment). For C1-symmetric anchors,
t_in = t_out. For corners, they differ.

Let e = (1, 0) (east), w = (-1, 0) (west), sou = (0, 1) (south in SVG).
Let TILT45_DR = (cos 45°, sin 45°) = (0.7071, 0.7071)  (east-south).
Let t_g7sbi = unit(G7sb_center - F7sb_center).
Let t_g7fbo = unit(F7fb_center - G7fb_center).
Let t_bt_out = unit(G7fbo - BT).

| # | Name   | t_in          | t_out         | Kind                    |
|---|--------|---------------|---------------|-------------------------|
| 0 | NB     | —             | e             | corner (leg 3 is line)  |
| 1 | C1sbi  | e             | e             | C1-symmetric horizontal |
| 2 | E2s    | e             | e             | C1-symmetric horizontal |
| 3 | A3s    | TILT45_DR     | TILT45_DR     | C1-symmetric tilted     |
| 4 | E5s    | e             | e             | C1-symmetric horizontal |
| 5 | G7sbi  | t_g7sbi       | t_g7sbi       | C1-symmetric, along G7↔F7 sharp center line |
| 6 | G7sbo  | e             | e             | C1-symmetric horizontal |
| 7 | BT     | e             | t_bt_out      | CORNER (t_in ≠ t_out)   |
| 8 | G7fbo  | t_g7fbo       | t_g7fbo       | C1-symmetric, along G7↔F7 flat center line  |
| 9 | F5f    | w             | w             | C1-symmetric horizontal |
|10 | G2f    | TILT45_DR     | TILT45_DR     | C1-symmetric tilted     |
|11 | F1fbi  | w             | w             | C1-symmetric horizontal |
|12 | NT     | sou           | —             | corner (leg 3 is line)  |

Note: at C1-symmetric interior anchors, the two sides of the anchor
share the same unit tangent vector. The HANDLE LENGTHS on the two sides
are independent (w_in, w_out separately tunable).

SEGMENTS.
12 Bezier segments in traversal order, each a cubic with control points
P0, P1, P2, P3:
    seg_i: P0 = anchor_i,  P3 = anchor_{i+1}
           P1 = P0 + w_out_i  * t_out_i
           P2 = P3 - w_in_{i+1} * t_in_{i+1}
After seg 11 (F1fbi -> NT), Leg 3 closes with a straight line NT -> NB.

TUNABLE PARAMETERS.
For each anchor k (0..12), two per-side half-widths: w_in_k, w_out_k,
both ≥ w_min = 2 mm. NB has no incoming handle; NT has no outgoing
handle — for those, only one half-width is tunable.

Total tunable count:
  - 11 C1-symmetric anchors × 2 widths each = 22
  - 2 corners (BT, G7sbi/G7sbo pair if treated as corners; otherwise BT alone) each with 2 widths = 4  [N.B. the G7sb anchor is split into two separate positions (G7sbi, G7sbo) so it's handled naturally; BT is the only "single-position corner" with t_in ≠ t_out.]
  - NB out-width and NT in-width = 2
  - Total: 24 half-widths (approximate; count exactly by summing segments' endpoint widths).

HARD CONSTRAINTS.

C1. Anchor positions: all 13 anchors at the positions in the table above.
    Not tunable.

C2. Tangent directions: all t_in, t_out as in the table above. Not
    tunable.

C3. Width floor: every tunable w >= w_min = 2.0 mm.

C4. Obstacle avoidance: let B be the set of buffer circle centres
    (flat + sharp) for every string where the corresponding
    `has_*_buffer` flag is True (i.e., buffers not in
    `build_harp.SKIPPED_BUFFERS`). For every sample point q on any
    Bezier segment of p, and for every b in B:
        |q - b| >= R_buffer = 12.0 mm.
    Enforced by sampling each of the 12 Bezier segments at >= 64
    uniform t values and checking every distance.

C5. Closed loop: the 12 Bezier segments followed by the straight line
    Leg 3 (NT -> NB) form a simple closed curve. Self-intersection is
    forbidden.

OBJECTIVE.
Bending energy integrated over the 12 Bezier segments:
    E(p) = sum over segments of integral_0^1 kappa(t)^2 * |p'(t)| dt
Minimise E subject to C1-C5. Approximate via sampling each segment at
>= 64 t-values; compute curvature from the cubic's first and second
derivatives analytically.

If no assignment of widths satisfies C4 (i.e., the anchor/tangent
layout is infeasible), report that fact explicitly along with the
per-segment minimum buffer distances and the identity of the offending
buffer(s).

NOTES.

- Unlike NECK.md (which allowed the solver to route around unvisited
  intermediate buffers), this layout forces the outline to pass exactly
  through each listed anchor with the prescribed tangent. The solver's
  only freedom is the handle lengths, which bend each segment within
  the corridor between consecutive anchors.

- Segments spanning many strings (e.g., C1sbi -> E2s passes 10 strings;
  A3s -> E5s passes 10 strings; F5f -> G2f passes 18 strings) are the
  hardest to satisfy C4 on, because intermediate buffers lie outside
  the span of what any single handle-length tweak can clear. If the
  spec is infeasible, the natural next step is adding intermediate
  anchors on the currently unvisited buffers.

- G7sb is represented as TWO anchors (G7sbi + G7sbo) at two different
  points on the same circle, with a short cubic segment between them.
  This is intentional: it lets the outline transition from the F7-G7
  tangent direction (at G7sbi) to the horizontal-toward-BT direction
  (at G7sbo) without forcing a corner at a single point on G7sb.

- The two 45° tilted anchors (A3s down-right on leg 1, G2f down-right
  on leg 2) were chosen empirically after observing that horizontal
  tangents at those positions left the curve unable to track the
  chain's southward dip through the middle of each leg.

- Hand-built segments from previous iterations (NB -> C1sbs horizontal
  line, ST -> G7fb11 soundboard-slope cubic) are NOT used in this
  layout. The outline is a single 12-segment Bezier chain closed by
  Leg 3, with no pre-locked sub-segments.

- ST (838.784, 481.939) is no longer on the outline; BT replaces it
  as the leg-1/leg-2 corner at the treble end. ST remains a reference
  point for the soundboard endpoint (drawn as a black anchor dot in
  the SVG for orientation).

VERIFICATION.

A reference (polyline) feasible outline is produced by
`neck_geodesic.py` — tangent lines and arcs around every non-skipped
buffer. It is always feasible (no buffer penetrated) but has many more
than 12 anchors. Use it as a bound on the feasible region: any
12-segment Bezier from the PROBLEMv2 layout that crosses a buffer
does so because the chosen anchors/tangents forbid the scallop
necessary to clear that buffer, not because a feasible curve with
these anchors/tangents is impossible in principle.
