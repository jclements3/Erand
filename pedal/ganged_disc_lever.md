# Ganged disc-lever — design memo

Alternative pitch-change mechanism replacing per-string clicky pens (or
per-string disc toggles) with **hand-pull levers at the base of the
neck**, each lever controlling all strings of one pitch class through a
rigid rod running along the outboard plate face. Inspired directly by
pedal-harp action — same mechanical principle (rod → bell-crank → disc
rotation at each pitch point) — but hand-operated instead of
foot-pedalled.

**Status:** design memo. Not integrated into the build. Competes with
the per-string disc toggle in `dual_prong_toggle.md` for the
pitch-change mechanism slot.

## 1. Summary

- **Per-string actuator:** the same disc-capture toggle documented in
  `dual_prong_toggle.md` (Ø10 disc inside the 12.7 mm plate gap, Ø3
  axle through the plate, two Ø1.5 pegs that swing into the string's
  rest lane when the disc rotates 180°).
- **Ganging:** each axle's outboard end has a crank arm (2 mm radial).
  A rigid rod along the outboard plate face connects the crank tips of
  all discs belonging to a single pitch class (all Cs, all Ds, etc.).
  Pulling the rod moves all crank tips together; each axle rotates
  180°; all linked discs engage or disengage simultaneously.
- **Actuation:** 7 hand levers at the base of the neck (one per pitch
  class C / D / E / F / G / A / B). Pull UP to engage, push DOWN to
  disengage. Bistable detent at each disc holds state between moves.
- **UX:** matches pedal harp convention — pitch-class at a time, one
  gesture changes all Cs across octaves. Fundamentally different from
  per-string toggles which give per-string independence.

## 2. Mechanical scheme

```
       ╭─────────────────────────────────────────────────╮
       │              NECK (viewed outboard)              │
       │                                                   │
       │   ╭──●──╮  ╭──●──╮  ╭──●──╮  ╭──●──╮  ╭──●──╮   │
       │   │ ⊗  │  │ ⊗  │  │ ⊗  │  │ ⊗  │  │ ⊗  │  ...  │  ← discs
       │   ╰──●──╯  ╰──●──╯  ╰──●──╯  ╰──●──╯  ╰──●──╯   │    (crank
       │                                                   │     tip ●
       │     A       B       C       D       E   ...       │     linked
       │     ║       ║       ║       ║       ║             │     to rod)
       │     ║       ║       ║       ║       ║             │
       │ ════╬═══════╬═══════╬═══════╬═══════╬════════════│
       │   rods, one per pitch class, run along outboard   │
       │   plate face; each rod connects to its class's    │
       │   discs via a bell crank at each disc             │
       │     ║       ║       ║       ║       ║             │
       │     ▼       ▼       ▼       ▼       ▼             │
       │  ╔═══╗   ╔═══╗   ╔═══╗   ╔═══╗   ╔═══╗           │
       │  ║ A ║   ║ B ║   ║ C ║   ║ D ║   ║ E ║           │
       │  ╚═══╝   ╚═══╝   ╚═══╝   ╚═══╝   ╚═══╝           │
       │   ↕       ↕       ↕       ↕       ↕               │
       │        lever bank (base of neck)                   │
       ╰─────────────────────────────────────────────────╯
```

**Single pitch class (e.g., all Cs):**

- 6 or 7 strings in the class (C1 through C7 — varies by pitch range).
- Each has a disc + crank + detent on the outboard plate face.
- One rigid thin CF rod connects their crank tips.
- Rod runs along the plate's outboard surface, pivoting on a pulley
  or guide at each disc.
- Rod terminates in a bell crank at the base that couples to the
  hand lever.

**Per class:**
- 1 lever
- 1 rigid rod (~1.6 m long, CF, Ø1-2 mm)
- 6-7 discs + crank arms

**Total:**
- 7 levers (one per pitch class)
- 7 rods
- 47 discs + crank arms
- If double-action (nat AND sharp raises like a pedal harp): 14 levers
  or 7 three-position levers driving 14 rods (nat rod + sharp rod per
  class). Doubles the rod count.

## 3. Rod-to-disc linkage (bell crank)

At each disc, the rigid rod (which runs along the neck, parallel to
the plate edge, perpendicular to each disc axle) is converted to
axle rotation via a bell crank:

```
  rod direction →
                 ●          ← rod attachment (crank tip)
                 │
            ─────●─────      ← bell-crank arm, 2 mm
                 ⊗          ← axle (Ø3, rotates when arm pivots)
            ─────●─────      ← other side of crank (detent cup)
                 │
                 │
              (axle extends
               through plate
               to disc inside
               the gap)
```

When the rod moves along its length by ~6.3 mm (= π × crank-tip-radius),
the crank arm swings 180°, rotating the axle 180°, rotating the disc
from DISENGAGED to ENGAGED (or back).

Rod stroke for full engagement = **~6.3 mm**. Lever at the base
multiplies this to a comfortable hand gesture (say, 50 mm lever
travel) via a mechanical advantage of ~8:1.

## 4. Bistable detent per disc

Each axle has a ball-and-cup bistable detent between the outboard
plate face and the disc's outboard end (or between the crank arm and
a fixed part of the plate). Two cups 180° apart, Ø2 mm ball, light
spring, ~1.5 N detent force.

**Function:** once the rod has pushed past the detent's center, the
disc SNAPS into the next stable state and STAYS there. The player
flicks the lever at the base, then lets go — the lever returns to rest
but the discs stay engaged until the next flick.

The lever itself might also have a detent. Or the lever is free-
swinging and the discs' collective detent torque (7 discs × 1.5 N ≈
10 N on the rod, ÷ 8:1 advantage = 1.25 N at the lever) is what
resists spurious lever motion.

## 5. Actuation force and travel

**Per disc:** 1.5 N detent × 2 mm crank radius = 3 N·mm torque needed
to flip. Detent force at rod = 1.5 N pulling tangent to crank.

**Per pitch class (7 discs):** 7 × 1.5 = 10.5 N peak force at the rod
during the detent crossover.

**At the lever:** 8:1 mechanical advantage → 10.5 / 8 = **1.3 N peak
at the lever** — well within comfortable single-finger pull force.

**Lever travel:** 6.3 mm rod × 8 = **50 mm lever travel**. Equivalent
to a small organ stop or a piano damper pedal — comfortable single
gesture.

## 6. Comparison to per-string disc toggle

| | Per-string toggle | Ganged lever (this memo) |
|---|---|---|
| Control granularity | One disc at a time | Whole pitch class at a time |
| Musical theory model | Free/chromatic/experimental | Key modulation (pedal harp) |
| Speed during play | Slow (47 thumbs) | Fast (7 levers) |
| Complexity | 47 discs + 47 detents + 47 knobs | 47 discs + 47 bell cranks + 7 rods + 7 levers + 7 detent systems |
| Rods along neck | None | **7** (or 14 for double-action) |
| Levers | 47 individual knobs | 7 hand levers at base |
| Per-string override | Native | **Lost** — can't engage single C without all Cs |
| Failure mode | Single disc stops working (local) | Rod jam/stretch → whole class affected |

## 7. Tradeoffs

**Why you'd choose ganged levers:**
- You want pedal-harp-style modulation UX without foot pedals.
- You play tonal music where pitch-class operations dominate.
- Fast key changes matter more than per-string weirdness.
- Want the bottom-of-harp lever bank aesthetic.

**Why you'd stick with per-string toggles:**
- You want individual-string pitch control (experimental music,
  microtonal, per-string alterations).
- You want minimum mechanical complexity.
- You don't want rods running along the outboard plate face.

**Why you might do BOTH:**
- Per-string toggles AS WELL as ganged levers — the levers drive all
  discs of a class, but each disc can also be individually
  thumb-overridden. Requires a slip-clutch or declutch mechanism at
  each bell crank so the rod doesn't fight the individual disc.
  Complex but maximally flexible.

## 8. Open questions

1. **Rod material**: CF rod (stiff, light, expensive) vs steel rod
   (classical, heavier, cheaper). Pedal harps use steel.
2. **Bell crank design**: 90° elbow with two arms, or rack-and-pinion,
   or eccentric cam? Pedal harps use two-arm elbows; rack-pinion
   would give smoother action.
3. **Rod routing**: on the plate's outboard face (visible) vs hidden
   between a cover plate and the neck plate. Pedal harps hide the rods
   inside the column and neck.
4. **Lever design**: simple up-down toggle lever, or rotating quadrant
   (like a pedal harp pedal with flat/nat/sharp positions)?
5. **Double-action (flat/nat/sharp)**: single-action (engaged/flat)
   vs double-action (flat/nat/sharp via three-position lever). Double
   action doubles rod count and lever complexity but matches standard
   harp notation conventions.
6. **Per-string override compatibility**: is individual disc override
   worth the slip-clutch complexity, or accept that this design
   surrenders per-string control entirely?

## 9. Summary decision table

| If you want | Use |
|---|---|
| Tonal / key-based music, fast modulation | Ganged levers (this memo) |
| Experimental / per-string / microtonal | Per-string disc toggles |
| Both | Ganged + slip-clutch override (most complex) |
| Simplest / prototype | Clicky pens (current build) |

**Recommendation**: ganged levers are the RIGHT answer for a pedal-
harp-convention harp and solve the F7/G7 overlap (the individual disc
at G7 never needs to be reached by a thumb). If the acoustic design
direction is pedal-harp-equivalent playability, build this. If the
design direction is experimental instrument, stay with per-string.
