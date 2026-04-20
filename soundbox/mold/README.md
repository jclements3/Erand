# Foam Mold Construction for Clements 47 Soundbox

This directory contains the cutting files and instructions for building a
male mold of the soundbox using stacked 1" foam slabs cut with a hot wire.
The mold is the plug over which carbon fiber is laid up.

## Strategy

Slice the chamber into 68 cross-sections perpendicular to the soundboard
axis, each 1" (25.4 mm) thick. Cut each section from 1" foam, drill
alignment dowel holes, stack on a common axis, glue together. The stack
gives the male mold surface — faceted at 1" resolution. Sand smooth to
reveal the true limaçon loft surface.

## Files in this directory

- `slab_templates_with_dowels.dxf` — All 68 profiles laid out on a grid
  with dowel holes marked. Good for viewing in CAD software, or for
  cutting multiple profiles from a large foam sheet with a CNC hot wire.
- `individual_slabs/slab_NN.dxf` — One DXF per slab (68 files), each
  with a single profile and the 4 dowel holes. Good for printing 1:1
  on a plotter, one per page, for transfer to foam.
- `slab_summary.json` — Metadata for each slab: index, s' range, D, b,
  thickness.
- `slab_profiles.csv` — All profile points as CSV, if you need the
  coordinates directly.
- `slab_templates_grid.dxf` — Earlier version without dowels, kept for
  reference.

## Slab inventory

- 68 slabs total
- Thickness: 25.389 mm each (nominal 1" = 25.4 mm, trimmed slightly to fit
  the full 1726.45 mm loft length exactly)
- Max slab: slab 26, near the peak at s' ≈ 523 mm. Profile 360 × 327 mm.
- Min slab: slab 67, at the treble clearance end. Profile 63 × 58 mm.
- Pattern: slab 0 is the bass end (flat face on floor), slab 67 is the
  treble end (bulge tip at ST horizontal). Slabs numbered bass to treble.

## Alignment dowel pattern

Four through-dowels run parallel to the soundboard axis (perpendicular
to each slab face), passing through every slab:

| Dowel | (n_local, z) mm | Position                        |
|-------|-----------------|---------------------------------|
| A     | (15, +18)       | front-top (toward flat face)    |
| B     | (15, -18)       | front-bot                       |
| C     | (45, +18)       | back-top (toward bulge)         |
| D     | (45, -18)       | back-bot                        |

Use 1/4" (6.35 mm) wooden dowels, 6.5 mm holes. The 4-dowel rectangular
pattern gives both translational and rotational alignment with enough
spread (30 × 36 mm) to minimize compound error across 68 slabs.

All four dowels fit inside the smallest slab's profile with at least
13 mm of clearance from the profile edge.

## Foam stock sizing

Each slab needs a rectangular piece of 1" foam at least as big as its
profile bounding box. For the worst case (slab 26):

- Width: 360 mm (~14.2") + margin → buy 16" minimum width
- Depth: 327 mm (~12.9") + margin → buy 14" minimum depth

For the full run, a 4' × 8' sheet of 1" EPS or polyurethane foam will
yield about 20-25 profiles with careful nesting. You'll need roughly
3 full sheets for all 68 slabs plus spares for mistakes.

**Foam type**: use **extruded polystyrene (XPS)** (the blue/pink boards)
or **rigid polyurethane**. Avoid EPS ("white beadboard") — the bead
boundaries cause surface irregularities that show up after sanding, and
the closed-cell structure of XPS handles hot-wire cutting better. For
polyurethane, check the hot-wire melts it cleanly — some PU foams
vaporize or release bad fumes; cut outside with ventilation.

## Cutting procedure

### 1. Setup

Print or plot each slab's DXF at 1:1 scale. Cut each printout slightly
outside the profile line with scissors. You now have 68 paper templates.

### 2. Transfer templates to foam

For each slab:
1. Spray-mount or tape the template to a piece of 1" foam, profile side up.
2. Drill the 4 dowel holes through the foam using a 6.5 mm drill bit,
   perpendicular to the foam face. Drill all the way through.
3. Mark the profile outline on the foam using a fine pen or scribe.
4. Also scribe registration marks at the flat face (0, 0) and bulge tip
   (4b, 0) — useful for verifying orientation later.

### 3. Hot-wire cutting

For each slab:
1. Thread the 4 dowels (temporarily, full-length rods of 1/4" metal work
   best here — cheap steel rod from a hardware store) through the slab
   and into a stationary jig or guide piece. The dowels hold the foam
   rigid during the cut.
2. Set up your hot-wire cutter with the wire horizontal, table level.
3. Position the foam against the fence so the wire will pass through at
   the correct angle (perpendicular to the foam face, so you get a
   straight prismatic cut).
4. Turn on the wire, wait for temperature.
5. Feed the foam into the wire, following the scribed outline. Take your
   time — feed slowly and steadily. Aim to cut just outside the line
   (stay ~1 mm outside) so you can sand to the line later.

### 4. Drill alignment holes (if not pre-drilled)

If you didn't drill in step 2, drill now. The dowel holes must be
perpendicular to the large face of the slab and aligned with the 4
positions in the DXF. A drill press with a fence is ideal.

### 5. Stack

1. On a flat work surface, lay out four 1/4" diameter wooden dowels
   (or threaded rod) cut to ~1750 mm length. These will thread through
   the entire stack.
2. Slide slab 0 onto the dowels, oriented correctly (flat face toward
   the soundboard side, bulge toward the chamber side). Use the (n_local, z)
   marks to check.
3. Apply a thin bead of spray-on adhesive or contact cement to the face
   of slab 0. Slide slab 1 on. Repeat for all 68 slabs.
4. Important: verify orientation at every slab. The soundboard-flat-face
   side of every slab must align — all the flat faces should form a
   straight line along the stacked axis. Dowel A and B (front dowels)
   are near the flat face; make sure they're always on the same side.

### 6. Sanding

The stacked mold is faceted at 1" intervals (25.4 mm). Sand with a long
flexible sanding block (a 18-24" rigid foam or wood board with adhesive
sandpaper) to blend between slabs. Work with progressively finer grits:
60 grit to level, 100 grit to smooth, 220 grit to finish.

Goal: no visible facet edges between slabs, with the overall shape
matching the limaçon loft to within ~1 mm.

**Reference the soundboard face-on view to check the pear shape.**
The widest point should be at slab 26 (s' = 523, D = 360 mm). Shape
should rise smoothly from D=175 at slab 0, peak at D=360 at slab 26,
then fall smoothly to D=63 at slab 67.

### 7. Surface preparation for layup

Foam is not a good release surface for carbon fiber. You have two options:

**Option A — Coat the foam mold with epoxy.** After sanding, apply 2-3
thin coats of epoxy resin, sanding between coats. This gives a hard,
smooth surface. Then wax (mold release wax, 5+ coats, buffing between)
and finish with PVA mold release. The foam is now a durable mold.

**Option B — Cover with tooling surface film.** Apply a thin (~0.5 mm)
layer of polyester filler over the sanded foam, sand smooth, then treat
like a fiberglass mold surface (gel coat or tooling resin, then
release wax + PVA).

Either way: this is the finished plug that carbon fiber goes over.

## Trimming to final shape

The mold as built is the full chamber loft including the parts that
stick past the floor (slab 0 extends below y = 1915.5) and past the
ST horizontal (slab 67 extends past y = 481.9). These are intentional
overshoot — see the main README.md for why.

For the mold, cut the ends off at:
- Bass end: cut perpendicular to the floor plane at y = 1915.5 (the
  horizontal floor). Mark with a level and cut.
- Treble end: cut perpendicular to the ST horizontal at y = 481.9. Same
  technique.

These are the actual terminations of the finished soundbox shell.

## Verification before layup

Check these against the geometry file:

- Mold total length along soundboard axis: 1726.45 mm (before trimming)
  or 1485.27 mm (after trimming CO to ST, if that's your scope).
- Mold widest point: 360 mm, at ~30% of the length from the bass end.
- Mold deepest point: 327 mm from flat face to bulge tip, at slab 26.

If any of these are off by more than 3-5 mm, re-check alignment and
re-sand before committing to layup.

## Column and base block

The mold covers only the chamber. The column and base block are separate
parts in the full assembly. If you want a complete mold of the whole
harp body:

- Column: simple rectangular prism, cut from 1" foam and stacked like
  the chamber, but all slabs are identical 39×39 mm squares.
- Base block: rectangular block. Dimensions per the base block spec
  (see `interfaces.md` or the main geometry file).

The chamber mold has a bass-end cavity where the base block goes. After
the chamber is laid up in carbon fiber, the base block is built or
molded separately and bonded in.

