# Soundbox Geometry Handoff for Neck/Column Integration

This package contains the authoritative geometry for the Clements 47 harp soundbox
so the neck-design chat can build the neck assembly and merge it cleanly with the
soundbox and column.

## Files

- `geometry.py` — Single source of truth. Point definitions, limaçon taper,
  clipping planes, loft helpers. Import from here for any computation.
- `grommets.csv` — All 47 grommet positions with s' (from CO) and (x,y).
- `interfaces.md` — What you (the neck chat) hand off at each interface.
- `construction.md` — FreeCAD construction sequence for the full assembly.
- `views_summary.md` — Brief description of the four orthogonal views so you
  can sanity-check your neck against them.

## Coordinate system

Millimeters. Harp 2D plane is (x, y) with y increasing downward.
The out-of-plane z axis is perpendicular to the string plane.
Chamber is symmetric about z = 0.

## Master reference points

| Name  | Coordinates (mm)          | Meaning                                  |
|-------|---------------------------|------------------------------------------|
| CO    | (12.700, 1803.910)        | Column outer × soundboard slope extended |
| CI    | (51.700, 1741.510)        | Column inner × soundboard                |
| NT    | (12.700,  146.563)        | Top of column outer (legacy from project)|
| NB    | (12.700,  323.844)        | Lower column anchor                      |
| ST    | (838.784, 481.939)        | Soundboard top × neck                    |
| Floor | y = 1915.5                | Floor plane                              |

## Soundboard axis

- u = (0.5299, -0.8480, 0)  unit vector CO → ST
- n = (0.8480,  0.5299, 0)  perpendicular to u, into chamber
- 58° above horizontal (32° off vertical)
- Length CO to ST: 1558.858 mm

## Two interfaces you own

1. **Neck–Chamber interface** at the ST horizontal plane (y = 481.939).
   The soundbox chamber terminates here via boolean subtraction of anything
   at y < 481.939 in the neck region. Your neck assembly must occupy this
   half-space in the x range past ST.
2. **Neck–Column interface** at the top of the column (near NT at
   (12.700, 146.563)). The column is a 39 mm prism; the neck assembly sits
   on top of it and connects across to ST.


## Mold construction

See `mold/README.md` for detailed instructions on building a foam mold
of the soundbox using hot-wire-cut 1" foam slabs stacked with alignment
dowels. The mold/ directory contains:

- `slab_templates_with_dowels.dxf` — all 68 profiles on a grid
- `individual_slabs/slab_NN.dxf` — one DXF per slab (68 files)
- `slab_summary.json` — slab index, s' range, D, b for each
- `slab_profiles.csv` — all profile points as CSV

