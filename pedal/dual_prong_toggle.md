# Dual-prong toggle — research memo

Research candidate to replace the per-string clicky-pen stack at the
treble end. Problem: at F7/G7 the nat and sharp pitch points sit
~3.4 mm apart, so the current design's two Ø6.5 mm clicky holes overlap
in material. `pedal/dual_clicky.svg` works around this with two clickies
on a shared flange; the toggle replaces **both** clickies with a single
rotary element through **one** hole.

**Status:** research only. Clicky pens stay in the current design.

## 1. Mechanical principle

One Ø4 mm shaft vertical through the neck plate, ending in a rigid
**bi-prong yoke** in the string gap — a cross-bar 3.4 mm wide with two
downward prongs (nat south of axis, sharp north). A face-cam detent
disc above the plywood locks the shaft in three rotational stops:

| Pos | Shaft angle | Prong down         | Pitch |
|-----|-------------|--------------------|-------|
| CCW | -30 deg     | neither (retracted)| flat  |
| 0   |  0 deg      | nat prong          | nat   |
| CW  | +30 deg     | sharp prong        | sharp |

The flat cup sits 0.6 mm deeper than nat/sharp, so rotating CCW lifts
the whole yoke clear of the string. Nat and sharp cups are equal-depth:
swinging between them slides one prong off and the other on without
height change. **Three pitches, mutually exclusive by construction.**

## 2. Geometry

- Shaft Ø4 mm, 24 mm long.
- **One Ø5 mm hole per string** (replaces clicky's 2 x Ø6.5).
- Flange: Ø14 mm round disc, 3 mm thick, 2 x M2.5 screws.
- Yoke: 6 x 3 x 4 mm, r=0.8 nose pins, prong pitch 3.4 mm (= G7 nat↔sharp).
- Lever: ~20 mm radial arm on top of shaft.
- Envelope: Ø14 x 18 mm above plywood; 6 x 3 x 4 mm yoke in the gap.

```
   /--\        thumb lever
  = O =        detent disc (flat/nat/sharp cups)
  [====]      flange Ø14
  --||---     plywood, Ø5 hole
    ||        shaft in 12.7 mm gap
   /  \
  [n][s]      yoke, 3.4 mm prong pitch
   v  v
   o  o       r=0.8 contact tips
  ------      string (end-on)
```

## 3. Actuation

Ball-and-cup detent inside the flange: Ø2 mm ball, small spring, three
cups 30 deg apart on the underside of the rotating disc. Detent force
~2-3 N — tactile click, no accidental bumps. Thumb flips the lever:
flat↔nat one click, nat↔sharp one click, flat↔sharp two clicks. All
three positions stable. State visible from lever angle.

## 4. Comparison to clicky pen

| Metric           | Clicky pen         | Dual-prong toggle       |
|------------------|--------------------|-------------------------|
| Holes / string   | 2 x Ø6.5           | **1 x Ø5**              |
| States           | 4 combos, 2 useful | 3 exclusive             |
| Action           | Two push-clicks    | One rotary flick        |
| F7/G7 fit        | Collides           | Clears                  |
| Speed            | Slower             | Faster                  |
| Mutual exclusion | Player's job       | Mechanical (rigid yoke) |
| Parts            | ~12 (two stacks)   | ~6                      |
| Manufacturing    | Near-off-the-shelf | Custom, tight yoke tol. |
| Contact          | 16 mm paddle face  | r=0.8 tip (gentler)     |
| Protrusion       | Flush              | ~10 mm lever proud      |

Main loss: levers clutter the top of the north plywood and could foul
tuning-key swing. So toggles only go where clickies can't fit
(F7, G7; maybe D7/E7). The rest stay clickies — incremental fix.

## 5. Integration at F7 / G7

- **Hole map:** G7 nat and sharp buffers are 3.4 mm apart. Clicky's two
  Ø6.5 holes overlap 3.1 mm. Toggle's single Ø5 hole at their midpoint
  sits well inside G7's 17.4 mm pitch allotment.
- **Shoulder tongue-and-groove** (tongue 2 x 8 mm): flange on north
  plywood sits inboard of the tongue line — clear.
- **Shoulder diffuser** (R=250, d=15, shoulder underside): yoke is 4 mm
  tall in the 12.7 mm gap, >20 mm from the diffuser. Clear.
- **BT treble scoop** (paraboloid r=30, d=12, BT-anchored): G7 sharp is
  ~7 mm north of BT, near the scoop rim. The scoop is on the shoulder
  underside; the yoke is in the neck gap, so they don't physically
  intersect — **confirm with a layout sweep** since the y-ranges overlap.

## 6. Open questions

1. Yoke durability — does Ø4 shaft + 6 mm yoke survive >10k flips
   against ~2.8 N string restoring force without yaw backlash?
2. Cross-talk during flip under tension — does sharp drop on cleanly
   as nat lifts off, or is there a mid-rotation click artefact?
3. Detent profile — centre-biased (nat as rest) or symmetric? Bench test.
4. Lever direction — CW=sharp on all strings, or mirrored by hand reach?
5. Deployment scope — toggle only G7, or F7+G7, or all treble? Driven
   by the per-string hole-overlap map.
6. Acoustic decay — r=0.8 prong vs r=0.8 clicky paddle pin: contact
   identical, but does yoke mass change damping? Single-string mic test.
