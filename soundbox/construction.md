# FreeCAD Construction Sequence for Full Assembly

This is the suggested ordering for building the complete harp in FreeCAD.
Each step relies on primitives from the step(s) above.

## Step 1: Build the limaçon loft (chamber shell)

For `sp` from `S_BASS_CLEAR` (-131.59) to `S_TREBLE_CLEAR` (1594.86) in
small increments (~20-40 mm), generate a closed polyline at each station
using `geometry.limacon_3d(sp, theta)` for theta in [0, 2π).

Loft the polylines into a solid. This is `limacon_loft_solid`.

Each cross-section is a planar curve in the plane perpendicular to
`u_hat` at the grommet line point `(CO + sp*u)`. The curves live in 3D,
sampled at many theta values; they are already closed because the
limaçon is a closed curve.

## Step 2: Build the column

Rectangular prism:
```
x in [COLUMN_OUTER_X, COLUMN_INNER_X] = [12.7, 51.7]
z in [-COLUMN_Z_HALF, +COLUMN_Z_HALF] = [-19.5, 19.5]
y in [y_top_of_column, FLOOR_Y] = [~100, 1915.5]
```
Use NT as the top reference if NT is correct; extend higher if the neck
assembly needs more column height.

This is `column_solid`.

## Step 3: Build the base block

Shape: bounded above by the top-of-base cap (`y = Y_TOP_OF_BASE = 1803.91`)
and below by the floor (`y = FLOOR_Y = 1915.5`). In x, z extent, it must
extend far enough to fully enclose the bass-end chamber bulge and the
column.

Suggested bounds:
```
x in [COLUMN_OUTER_X, ~350]      # column outer to past bass chamber footprint
z in [-180, 180]                 # wraps around the full bass-end bulge
y in [Y_TOP_OF_BASE, FLOOR_Y]    # from cap down to floor
```

This is `base_block_solid` (rectangular; if you want something sculpted,
go ahead).

## Step 4: Build the floor half-space

A large plane or thick slab at `y >= FLOOR_Y`. Used to subtract anything
the chamber has that is below the floor.

This is `floor_halfspace`.

## Step 5: Build the neck assembly (your job)

Design freely. Must occupy:
- Some region near the top of the column (around NT at `(12.7, 146.56)`)
- A region at or above the ST horizontal plane (`y <= Y_ST_HORIZ = 481.939`)
  past the ST point
- Connecting structure between these two regions

This is `neck_solid`.

Inside the neck solid, place 47 tuning pins (one above each grommet,
connected by strings that run through the grommet holes).

## Step 6: Assemble

```
# subtract floor-excluded material from the chamber loft
chamber_trimmed = limacon_loft_solid - floor_halfspace

# carve out the hollow chamber volume from base + loft
# (chamber interior is the part of the loft NOT overlapped by base or column)
chamber_hollow_volume = chamber_trimmed - base_block_solid - column_solid - neck_solid

# the "chamber walls" are the shell of the loft minus the hollow interior
# — you may want a thin-walled shell instead of the full loft solid; if so
# offset the loft inward by wall thickness before subtracting and use the
# result as `chamber_shell`

# the full harp body
harp_body = chamber_shell + column_solid + base_block_solid + neck_solid
```

For a true thin-walled chamber, use a shell operation on the loft with
inward offset equal to the carbon-fiber wall thickness (typically 3-6 mm),
then the hollow interior is automatic.

## Step 7: Boolean-verify

Quick checks:
- The chamber interior should open upward past ST into the neck region
  (or cap there, depending on your neck design).
- The chamber interior at C1's station should extend from the grommet
  line all the way down to the floor (y range approximately 1661 to 1915).
- The column should appear inside the base block, surrounded by solid.
- The top of the base block (`y = 1803.91`) should be a single flat
  horizontal surface from column outer out to the perimeter of the bass
  chamber footprint.
- Grommet positions should all lie on the flat face of the chamber.

## Step 8: Add grommet holes

Each grommet is a small cylindrical hole through the flat face of the
chamber. Iterate through `geometry.GROMMETS`, placing a cylinder of
radius ~1.5 mm at each `(x, y)` on the grommet line, oriented along
`n_hat` (perpendicular to soundboard, passing through the chamber wall).

Subtract the cylinders from the harp body.

