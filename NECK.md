Fit the neck outline of the Clements 47 harp: a closed piecewise cubic Bezier
path around a set of circular buffer obstacles, with specific locked anchors,
tangent angles, and handle lengths.

COORDINATE FRAME.
SVG convention: x increases to the right, y increases DOWNWARD. Lengths in
millimeters. Angles in radians: angle 0 points +x, angle +pi/2 points +y
(downward on screen).

PROBLEM.
Find the piecewise cubic Bezier outline p of the harp neck. p is a closed
loop subdivided into three legs by corner anchors NB, ST, NT. Two interior
waypoints (C1sbs on leg 1, G7fb11 on leg 2) are locked. Two segments
(NB->C1sbs, ST->G7fb11) are pre-defined straight/slope cubics ("hand-built"
segments). The remaining two portions are tunable piecewise cubic Bezier
curves of N >= 1 segments each. Minimize a smoothness objective subject to
hard obstacle-avoidance and tangent-locking constraints.

HARD CONSTRAINTS.

C1. Locked anchor positions (all in mm):
    NB     = (12.700, 323.844)   # column outer, base of neck
    NT     = (12.700, 146.563)   # column outer, top of neck
    ST     = (838.784, 481.939)  # soundboard top
    C1sbs  = (x_c1, 323.844)     # south pole of bass-most sharp buffer
    G7fb11 = G7fb + 12 * perp(SOUNDBOARD_DIR)   # tangent point on G7 flat buffer
    where x_c1 is the x-coordinate of the bass-most sharp buffer center
    (from build_harp.build_strings()), G7fb is the G7 (last) flat buffer
    center, and SOUNDBOARD_DIR is the unit vector from CO=(12.7, 1803.91)
    to ST. The perpendicular in the G7fb11 definition is chosen to point
    upper-left (both components negative in SVG).

C2. Locked tangent angles at named anchors:
    NB exit          = 0                (east, +x)
    C1sbs in, out    = 0                (east, +x) — tangent to C1 sharp buffer at its south pole
    ST exit          = angle(+SOUNDBOARD_DIR)
    G7fb11 in, out   = angle(-SOUNDBOARD_DIR)  (tangent to G7 flat buffer at G7fb11)
    NT in            = pi/2             (south, +y — matches leg 3 down the column)

C3. Locked handle lengths:
    L_nb  = 80 mm     (NB exit handle)
    L_c1  = 40 mm     (C1sbs incoming handle, also outgoing for C1 continuity)
    L_st  = 80 mm     (ST exit handle)
    L_g7  = 40 mm     (G7fb11 incoming handle, also outgoing for C1 continuity)
    Pattern: the junction-exit handle from a corner anchor (NB, ST) is
    twice the incoming handle at the downstream interior waypoint (C1sbs,
    G7fb11). These are the "user-approved" values per NECK_STATUS.md;
    sub-multiples / multiples of the 2:1 ratio are tuneable if needed.

C4. Hand-built (pre-defined, non-optimized) segments:
    Segment NB->C1sbs: one cubic with
        P0 = NB
        P1 = NB + L_nb * (1, 0)
        P2 = C1sbs + L_c1 * (-1, 0)      (so incoming tangent at C1sbs = +east)
        P3 = C1sbs
    Segment ST->G7fb11: one cubic with
        P0 = ST
        P1 = ST + L_st * SOUNDBOARD_DIR
        P2 = G7fb11 + L_g7 * SOUNDBOARD_DIR  (so incoming tangent at G7fb11 = -SOUNDBOARD_DIR)
        P3 = G7fb11
    These segments are not tunable. Both are geometrically straight in the
    current L_nb = 2 * L_c1, L_st = 2 * L_g7 ratio: their two anchors are
    collinear with the tangent direction, and the handles lie on that line.

C5. Tunable portions (two):
    Portion A: C1sbs -> ST, on the SOUTH side of the sharp-buffer chain
               (excluding the bass-most sharp whose tangency is handled
               by the NB->C1sbs hand-built segment).
    Portion B: G7fb11 -> NT, on the NORTH side of the flat-buffer chain
               (excluding the G7 flat whose tangency is handled by the
               ST->G7fb11 hand-built segment).

    Each portion is a piecewise cubic Bezier with N_A (resp. N_B) segments
    and N_A + 1 (resp. N_B + 1) anchors. The first and last anchors are
    fixed by C1/C2/C3 (C1sbs, ST for portion A; G7fb11, NT for portion B).
    Interior anchors are tunable.

C6. C1 continuity within each tunable portion:
    Interior anchors carry a single (angle, width) pair; incoming and
    outgoing handles are collinear and equal in length (full C1
    continuity). Corners NB, ST, NT do NOT enforce C1 across leg
    boundaries.

C7. Width floor:
    All tunable widths w_i >= w_min = 2.0 mm.

C8. Obstacle avoidance:
    Let B be the set of buffer circle centers (flat + sharp) on strings
    with has_flat_buffer / has_sharp_buffer set True in
    build_harp.build_strings(). Every sample point of p on any tunable
    portion must satisfy Euclidean distance to every b in B of at least
    R_buffer = 12.0 mm. Enforced by sampling each tunable segment at
    >= 64 uniformly spaced t values and checking distance to every center.

C9. Closed loop:
    The outline closes via Leg 3 (NT -> NB), which is a straight line on
    x = 12.7 (the column outer). Not tunable. Included in the output
    path for completeness but not in the optimization.

C10. One-sided attack:
    Portion A lies entirely on the SOUTH side of the sharp-buffer chain
    (each sample has signed normal distance to the geodesic outline >= 0).
    Portion B lies entirely on the NORTH side of the flat-buffer chain.
    Equivalent to the one-sidedness constraint from CURVE_FITTING_PROBLEM
    with the geodesic polyline as reference. Enforced to prevent the
    curve from crossing through the buffer chain into the neck interior.

TUNABLE PARAMETERS.
For each tunable portion with N segments (N+1 anchors of which 2 are
locked, so N-1 free interior anchors):
    - Positions of N-1 interior anchors: 2(N-1) numbers.
    - Tangent angles at N-1 interior anchors: N-1 numbers (endpoint angles
      are locked by C2).
    - Half-widths at N-1 interior anchors: N-1 numbers.
    - Optionally the locked-anchor outgoing widths (if not locked by C3):
      w_C1sbs_out and w_ST_entry for portion A, w_G7fb11_out and w_NT_in
      for portion B. By default these are freed and tuned; L_c1 and L_g7
      stay fixed on the hand-built side.
Total per portion: 4(N-1) + 2 free widths = 4N - 2 numbers.

OBJECTIVE.
Bending energy:
    E(p) = sum over tunable segments of integral_0^1 kappa(t)^2 * |p'(t)| dt
    where kappa is the signed curvature of the cubic Bezier segment.
Approximated by sampling each segment at >= 64 t-values; differentiation via
finite differences on the sample points is sufficient given the analytic
derivatives of the cubic. Minimize E subject to C1-C10.

Rationale: bending energy favors a smooth "racing line" that takes the
straightest reasonable path around the buffer chain. Unlike the area
objective of CURVE_FITTING_PROBLEM, bending energy has no |A_signed|
cancellation hole. It penalizes sharp turns directly, making the
obstacle-avoidance constraint the only way to produce scallops.

INSTANCE — erand47 neck.

Obstacle data is produced by running `python3 build_harp.py`. The 47
strings each contribute up to 2 buffer centers (flat, sharp) at positions
computed from the physical pedal-disc engagement geometry in build_harp.py.
Certain (string_index, "flat"|"sharp") pairs are in SKIPPED_BUFFERS and
contribute no obstacle (but are still rendered as circles for reference).

The buffers to AVOID (B in C8) are exactly the ones with has_*_buffer=True
after SKIPPED_BUFFERS is applied. The tangent-point waypoints are:
  - C1sbs uses the bass-most sharp buffer in B.
  - G7fb11 uses the treble-most flat buffer in B.

Derived quantities (mm):
  SOUNDBOARD_DIR = (0.5299, -0.8480)     # unit, CO -> ST
  angle(SOUNDBOARD_DIR) = -1.0123        # radians, ~-58 deg
  angle(-SOUNDBOARD_DIR) = +2.1293       # radians, ~+122 deg
  Approx arc length portion A (C1sbs -> ST) ~ 850 mm
  Approx arc length portion B (G7fb11 -> NT) ~ 800 mm

OUTPUT.
For each tunable portion (A and B):
1. The interior-anchor parameter list: for each of N-1 free anchors,
   (x, y, a, w). Plus the 2 endpoint widths if freed.
2. Final bending energy E, reported to at least 4 significant figures.
3. Minimum buffer distance min_{q in p, b in B} |q - b|, reported in mm.
   Must be >= 12.0 (strict), or >= 11.95 if the kerf tolerance from
   `neck_geodesic.py` is accepted.
4. A self-contained SVG artifact `erand47_neck.svg` showing:
   - All strings and buffer circles as in `erand47.svg`.
   - The closed neck outline (portion A + NB->C1sbs hand segment +
     portion B + ST->G7fb11 hand segment + NT->NB straight line) as a
     single stroked path, stroke #ff69b4, stroke-width 1.6.
   - Interior anchors of each tunable portion as filled black dots r=2.
   - Control-point handles rendered as dashed lines + open circles
     (same style as leg2_bezier.py).
   - No external references, no CSS classes, no scripts.

NOTES.

- The current `leg2_bezier.py` uses Schneider's fit through an offset
  geodesic polyline. That approach produces ~30-35 segments per tunable
  portion. A solution to this problem with, say, N_A = N_B = 4 would give
  a smoother 4-segment-per-portion curve — the "fast racing line"
  formulation from NECK_STATUS.md's user-feedback section.

- A safety margin during optimization (d_target > R_buffer by 0.2-0.5 mm)
  prevents the solver from oscillating at the constraint boundary; validate
  at the strict R_buffer = 12.0 threshold. Same lesson learned in
  CURVE_FITTING_PROBLEM.

- The hand-built NB->C1sbs and ST->G7fb11 segments are locked because
  the user has already chosen their geometry; re-litigating them is out
  of scope. L_g7 = 40, L_st = 80 are the user-approved values (see
  NECK_STATUS.md "Design-locked constraints").

- SKIPPED_BUFFERS lives in build_harp.py; updating it changes both the
  obstacle set and what the neck has to wrap around. Coordinate changes
  with the user via the "remove xNfb / xNsb" shorthand documented in
  NECK_STATUS.md.
