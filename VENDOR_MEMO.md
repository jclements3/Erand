# Clements 47 Harp — Carbon Fiber Vendor Memo

**Date:** 2026-04-23
**Project:** Clements 47 Erard-style concert harp
**Quantity:** 1 prototype
**Contact:** james.l.clements.iii@gmail.com

## Overview

The Clements 47 is a 47-string Erard-style concert harp adapted from a 1901
Paris Erard drawing. We are designing the load-bearing acoustic structure in
carbon fiber for a single prototype build. Aesthetic intent is structural
CF: visible weave is acceptable and welcome. Painting or top-coating is
optional, vendor's call. There is no veneer or laminate-over treatment in
this design. The harp ships in three CF assemblies plus a base block (which
may or may not be CF — see Parts list).

## Parts list

Three CF parts plus one optional fourth:

| # | Part           | Form                           | Wall / thickness | Approx envelope         |
|---|----------------|--------------------------------|------------------|-------------------------|
| 1 | Soundbox chamber | Thin-walled limaçon shell    | 3 to 6 mm wall   | ~1322 mm tall, 360 mm peak width |
| 2 | Shoulder       | Thin-walled limaçon-continuation shell | 3 to 6 mm wall | ~30 mm tall above its bottom rim |
| 3 | Neck plates (x2) | Mirror-image flat CF plates  | 2 to 3 mm thick  | ~830 mm long along the string-pull axis |
| 4 | Base           | Block, sealing the bottom rim  | TBD              | Footprint ~360 x 70 mm  |

**Soundbox chamber.** Thin-walled limaçon shell bounded by two open rims
with hidden tongue-and-groove features. Top rim at `Y_ST_HORIZ = 481.94`
joins the shoulder. Bottom rim at `Y_TOP_OF_BASE = 1803.91` joins the base.
The chamber carries the **tongue at the top** (mating into shoulder groove)
and the **groove at the bottom** (receiving base tongue).

**Shoulder.** Thin-walled limaçon-continuation shell, ~30 mm tall above
`Y_ST_HORIZ`. Underside has the matching groove for the chamber tongue. Body
contains two horizontal slots receiving the neck plates' ST→BT tangs (see
Plate slots below). Threaded inserts molded adjacent to the groove for
chamber-to-shoulder fasteners.

**Neck plates (x2).** Mirror-image flat plates running from NB at the
column to BT at the shoulder. **Holes are molded, not drilled** (see
Material intent). Hole pattern is mirrored by string parity per HANDOFF.md
§"Hole alternation" — even strings drill the +z plate, odd strings drill
the -z plate. No x-station has holes through both plates.

**Base.** Caps the chamber's bottom rim with a tongue-up feature into the
chamber groove (opposite polarity to the top joint). Material may be CF or
machined metal — vendor's call. Not strictly a CF deliverable; mention if
you want to scope it.

## Material intent

All three primary parts are carbon fiber. Choice of resin system, fiber
form (UD, woven, braided), and process (RTM, compression mold, prepreg,
filament wind, etc.) is open — see Open questions.

**Molded holes on the neck plates are non-negotiable.** The plates carry
~141 holes total (47 strings x ~3 features per string: tuner Ø16, nat
clicky Ø6.5, sharp clicky Ø6.5). At the string pitch on this harp
(~14 mm at the bass widening to ~17 mm at the treble in the relevant
band), drilled CF is not acceptable:

- Drilling cuts fibers, producing a stress concentration factor of
  approximately 3x at every hole edge.
- Fastener-design rules of thumb for drilled CF call for edge distance
  >= 3D, which on a 16 mm tuner hole demands 48 mm of clear material —
  more than twice the available pitch.
- Molded holes (RTM, compression mold, or braided preform around hole
  pins) keep fibers continuous around each hole. SCF drops to ~1.5x and
  edge distance can shrink to 1.5–2D, which fits the pitch budget.

Chamber and shoulder may use drilled features where appropriate (fastener
through-holes in the chamber rim, threaded inserts in the shoulder, etc.).
The molded-hole requirement applies specifically to the neck plates.

## Critical dimensions and tolerances

All units millimeters. Coordinate system is right-handed: x along the
string-pull axis (positive toward treble), y vertical (positive downward,
SVG convention), z perpendicular to the harp plane.

| Reference | Coordinates (x, y) | Role |
|-----------|--------------------|------|
| ST  | (838.78, 481.94)   | Soundboard top, west tip of chamber lens at top rim |
| BT  | (906.63, 481.88)   | Bulge tip, east end of plate ST→BT segment |
| NT  | (12.70, 146.56)    | Top of column, top anchor of neck plates |
| NB  | (12.70, 323.84)    | Bottom of neck arc, lower column anchor |
| CO  | (12.70, 1803.91)   | Column outer at base — top-of-base plane |
| CI  | (51.70, ~1741)     | Column inner, on soundboard axis |

Tolerances:

| Feature                                           | Tolerance |
|---------------------------------------------------|-----------|
| Hole position on neck plates                      | ± 0.10 mm |
| Plate thickness                                   | ± 0.15 mm |
| Wall thickness (chamber, shoulder)                | ± 0.50 mm |
| Overall dimensional tolerance, features > 50 mm   | ± 0.30 mm |
| Tongue/groove bond clearance (designed)           | 0.15 mm   |
| External chamfer at hidden seams                  | 1.0 mm    |

## Load environment

Total static string load is ~1500 lb (~6.7 kN), distributed across 47
strings. Per-string tensions span **10.976 lb at string 1 (G7) to
52.693 lb at string 47 (C1)** per ERAND.md line 89. Direction vectors per
string are in the accompanying `force_schedule.csv`. The load is static
under tuned conditions; transient excursions during tuning are bounded by
~10% above tuned tension.

Service environment:

- Indoor only.
- Room temperature: 15 to 30 C.
- Relative humidity: 30 to 70 percent.
- No outdoor, transit, or thermal-cycling spec required for the prototype.

## Joints

Two hidden tongue-and-groove joints. See `soundbox/interfaces.md` §1 and §3
for full geometry; key dimensions below.

**Shoulder ↔ Chamber at `Y_ST_HORIZ = 481.94`:**

- Chamber tongue: 8 mm tall, 2 mm thick, follows the lens-shaped rim in
  plan view.
- Shoulder groove: matches tongue + 0.15 mm bond clearance for structural
  adhesive.
- External chamfer: 1 mm on both edges, hides the seam as a design
  feature.
- Fasteners: 4x M4 (or M5) cap screws from inside the chamber upward
  through chamber rim into threaded inserts molded into shoulder
  underside. Invisible from outside. Default pattern: roughly N/S/E/W of
  the lens.

**Base ↔ Chamber at `Y_TOP_OF_BASE = 1803.91`:**

- Polarity reversed: base carries the tongue, chamber the groove.
- Same dimensions: 8 mm tall, 2 mm thick, 0.15 mm bond clearance, 1 mm
  external chamfer.
- Fasteners: from below (instrument underside) up into threaded inserts
  in the chamber's lower rim.

## Plate slots

The shoulder body contains two horizontal slots receiving the neck plates'
ST→BT tangs (one slot per plate in z).

- **Slot width:** plate thickness + 0.20 mm sliding fit.
- **Slot depth:** ~30 mm.
- **Slot mouth fillet:** R 2 to 3 mm.
- **Generator station:** positioned where the shoulder's limaçon
  cross-section z-extent matches the plate z-thickness (~17 mm pair) for
  visual continuity from the plate surface to the shoulder surface.
- **Transverse bolts:** 2x M4 per slot, clamping the plate tang in its
  slot.

## Delivery plan

Alongside this memo, the vendor receives:

| File                  | Contents                                              |
|-----------------------|-------------------------------------------------------|
| STEP files (per part) | Chamber, shoulder, neck plate (one mirror-pair) — forthcoming |
| `force_schedule.csv`  | 47 rows. Per-string force vectors at each anchor.     |
| `hole_schedule.csv`   | ~141 rows. All neck-plate holes with plate assignment, position, diameter, and fiber-orientation hints. |

## Open questions for the vendor

- **Process.** Preferred CF process (RTM, compression mold, prepreg over
  mandrel, filament-wind plus skins, braided preform, other)?
- **Tooling cost and lead time** for this geometry, particularly the
  shoulder's compound curvature and the molded plate holes.
- **Joint construction.** Can the hidden tongue-and-groove joints be
  co-cured, or do they require secondary structural bonding? Preferred
  adhesive?
- **Fiber orientation.** Recommendation given the load case — UD-dominant
  along the string-pull direction on the neck plates, vs quasi-iso for
  the shells? Hole-region layup callouts welcome.
- **Thickness.** We have scoped 2 to 3 mm plates and 3 to 6 mm shells.
  Flexible on absolute numbers given your process constraints; please
  recommend.
- **Mirrored plate tooling.** Can the mirrored neck plate pair share
  tooling (flip the layup), or do they need separate molds?
- **Base part.** Are you interested in scoping the base block as a fourth
  CF part, or should we machine it from metal externally?
