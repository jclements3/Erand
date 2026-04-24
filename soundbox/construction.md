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

The column is a **bent** rectangular cross-section — 39 mm × 39 mm
(`x`-width 39 mm, `z`-width 39 mm centered on `z = 0`) at every y, with
a centerline that follows a gentle circular arc in the x-y plane rather
than a straight vertical line. See `interfaces.md` §2 for the full arc
spec (`COLUMN_BEND_RADIUS = 10000 mm`, tangent to vertical at
`y_mid ≈ 975.24`, bulging toward `-x` at both ends).

Key reference elevations on the centerline / outer face (see §2):

- At `y_mid = (NT.y + CO.y) / 2 ≈ 975.24` the centerline sits at the
  ORIGINAL straight-column x = 32.2 (the bend offset is zero here).
- At `y = NT.y = 146.563` the outer face is at `x ≈ -21.69`
  (`NT_BENT ≈ (-21.694, 146.563)`).
- At `y = FLOOR_Y = 1915.5` the outer face is at `x ≈ -31.60`.

At each y the column's x-extent is
`[column_outer_x(y), column_inner_x(y)]` and the z-extent is
`[-COLUMN_Z_HALF, +COLUMN_Z_HALF] = [-19.5, 19.5]`. Build `column_solid`
by **sweeping** the 39 mm × 39 mm rectangular cross-section along the
column's arc centerline from `y = y_top_of_column` (use NT.y as the top
reference, or extend higher if the neck assembly needs more column
height) down to `y = FLOOR_Y`. Use the helpers
`geometry.column_outer_x(y)`, `geometry.column_inner_x(y)`, and
`geometry.column_centerline_x(y)` to generate the sweep path; do NOT use
the constants `COLUMN_OUTER_X` / `COLUMN_INNER_X`, which correspond to
the straight (pre-bend) column and are retained only for backwards
compatibility.

This is `column_solid`.

## Step 3: Build the base as a plug-and-lower-body part

The base is a **discrete part** (CF or, vendor's call, an alternative
material such as machined aluminum), bonded to the chamber via a hidden
tongue-and-groove joint at `y = Y_TOP_OF_BASE = 1803.91` (mirror of the
shoulder joint at the top end). The chamber is OPEN at its bottom rim;
the base plugs UP into it from below. See `interfaces.md` §3 for the
joint specification.

The part has three functional regions:

- **Plug region** (y in `[Y_TOP_OF_BASE - BASE_PLUG_DEPTH,
  Y_TOP_OF_BASE + BASE_JOINT_TONGUE_HEIGHT]` = `[1783.91, 1811.91]`):
  a solid body whose horizontal cross-section matches the chamber's
  interior cross-section at each y, plus a thin TONGUE on the top face
  rising into the chamber's GROOVE. Fills the chamber's bottom opening
  and registers the joint.
- **Lower body** (y in `[Y_TOP_OF_BASE, FLOOR_Y]` = `[1803.91, 1915.5]`):
  the structural section that contacts the floor, wraps the curved
  column, and contains the (curved) column socket. Also wraps the
  volume where the chamber's bass-end bulge *would* have continued
  downward past the clip plane — the chamber is open at
  `y = Y_TOP_OF_BASE`, so the base owns that region.
- **Column socket** (curved, not a straight vertical pocket): the
  column's centerline follows an arc in the x–y plane (see
  `interfaces.md` §2), so the socket is a **swept rectangular
  cross-section along the column's curved centerline** from
  `y = Y_TOP_OF_BASE` down to `y = FLOOR_Y` (extend slightly deeper,
  e.g. 10–20 mm past FLOOR_Y, for engagement/bonding if the vendor
  wants more glue area). At each y the socket's x-extent is
  `[column_outer_x(y), column_inner_x(y)]` and the z-extent is
  `[-COLUMN_Z_HALF, +COLUMN_Z_HALF] = [-19.5, +19.5]`, with the usual
  bond/sliding clearance (e.g. +0.2 mm per side). Use
  `geometry.column_outer_x(y)` / `geometry.column_inner_x(y)` to
  generate the sweep path; do NOT use the constants `COLUMN_OUTER_X` /
  `COLUMN_INNER_X`, which correspond to the straight (pre-bend)
  column.

Suggested bounds for the lower body in x, z (must fully enclose the
curved column AND the bass-end chamber bulge footprint, with margin):
```
x in [-40, ~350]                 # west of bent column at floor (x≈-31.6)
                                 # with ~8 mm margin, east to past the
                                 # bass bulge tip at floor (x≈191) with
                                 # generous margin
z in [-180, 180]                 # wraps around the full bass-end bulge
y in [Y_TOP_OF_BASE, FLOOR_Y]    # from top-of-base plane down to floor
```

Why the x-bounds changed: the column now curves outward toward `-x`
and its outer face sits at `x ≈ -21.7` at `y = Y_TOP_OF_BASE`, at
`x ≈ -31.6` at `y = FLOOR_Y`. The legacy `x ∈ [COLUMN_OUTER_X, 350]
= [12.7, 350]` no longer encloses the column. Separately, the
chamber's limaçon flat face at `s' = S_BASS_CLEAR` reaches `x ≈ -57`
right at the floor (the flat face tips inward again above the floor),
so if you prefer the base to also fully enclose the chamber bulge's
footprint at the floor, widen the west bound to `x = -65` or so. For
a symmetric rectangular bounding box the looser `x ∈ [-70, 350]` is
safe; for a tighter fit the two features can be unioned individually
(see boolean construction below).

The TOP face is not flat — it carries the tongue feature around the
chamber rim's lens perimeter and an opening for the (curved) column
socket. The plug region above `y = Y_TOP_OF_BASE` follows the
chamber's interior shape, not a rectangular box.

Boolean construction (suggested):

```
# 1. Outer envelope of the lower body: take the chamber's bass-bulge
#    footprint (the lofted solid clipped to y in [Y_TOP_OF_BASE,
#    FLOOR_Y]) unioned with a rectangular block sized to wrap the
#    curved column.
lower_envelope = (
    limacon_loft_solid.clipped_to(y_range=[Y_TOP_OF_BASE, FLOOR_Y])
    + column_wrap_block   # e.g. x∈[-40, 20], z∈[-25, 25], same y range
)

# 2. Plug region: intersection of the chamber's interior with the slab
#    y in [Y_TOP_OF_BASE - BASE_PLUG_DEPTH, Y_TOP_OF_BASE].
plug = chamber_interior.clipped_to(
    y_range=[Y_TOP_OF_BASE - BASE_PLUG_DEPTH, Y_TOP_OF_BASE]
)

# 3. Tongue: extrude the chamber rim's lens shape upward by
#    BASE_JOINT_TONGUE_HEIGHT, wall thickness BASE_JOINT_TONGUE_THICK.
tongue = extrude_rim_lens(...)

# 4. Curved column socket: sweep a rectangular cross-section of size
#    (COLUMN_WIDTH + clearance) x (2*COLUMN_Z_HALF + clearance) along
#    the path {(column_centerline_x(y), y) | y in [Y_TOP_OF_BASE,
#    FLOOR_Y + engagement_extra]}.
column_socket = sweep_rect_along_column_arc(...)

# 5. Assemble.
base_part = (lower_envelope + plug + tongue) - column_socket
```

This is `base_part`.

## Step 4: Build the floor half-space

A large plane or thick slab at `y >= FLOOR_Y`. Used to subtract anything
the chamber has that is below the floor.

This is `floor_halfspace`.

## Step 5: Build the neck assembly (your job)

Design freely. Must occupy:
- Some region near the top of the column (around `NT_BENT ≈ (-21.69, 146.56)`,
  i.e. `(column_outer_x(146.56), 146.56)`). The straight-column value
  `NT = (12.7, 146.56)` is preserved in `NT_XY_BASE` for backwards
  compatibility, but the active top-anchor point on the bent column is
  `NT_BENT` — see `interfaces.md` §2.
- A region at or above the ST horizontal plane (`y <= Y_ST_HORIZ = 481.939`)
  past the ST point
- Connecting structure between these two regions

This is `neck_solid`.

Inside the neck solid, place 47 tuning pins (one above each grommet,
connected by strings that run through the grommet holes).

## Step 6: Assemble

```
# Clip the chamber loft at BOTH open rims. With the new tongue-and-groove
# joints at both ends, the chamber is OPEN at y = Y_ST_HORIZ (top, treble/
# shoulder end) and OPEN at y = Y_TOP_OF_BASE (bottom, bass end) — neither
# rim is capped. Both are annular rims with tongue/groove features (polarity
# per interfaces.md §1 and §3).
chamber_trimmed = limacon_loft_solid.clipped_to(
    y_range=[Y_ST_HORIZ, Y_TOP_OF_BASE]
)

# The chamber is a thin-walled shell open at BOTH ends. Use a shell
# operation on chamber_trimmed with inward offset equal to the carbon-
# fiber wall thickness (typically 3-6 mm) to get `chamber_shell`. The
# base part below and the shoulder above close off the open rims via
# their respective tongue-and-groove joints — the base is NOT subtracted
# from the chamber, it is a separate part joined at the bottom rim, and
# the shoulder likewise is a separate part joined at the top rim.

# The full harp body is assembled from four discrete parts joined at
# their respective interfaces:
#   - chamber_shell : thin-walled CF limaçon shell, open at Y_ST_HORIZ
#                     and Y_TOP_OF_BASE
#   - shoulder      : separate CF part joined at Y_ST_HORIZ (hidden
#                     tongue-and-groove, interfaces.md §1)
#   - base_part     : separate CF/aluminum part joined at Y_TOP_OF_BASE
#                     (hidden tongue-and-groove, interfaces.md §3),
#                     containing the lower-body floor contact and the
#                     curved column socket
#   - neck_solid    : from Step 5, bridging NT_BENT to ST
harp_body = chamber_shell + shoulder + base_part + neck_solid
```

## Step 7: Boolean-verify

Quick checks:
- The chamber interior should open upward past ST into the shoulder via
  the tongue-and-groove joint at `y = Y_ST_HORIZ`.
- The chamber interior at C1's station should extend from the grommet
  line all the way down to the floor (y range approximately 1661 to 1915);
  the lower portion below `y = Y_TOP_OF_BASE = 1803.91` is now formed by
  the base part's plug region rather than the chamber shell.
- The column should appear passing from `NT_BENT` through the chamber
  interior into the base part's column socket. The bent column's swept
  socket should appear inside the base, with the column's outer face
  following `column_outer_x(y)` from `Y_TOP_OF_BASE` down to `FLOOR_Y`
  (outer face at `x ≈ -21.69` at the top of the base, curving out to
  `x ≈ -31.60` at the floor). The base's lower body should fully wrap
  the curved column down to the floor.
- The seam at `y = Y_TOP_OF_BASE = 1803.91` between chamber and base
  should be hidden by the chamfer on both parts; no visible gap.
- Grommet positions should all lie on the flat face of the chamber.

## Step 8: Add grommet holes

Each grommet is a small cylindrical hole through the flat face of the
chamber. Iterate through `geometry.GROMMETS`, placing a cylinder of
radius ~1.5 mm at each `(x, y)` on the grommet line, oriented along
`n_hat` (perpendicular to soundboard, passing through the chamber wall).

Subtract the cylinders from the harp body.

