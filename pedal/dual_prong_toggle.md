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

- Disc: Ø14 mm, 1.5 mm thick, brass or molded filled nylon.
- Axle: Ø3 mm through the neck plate — **one Ø3 mm hole per pitch point**.
- Pegs: two Ø1.5 mm cylinders standing 3 mm proud of disc face, tip
  radius r=0.5, offset 2.5 mm from disc center on opposite sides of a
  diameter. Peg pitch (distance between pegs) = 5 mm.
- String passes through the 12.7 mm plate gap; disc sits flush against
  the inboard plate face with axle through the plate to a thumb lever
  on the outboard side.
- Per-string envelope: Ø14 × 1.5 mm disc in the string gap; Ø3 axle
  hole; small lever on the outboard face.

```
  outboard side                    inboard side (string gap)

     __                            __
    /  \                          /  \        ---> string lane
   | oo |  thumb lever/detent    |(ax)|       Y|        engaged:
    \__/                          \__/         |        pegs straddle
     ||                            ||          |        string
    [||]  axle                    [||]         |
    --||-- plywood Ø3             --||-- plate |
     ||                            ||         | |
     ||                            |=|        | |    disengaged:
                                    disc      | |    pegs clear
                                              | |    of lane
                                  pegs -->. . |
                                              |
                                           string
```

## 3. Actuation

Ball-and-cup bistable detent on the outboard face — one cup at 0° (DISENGAGED)
and one at 180° (ENGAGED). Small thumb lever or knurled edge on the disc
lets the player flip it with one finger. Detent force ~1.5 N (lower than
the clicky or the yoke-press design because **no axial preload needed**
— the disc only needs torque to swing, no force to hold the string
against a backstop).

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
