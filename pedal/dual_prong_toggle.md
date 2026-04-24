# Dual-prong toggle — research memo

Research candidate to replace the clicky pen at each pitch point on the
treble end. The mechanism is modelled on the **real pedal-harp disc**:
a flat rotating disc with two pegs on its face that **grip the string
between them** when engaged. The string is caught between the pegs,
which become the new vibrating-length boundary. Binary operation:
**pegs straddling the string (engaged)** or **pegs rotated clear of
the string path (disengaged)**. Per string: one disc at the nat pitch
point + one disc at the sharp point, same count as clickies.

**Status:** research only. Clicky pens stay in the current design.

## 1. Mechanical principle

Flat brass disc rotating on a single central axle through the neck
plate. Two small cylindrical pegs protrude from the disc's front face,
symmetrically offset from the axle so they straddle a string lane when
the disc is rotated into engagement. Rotating the disc ~90-180° from
engaged position swings **both pegs clear** of the string, letting it
run straight; rotating back **captures the string between the pegs**,
bending it at the peg-tip contacts. The peg contacts become the new
effective pivot — exactly how 20th-century pedal harps raise a string
by a semitone.

| Position    | Disc angle | Pegs vs string lane   | Pitch              |
|-------------|------------|-----------------------|--------------------|
| DISENGAGED  | 0 deg      | Both pegs aside       | nominal (flat)     |
| ENGAGED     | ~180 deg   | Both pegs straddle    | raised (nat or sharp) |

Critical difference from the earlier "yoke press" design: **the pegs
do not press the string against a backstop**. The string wedges between
the two pegs; the pegs are the new pivot. No axial force through the
plate; the disc can be thin. The engagement angle is not critical — any
rotation that brings both pegs to straddle the string's rest line
catches it. Raise amount depends on WHERE along the string the disc
sits: at the nat pitch point → +1 semitone; at the sharp pitch point →
+2 semitones.

## 2. Geometry

- Disc: Ø14 mm, 1.5 mm thick, brass or molded filled nylon, knurled rim.
- Axle: Ø3 mm through the neck plate — **one Ø3 mm hole per pitch point**.
- Disc is mounted so its **top edge protrudes ~3 mm above the plate top
  edge** — the protruding knurled arc is the user-facing control.
- Pegs: two Ø1.5 mm cylinders standing 3 mm proud of disc face, tip
  radius r=0.5, offset 2.5 mm from disc center on opposite sides of a
  diameter. Peg pitch (distance between pegs) = 5 mm.
- Per-string envelope: Ø14 × 1.5 mm disc straddling the plate top edge,
  ~3 mm above and ~11 mm below the plate edge; Ø3 axle hole; two pegs
  in the 12.7 mm string gap.

```
               ○○○○○      ← knurled disc rim (3 mm above plate top)
              ╱ ╲           thumb rolls this directly
   plate top ─────────────────────
             │  ●  │        ← disc body below plate top
             │ ╱ ╲ │            (axle at disc center, pegs straddle
             │●   ●│             symmetrically)
     plate ═══════════════════
                     ↓
                string gap (12.7 mm)
                  pegs .  .     ← pegs project 3 mm into gap,
                                   swinging through the string's
                                   rest lane as the disc rotates
                  string ──
```

Key point: **no barrel on the outboard face, no lever, no push rod.**
The disc itself is the control surface. User rolls the knurled rim with
a thumb, exactly where a fingertip naturally lands resting above the
string.

## 3. Actuation

**Direct thumb-wheel rotation of the disc's knurled rim.** No
intermediate mechanism — no cam, no push, no lever. Thumb contacts the
3 mm of disc edge protruding above the plate top and rolls it forward
or backward, exactly like a volume knob or a mouse scroll wheel.

Ball-and-cup bistable detent INSIDE the plate (under the disc, against
the inboard face): two cups 180° apart, Ø2 mm ball, light spring.
Detent force ~1.5 N — just enough for a tactile click, low enough to
flick with minimal thumb effort. No axial preload required because the
pegs capture the string without pressing against a backstop — the disc
only needs torque to swing, not force.

**Rotation per engagement = 180°.** Half a turn to go from DISENGAGED
(pegs parallel to string) to ENGAGED (pegs straddling string). The 180°
swing is fast — finger-flick distance ~22 mm along the disc rim.

Why this beats a push-cam:

- **Fewer parts** (disc + axle + detent + knurl), all integrated in one
  component — no separate barrel, shaft, cam, or lever.
- **Fastest gesture** — direct rotary control instead of push-to-rotate.
- **Self-evident state** — disc orientation visible and feelable without
  looking. Pegs down = engaged, pegs along plate edge = disengaged.
- **Matches pedal-harp prior art** — pedal harpists manipulate discs by
  rotating them via pedal shafts; a thumb rolling a disc rim is the
  hand-scale analog.

Caveat: the disc rim protruding 3 mm above the plate adds visible
hardware to the neck top. Pedal-harp discs are prominently visible,
so there's precedent. If a flush/hidden control is wanted (matching
the clicky pen's outboard-barrel aesthetic), fall back to a push-cam
mechanism driving the same disc — but that's extra complexity for
worse ergonomics.

## 4. Comparison to clicky pen and earlier yoke-press toggle

| Metric               | Clicky pen         | Yoke-press toggle       | Disc-capture toggle       |
|----------------------|--------------------|-------------------------|---------------------------|
| Holes / pitch point  | Ø6.5 shaft         | Ø5 shaft                | **Ø3 axle only**          |
| Force to engage      | Push spring ~3 N   | Rotate against spring   | **Rotate only, ~1.5 N**   |
| Contact mode         | Paddle pins press  | Yoke presses onto back  | **Pegs grip from both sides** |
| Needs backstop?      | Yes                | Yes                     | **No — pegs are pivot**   |
| String wear          | Point pressure     | Point pressure          | Two-point pinch (gentler) |
| Parts / assembly     | ~6                 | ~5                      | **~4** (disc, axle, detent, lever) |
| F7/G7 fit (Ø3 @ 3.4) | Overlap 3.1 mm     | Overlap 1.6 mm (Ø5)     | **Clear** (3.4 − 3 = 0.4 mm wall) |
| Historical precedent | Organ stop derivative | Custom                | **100+ years of pedal harps** |

Main wins: **tiny hole (Ø3)**, proven mechanism copied from pedal harps,
no backstop means the neck plate can be thinner at each pitch point.

Main loss: pegs are small and take pinch load from string tension (~2.8 N
per string) — durability is the key question. But pedal harp discs do
exactly this at bigger scale for decades, so it's mostly a scaling
exercise.

## 5. Integration at F7 / G7

- **Hole map:** G7 nat and sharp pitch points are 3.4 mm apart on the
  string. Two Ø3 axle holes at 3.4 mm spacing leave **0.4 mm wall**
  between them — marginal but feasible in CF. Two Ø2.5 axles would give
  0.9 mm wall, safer.
- **Shoulder features clear:** discs sit flat on the neck plate's
  inboard face. Diffuser (R=250 spherical depression) and treble scoop
  (paraboloid r=30, d=12) are on the SHOULDER UNDERSIDE on the OPPOSITE
  side of the chamber wall — no physical intersection. The G7 sharp
  disc is the closest at ~7 mm north of BT; verify disc Ø14 doesn't
  crash into the BT rim.
- **Tongue-and-groove joint** (8 mm tongue at chamber top): discs sit
  on the neck plate face, well inboard of the tongue — clear.

## 6. Open questions

1. **Peg durability under sustained tension** — ~2.8 N per engaged string
   pulls on the two peg contacts. Bench test: 10k engage/disengage
   cycles on CF/nylon pegs vs brass pegs.
2. **Peg spacing tuning** — 5 mm peg pitch is a starting guess. Wider
   pitch = more string bend = more pitch shift per given peg height.
   Measure empirically to hit exactly 1 semitone (nat) or 2 (sharp).
3. **Disc rotation vs pedal-harp prior art** — copy existing designs?
   Modify? Scaling down from pedal-harp (strings 2–5 mm diameter) to
   harp treble (0.3 mm treble strings) affects both peg size and disc
   diameter.
4. **Manufacturing** — machined brass or injection-molded filled nylon?
   CF disc with over-molded plastic pegs?
5. **Actuation UX** — thumb lever vs knurled disc edge vs coin-slot.
   What's fastest during play?
6. **Mixed deployment** — where clickies fit (low-mid strings), keep
   them. Where they don't (F7/G7, maybe E7/D7), use disc toggles. Does
   mixed UX confuse the player, or is the per-region split clear?
