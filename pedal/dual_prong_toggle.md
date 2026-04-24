# Dual-prong toggle — research memo

Research candidate to replace the clicky pen at each pitch point on the
treble end. Each toggle is a **single binary device** — ENGAGED or NOT —
just like a clicky pen. The "dual-prong" refers to the yoke shape (two
prongs that press the string from above at one pitch point), not to a
multi-position mechanism. Per string: **one toggle for nat, one for
sharp**, same count as clickies.

**Status:** research only. Clicky pens stay in the current design.

## 1. Mechanical principle

One Ø4 mm shaft vertical through the neck plate, ending in a rigid
**U-shaped yoke** in the string gap. The yoke has two small prongs
straddling the string (3.4 mm prong pitch = string diameter + clearance);
rotating the shaft 90° swings the yoke from parallel-to-string
(DISENGAGED, string passes freely between the prongs) to
perpendicular-to-string (ENGAGED, both prong tips press the string
down against a fixed backstop on the far plywood).

| Position | Shaft angle | Yoke        | Pitch                   |
|----------|-------------|-------------|-------------------------|
| REST     | 0 deg       | clears string | nominal (flat)        |
| ENGAGED  | 90 deg      | clamps string | raised 1 or 2 semitones |

Two positions, bistable detent. The raise amount depends on WHERE along
the string the toggle sits — i.e., at the nat pitch point it raises by
one semitone; at the sharp pitch point by two semitones. **One toggle
per pitch point**, so each string has two toggles (nat + sharp), same
combinatorial options as the clicky design.

## 2. Geometry

- Shaft Ø4 mm, 24 mm long.
- **One Ø5 mm hole per toggle** (replaces clicky's Ø6.5).
- Flange: Ø12 mm round disc, 3 mm thick, 2 × M2 screws.
- Yoke: 6 × 2 × 4 mm, r=0.5 prong tips, prong pitch 3.4 mm.
- Lever: 15 mm radial arm with detent notches at 0° and 90°.
- Per string: **2 toggles × Ø5 = two Ø5 mm holes at the nat and sharp s' positions**.

```
   /--\         thumb lever (0 = rest, 90 = engaged)
  = O =         bistable detent disc
  [====]       flange Ø12
  --||---      plywood, Ø5 hole
    ||          shaft in 12.7 mm gap
   |  |
   [=||=]     yoke, prongs down when engaged
    v v
    o o       r=0.5 contact tips, 3.4 mm apart straddling string
   -----      string (end-on)
```

## 3. Actuation

Ball-and-cup detent at 0° and 90° — two cups, not three. ~2 N force,
clear tactile click. Player flips lever with the thumb between rest
(90° angle to string plane) and engaged (flush against plate edge).
Per-string you flip nat ON or OFF, then sharp ON or OFF, just like
pressing two clickies — same muscle memory, but rotary.

## 4. Comparison to clicky pen

| Metric           | Clicky pen         | Binary toggle              |
|------------------|--------------------|----------------------------|
| Holes / string   | 2 × Ø6.5           | **2 × Ø5**                 |
| States / toggle  | Engaged/flat       | Engaged/flat               |
| Action           | Push-click         | Rotary flick (90°)         |
| F7/G7 fit        | Collides (Ø6.5)    | **Fits** (Ø5 at 3.4 pitch still overlaps 1.6 mm — SEE §5) |
| Mutual exclusion | n/a (independent)  | n/a (independent)          |
| Parts / toggle   | ~6                 | ~5                         |
| Manufacturing    | Near-off-the-shelf | Custom (tight yoke tol.)   |
| Contact          | 16 mm paddle face  | 2 × r=0.5 tip (gentler)    |
| Protrusion       | Flush              | ~8 mm lever proud          |

Main win: smaller hole (Ø5 vs Ø6.5). Main loss: levers clutter the
plate top and could foul a tuning key.

## 5. Integration at F7 / G7

- **Hole map:** G7 nat and sharp pitch points are 3.4 mm apart on the
  string. Clicky Ø6.5 holes overlap 3.1 mm in material (infeasible).
  Toggle Ø5 holes at the same 3.4 mm spacing still overlap by **1.6 mm**
  — reduced but not eliminated.
- **To eliminate overlap**, shrink the toggle hole to Ø3.4 (zero overlap,
  tangent) or rethink at F7/G7 specifically (merge both toggles into a
  single 3-position device — the original memo's approach).
- **Recommend:** use Ø5 binary toggles for strings where 2 × Ø5 fits
  (≤ C7 or so), and the 3-position merged toggle ONLY where needed
  (F7, G7, possibly E7). Incremental deployment.
- **Shoulder features clear:** flange sits inboard of tongue line;
  yoke is 4 mm tall in the 12.7 mm gap; diffuser and treble scoop
  are on the shoulder UNDERSIDE, yoke is in the NECK gap — no physical
  intersection at G7.

## 6. Open questions

1. **Hole-diameter vs yoke stiffness** — can a Ø3.4 shaft + Ø3 yoke
   survive >10k flips against ~2.8 N string restoring force?
2. **Bistable detent feel** — 2-cup vs 3-cup bench test; is 2-state
   enough haptic feedback to avoid mid-flip confusion?
3. **Lever swing arc** — 90° per engagement is a bigger gesture than a
   clicky push-click; slower or faster in practice?
4. **Deployment scope** — which strings get toggles vs clickies? Driven
   by the per-string hole-overlap map, not a uniform choice.
5. **Mixed deployment UX** — does having clickies on bass strings and
   toggles on treble strings confuse muscle memory, or is it a clear
   per-hand regional split?
6. **Acoustic decay** — yoke has less mass and smaller contact area
   than a clicky paddle; does this change damping? Single-string mic test.
