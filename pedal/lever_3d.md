# Pitch mechanism — Josephus 3D-printed lever

**Decision (2026-04-25):** the Clements 47 will use **Josephus's CC BY-SA
3D-printed harp lever** as the chosen per-string pitch mechanism. Replaces
clicky-pen, dual-prong-toggle, and ganged-disc-lever (all removed from
this directory).

- Source: `https://harpcanada.com/3d-lever/3d-levermain.htm`
- Author: Josephus Harps (harpcanada.com)
- License: Creative Commons **BY-SA 4.0** (2024). Attribution required;
  derivative work must use the same license. Commercial use allowed.
- Files referenced (not vendored here): DIY manual PDF (~16 MB), STL set
  (~250 MB) at `harpcanada.com/3d-lever/`.

## Why this design

- **Real working lever.** Already in production by Josephus; comparable
  operating force (100 - 350 g at the handle) to commercial Camac /
  Loveland / Truitt levers per Josephus's measurements.
- **Three printed parts + one metal pin.** Base + rotor handle (with
  V-groove pusher tip integral to the rotor) + slotted spring tension
  pin (the axle). Bridge pin is a #6 Philips screw + a printed sleeve
  with a V-groove on top, so the lever and bridge are both adjustable.
- **No springs, no spacers.** The slotted spring tension pin's hoop
  springiness combined with the handle pre-loaded against the base jaws
  (compressed ~13 kg at assembly) gives the bistable click feel without
  any separate spring washer.
- **CC BY-SA = legal to ship with the harp** as long as we credit and
  match license downstream.

## Datasheet (Josephus's three sizes)

All dimensions in mm; +/-0.5 mm tolerance from the data sheet.

### Moving handle (rotor)

| dim                      | Narrow | Regular | Large |
|--------------------------|-------:|--------:|------:|
| handle length from axle  |     34 |      39 |    44 |
| pusher height when down  |      9 |       9 |     9 |
| pusher height when up    |     14 |      14 |    15 |
| elevation range (lift)   |      5 |       5 |     6 |
| handle width             |      5 |       5 |     5 |
| string height (+/- 2 mm) |     12 |      12 |    13 |

### Regular base

| dim                      | Narrow | Regular | Large |
|--------------------------|-------:|--------:|------:|
| width                    |      9 |      11 |    12 |
| length                   |     32 |      33 |    37 |
| thickness                |      4 |       4 |     4 |
| full height              |      8 |       8 |     8 |
| screw slot length        |      5 |       6 |     8 |
| screw slot width         |      3 |       3 |     3 |
| screw (#4-40 button cap) |     13 |      13 |    13 |
| min string spacing       |     13 |      14 |    14 |

### Slotted spring tension pin (the axle)

| dim                | Narrow base | Regular base | Large base |
|--------------------|------------:|-------------:|-----------:|
| nominal Ø          |        5/64 |         5/64 |       5/64 |
| length (")         |        5/16 |         7/16 |       7/16 |
| SPAENAUR part      |       TP-56 |        TP-58 |      TP-58 |
| drill bit (stiff)  |     1.98 mm |      1.98 mm |    1.98 mm |
| drill bit (mild)   |   2.00 mm   |    2.00 mm   |  2.00 mm   |

Plus an extra 1/16" x 7/16" pin (TP-49) used in the V-groove pusher of
the Large bass handle.

### Optional bridge-pin sleeve

| dim                | Narrow | Regular | Large |
|--------------------|-------:|--------:|------:|
| screw size         |   #6   |    #6   |  #8   |
| screw length       |    30  |     30  |   38  |
| screw head Ø       |    6   |     6.4 |   7.4 |
| sleeve Ø           |    6   |     7   |   7   |
| sleeve length      |    6   |     6   |   6   |

### Print parameters (Josephus's K1C + Hyper PLA)

- Filament: Creality Hyper Series PLA, 1.75 mm.
- Layer height: 0.16 mm for handle/base, 0.08 mm for sleeves.
- Infill: 90%.
- Default print speed: 300 mm/s on K1C.
- Custom slicer settings: top ironing on, Z-hopping on, slim support on.
- One handle ~10 min print time; full 47-string set < 10 hours.

## Modifications for the Clements 47

The 47-string range (C1 to G7) is wider than a typical lever harp's
26-36 strings, so Josephus's three sizes (Narrow / Regular / Large)
need to be **extended to five** at both ends:

| size               | handle L | base L x W | lift  | string Ø    | min spacing |
|--------------------|---------:|-----------:|------:|------------:|------------:|
| **XL** (NEW)       |    50 mm |  42 x 14   |  7 mm | 2.5 - 3.0 mm |   18 mm     |
| Large (Josephus)   |    44 mm |  37 x 12   |  6 mm | 1.5 - 2.1 mm |   14 mm     |
| Regular (Josephus) |    39 mm |  33 x 11   |  5 mm | 0.7 - 1.2 mm |   14 mm     |
| Narrow (Josephus)  |    34 mm |  32 x  9   |  5 mm | 0.5 - 0.8 mm |   13 mm     |
| **XS** (NEW)       |    28 mm |  26 x  6   |  4 mm | 0.3 - 0.5 mm |    6 mm     |

**XL** is needed because Josephus quotes 2.13 mm as the thickest tested
string; the Clements 47's bottom octave (C1 = 33 Hz) very likely uses
2.5 - 3.0 mm wound strings. Larger V-groove, deeper lift, larger axle
pin (3/32" suggested) for the higher torque load.

**XS** is needed because the Erard tier scale used in `build_harp.py`
shrinks string spacing into the high treble — at C7-G7 the spacing is
near 5-7 mm, well below Narrow's 13 mm minimum. Narrowed base, scaled
handle, smaller axle (1/16" TP-49 already used in Josephus's set as the
V-pusher pin).

## Per-string size allocation (first-pass)

| octave           | strings        | size    | count |
|------------------|----------------|---------|------:|
| C1 - B1          | #1 - #7        | XL      |     7 |
| C2 - B2          | #8 - #14       | Large   |     7 |
| C3 - B3          | #15 - #21      | Regular |     7 |
| C4 - B4          | #22 - #28      | Regular |     7 |
| C5 - B5          | #29 - #35      | Regular |     7 |
| C6 - B6          | #36 - #42      | Narrow  |     7 |
| C7 - G7          | #43 - #47      | XS      |     5 |
|                  |                | total   |    47 |

Refine when ERAND.md's per-string diameter table is wired into
`build_harp.py`.

## Mounting on the neck

Each lever bolts to the OUTBOARD face of the north neck plate via a
single #4-40 button-cap screw through its base slot. Slot allows
+/- 3 mm of x-axis adjustment for fine regulation. Bridge pin is a
threaded #6 (or #8 on Large/XL) screw threaded into the plate,
height-adjusted by turning, with a printed sleeve providing the V-groove.

This means **47 lever positions on one plate face**. Hole pattern in
`build_harp.build_strings()` will need:

- Replace `nat_buffer` and `sharp_buffer` clicky-pen Ø6.5 holes with
  a single #4-40 mounting hole (Ø2.4 tapped, Ø2.7 clear) per string,
  located at the lever-base centroid.
- Add a #6 / #8 bridge-pin tap hole per string at the V-groove
  position, ahead of the lever along the string's run.
- Update `optimize_v2.py` neck-outline clearance check for the new
  smaller hole pattern.

Drawing files:

- `pedal/lever_3d_side.svg` - side elevation (down + engaged), Regular
  size, with notes on operation and 47-string caveats.
- `pedal/lever_3d_assembly.svg` - exploded view (base, rotor, spring
  pin, bridge-pin screw + sleeve) with bill of materials.
- `pedal/lever_3d_sizes.svg` - 5-size family at common scale + the
  per-octave allocation table.

## What the lever does NOT do (vs. pedal-harp discs)

- **Single-action only.** One lever per string raises by exactly one
  semitone. No nat/sharp swap (no double-action). For a key change
  the player engages multiple levers.
- **Per-string actuation.** No ganged pitch-class control; the
  ganged-disc-lever idea is dropped.
- **Hand-operated.** No foot pedals on this harp.

## Provenance and licensing

- Original design: Josephus Harps, harpcanada.com (CC BY-SA 4.0, 2024).
- This memo and the SVGs in this directory are derivative works,
  released under the same CC BY-SA 4.0 license.
- If we ship STL files derived from Josephus's STLs, they MUST carry
  the same license and credit Josephus by name and URL.
- The size dimensions in the data-sheet table above are direct
  excerpts from Josephus's published data sheet for attribution and
  archival purposes; the XL and XS sizes are our additions.
