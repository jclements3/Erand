# Neck-design status

Handoff notes for the next Claude Code session working on the neck. Everything
else lives in the code; this file covers only what the code doesn't already say.

## Canonical state of `erand47.svg`

`erand47.svg` currently shows the **full Bezier neck** produced by
`leg2_bezier.py`:

- Leg 1 (NB → ST, south side):
  - one hand-constructed NB→C1sbs segment (straight horizontal cubic),
  - ~34 Schneider segments C1sbs → ST through the offset geodesic polyline.
- Leg 2 (ST → NT, north side):
  - one hand-constructed ST→G7fb11 segment,
  - ~36 Schneider segments G7fb11 → NT.
- Leg 3 (NT → NB): straight line down the column.
- Min buffer distance: 12.00 mm (strict feasible — no curve sample inside
  any buffer's R=12 radius).

A smoother alternative, `erand47_dec_n20.svg`, has 19-segment leg 1 +
same leg 2. Min distance 11.51 mm (0.49 mm cosmetic penetration, below
saw-kerf precision). Produced by `decimate.py`; not the default.

## How to regenerate the neck

```bash
python3 build_harp.py       # emits erand47.svg with strings / buffers / anchors
python3 leg2_bezier.py      # overwrites the pink neck with the Bezier fit
```

The sweep (`sweep.py`) and decimation (`decimate.py`) scripts are
exploratory — they emit their own `erand47_*_.svg` variants but do NOT
need to rerun unless you're investigating a tradeoff.

## Design-locked constraints (encoded in `leg2_bezier.py`)

These are fixed decisions from the user. Don't re-litigate:

- **NB exit handle** = +east `(1, 0)`, length = `L_nb = 2 * L_c1`. Mirrors
  the ST / G7fb11 setup on leg 2.
- **C1sbs** = south pole of the bass-most sharp buffer `(x_c1sb, NB[1])`,
  computed from `bh.build_strings()[0]['sharp']` (first in bass-to-treble
  order). The tangent line from NB to C1 sharp is horizontal because
  NB's y is chosen to equal the buffer's south-pole y.
- **C1sbs handle at entry** = `C1sbs + L_c1 * (-1, 0)`, so the curve's
  tangent at C1sbs is `+east`, matching the natural tangent of the C1
  sharp circle at its south pole. `L_c1 = 40 mm`, `L_nb = 80 mm` —
  mirrors `L_g7 = 40`, `L_st = 80` on leg 2.
- **NB → C1sbs hand-built segment**. Not re-fit. Because both anchors
  have the same y and both tangents are east, this cubic is a straight
  horizontal line at `y = NB[1] = 323.844`.
- **ST exit handle** = +SOUNDBOARD_DIR (up-right, along soundboard extension),
  length = `L_st = 2 * L_g7`.
- **G7fb11** = the point on the G7 flat buffer where the circle's tangent
  is parallel to the soundboard slope, on the upper-left (~10–11 o'clock)
  side. Computed in code as `G7fb_center + R * perp(SOUNDBOARD_DIR)`, with
  the perpendicular chosen to point upper-left.
- **G7fb11 handle at entry** = `G7fb11 + L_g7 * SOUNDBOARD_DIR`, so the
  curve's tangent at G7fb11 is `-SOUNDBOARD_DIR` (matches the natural
  tangent direction for traversing the north side of the G7 flat buffer
  east-to-west).
- **L_g7 = 40 mm** currently; `L_st = 80 mm`. User has tried 20/40 ("better"),
  40/80 ("better" → doubled), 60/120 ("flipped again" complaint after
  tripling). 40/80 is the approved state. Sub-multiples / multiples of the
  2:1 ratio are tuneable.
- **Leg 2 geodesic polyline offset = 0.6 mm outward** before Schneider fit,
  providing the margin that keeps the Bezier outside every buffer.
- **NB, NT, ST are corners**. They do NOT enforce smooth tangent continuity
  across leg boundaries. The only locked mid-leg tangent is at G7fb11.

## Open thread: BT (Box Top)

User introduced this near the end of the session and did not finalize:

> *"A new point BT for box top. The horizontal from G7sb will extend past ST
> and to BT."*

- The horizontal line `y = 481.94` passes exactly through ST and through
  the south pole of the G7 sharp buffer (G7 sharp center y = 469.94,
  south pole y = 481.94). So ST lies on this natural horizontal.
- BT sits further **right** along this line, at an unspecified x.
- When BT's x is finalized: add `BT = (x, 481.939)` to `build_harp.py` and
  extend the neck path to terminate at BT (leg 2 becomes ST→BT, and the
  old leg 2 becomes BT→NT; or similar).

## SKIPPED_BUFFERS convention

In `build_harp.py`, `SKIPPED_BUFFERS` is a set of `(string_num, "flat"|"sharp")`
tuples. When user says things like:

- "remove a2fb" → add `(13, "flat")` (A2 is string #13)
- "remove c5s" → add `(29, "sharp")` (C5 is string #29)
- "remove d2s d5s" → add `(9, "sharp"), (30, "sharp")`

String numbering is bass-to-treble, scientific pitch notation (octave
increments at C): C1=1, D1=2, …, G1=5, A1=6, B1=7, C2=8, …, G7=47.

## Soundbox integration

`soundbox/geometry.py` is the authoritative source of truth for
shared geometry (CO, CI, ST, NT, NB, floor, limaçon taper, clipping
planes). The neck chat must not change any of those points; see
`soundbox/interfaces.md` for what's owned where.

**Naming**: The pre-handoff `CO` has been renamed to `CI` (column inner,
x = 51.7, y = 1741.51). The new `CO` is the column outer × extended
soundboard slope point on the floor plane (x = 12.7, y = 1803.91).
`SOUNDBOARD_DIR` unit vector is unchanged by the rename (both CO and CI
are collinear on the soundboard slope).

Mold DXFs and build instructions live under `soundbox/mold/` and
`soundbox/construction.md` — touch only if the neck design forces a
soundbox geometry change (which would trigger a joint conversation per
`interfaces.md` §3).

## Failed attempts (don't repeat)

`fitneck5.py` through `fitneck8.py` tried constrained nonlinear optimization
with `scipy.optimize.minimize(trust-constr)`:

- **fitneck5/6**: 3 interior anchors per leg; infeasible warm start; solver
  did not converge (leg 2 had 2–10 infeasible constraints after 2000 iter).
- **fitneck7**: geodesic polyline warm start (feasible as polyline, not
  as Bezier); bilateral penalty objective. Worse than fitneck6.
- **fitneck8**: corridor half-plane constraints from geodesic polyline.
  Crashed silently (stdout buffering interaction).

Root causes of failure were (a) infeasible Bezier warm start even when
polyline was feasible, (b) hard constraints went singular when samples
landed on the same buffer, (c) objective clipped penetrations to zero
leaving no gradient inside buffers.

Current `leg2_bezier.py` side-steps these by using Schneider's fit
through a polyline with a small outward offset. It's not a min-curvature
optimizer, but it gives a clean feasible Bezier with minimal fuss.

## User feedback patterns

- Terse responses; no promises ("this will work"); ship one working thing
  or say clearly that you couldn't.
- Don't re-litigate settled design decisions (NB y-coord, ST location,
  soundboard angle, G7fb11 tangent locked to soundboard slope). If
  something looks wrong, read the comments in `build_harp.py` first.
- "Fast car / slow car" mental model: fewer nodes = faster = smoother
  racing line. More nodes = slower = tight hug around every buffer.
- Safe floor if Bezier fails: `python3 neck_geodesic.py`. Scalloped but
  guaranteed feasible (tangent lines + arcs by construction).
