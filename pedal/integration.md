# Clicky-pen pedal engagement - integration notes

Scope: first-pass mechanical design for "one click engages the string...
clicky pens for each sharp and natural point... paddle puts the string
under the impact". Companion files in this folder:

- `paddle.svg`  - paddle + clicky side view, 1:1 mm, B4 sharp example.
- `packing.svg` - top view, treble-end packing (strings 38-47).

## 1. Interpretation

Prompt says "natural and sharp" paddles, 2 per string, 94 total. That
maps cleanly onto the code, but with a terminology clash worth pinning.

In `build_harp.py` each string exposes three pedal-state points:
`flat` (= `pin`, full length), `nat` (one semitone shorter), and
`sharp` (two semitones shorter). Only **two** get physical 12-mm buffer
obstacles: `flat_buffer` and `sharp_buffer`. The `nat` point is computed
but has no buffer - the natural-pedal state engages the same physical
stop as the flat-pedal state. So there are **two paddles per string**,
and the user's "natural" is the code's `flat_buffer`. Suggested rename:
**flat-paddle** and **sharp-paddle**.

Verification for B4 (string #28) via `python3 build_harp.py`:

- `pin`          = (554.226, 583.799)  flat-pedal point (= pin itself)
- `flat_buffer`  = (563.326, 545.699)  flat/nat stop, R = 12 mm circle
- `sharp_buffer` = (554.226, 622.365)  sharp stop, R = 12 mm circle
- `nat`          = (554.226, 603.639)  (no buffer rendered)

Each paddle nose must coincide with its buffer center when extended.

## 2. Paddle geometry (see paddle.svg)

Shape: trapezoidal plate ~16 mm along the string x 5 mm into the gap x
6 mm tall. A half-round nose pin (r = 0.8 mm) projects 0.6 mm proud of
the paddle face; its apex is the string-stop point, defined to within
~0.1 mm.

Round nose (not flat edge): strings angle 3-34 degrees off horizontal
along the neck; a round nose has the same contact geometry regardless
of local string angle, so one paddle SKU fits all 47 strings.

Trapezoidal wing near the shaft picks up the clicky tip without a
separate coupling; narrow nose lets the paddle pass between adjacent
strings at the tight treble end.

Air gap retracted: 3 mm. Over-travel extended: 0.6 mm past string
centerline for spring preload. **Stroke = ~4 mm.**

## 3. Clicky-pen integration

### Mounting

Two 6 mm plywood sheets separated by a 12.7 mm gap (from `NECK.md`).
Clicky barrel flush against the OUTER face of one plywood sheet; shaft
through a 6.5 mm clearance hole into the gap; paddle on the shaft tip.

Which side:

- **Flat paddle**: NORTH plywood sheet, reaches south; hits `flat_buffer`.
- **Sharp paddle**: SOUTH plywood sheet, reaches north; hits `sharp_buffer`.

Sanity-check at B4: `flat_buffer` y = 545.7 (north of pin y = 583.8 in
SVG-down-positive frame), `sharp_buffer` y = 622.4 (south). Holds for
B4; worth a scripted sweep across all 47 strings before prototyping.

Barrel axis assumed perpendicular to the plywood (not to the string
plane). String angle introduces a cosine error on stroke - ~14% at
34 degrees at the bass end, negligible at the treble. Accept.

### Packing

String spacing from `_RAW_GEOM` (pin-to-pin `hypot`):

- Treble (F7-G7): 17.4 mm; sharp-buffer-to-sharp-buffer 18.2 mm
- Mid (around B4): 14-15 mm
- Bass: up to ~18 mm

Flat paddles on one sheet, sharp on the other, means each sheet carries
47 barrels at ~17 mm pitch - NOT 94 at 8.5 mm. **The odd/even stagger
in the prompt is not needed.** It stays in reserve if clicky OD grows.

Candidate clicky size: **OD 12 mm, L 16 mm**, slim round barrel based
on the 99950 Penmechbarrel (20x10x21 bbox). That yields 5.4 mm
edge-to-edge clearance at the treble end. Thingiverse 4825717 (32x28x68)
is too big; 99950 Cammed shaft (14x16x52) is too long. Custom print
required either way.

Spring (per 99950 README): wire 0.8, OD 7.5, free length 30 mm - will
ride ~12 mm compressed in a 16 mm barrel, marginal; custom wound
spring likely needed for consistent click-cam engagement.

### Stroke & force

- Retracted nose to string centerline: 3.0 mm (clear of oscillation).
- Extended: string center + 0.6 mm over-travel.
- Stroke: 3.6 mm nominal, 4.0 mm design. Thingiverse designs give 10+
  mm stroke, so headroom is easy.

Engagement force: for a 0.6 mm deflection over ~100 mm of string at
C1's 235 N tension, restoring force ~ 2 T sin(theta) ~ 2.8 N. Spring
must hold >= 2.8 N at extended state. Soap-dispenser-class springs give
3-10 N - **marginal at the bass end, confirm at prototype.**

## 4. Open questions

1. **Natural vs flat terminology.** Is "natural" the code's
   `flat_buffer` (two paddles/string) or a third distinct stop (three
   paddles/string = 141 clickies)? Current design assumes two.
2. **Pedal-system context.** On a traditional pedal harp, seven foot
   pedals drive cams that flip all strings of a given letter (all A, all
   B, etc.) at once. A clicky-pen per string is unusual: is this an
   electric-pedal substitute? A per-key preset rig? A test fixture for
   one string at a time? Design changes a lot with the answer. **Biggest
   unknown.**
3. **Flat/sharp-buffer side-of-string assumption.** Verified at B4;
   sweep the other 46 to rule out exceptions before committing to
   "flat on north sheet, sharp on south".
4. **Barrel axis perpendicular to plywood vs to string plane.** Current:
   perpendicular to plywood (small cosine error in stroke). Revisit if
   the neck curvature tilts the plywood away from the string plane.
5. **Paddle-to-shaft coupling.** Fixed (glued) is simpler; pivoted
   compensates for string angle but adds parts. Round nose makes fixed
   sufficient.
6. **Nose material.** PETG will wear against nylon and especially wound
   steel strings. 1 mm brass insert or ceramic tip strongly suggested.
7. **Tuning-key access.** Tuning pins sit above the north plywood.
   Flat-paddle clickies also on north. Collision check needed vs tuning
   key swing radius.
8. **Acoustic damping.** Plastic paddle at the stop may damp overtones
   differently than a traditional rigid pin-and-grommet buffer. A
   small brass/ceramic contact face is a cheap mitigation.

## 5. Files

- `paddle.svg`      - 1:1 paddle detail, B4 sharp, with R_BUFFER circle.
- `packing.svg`     - top view, strings 38-47 packing layout.
- `integration.md`  - this file.
