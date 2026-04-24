# Interfaces the Neck Chat Owns

The soundbox chamber geometry is fully specified in `geometry.py`. Your job
is to design the neck assembly and make sure it mates cleanly at the
two interfaces below.

## 1. Neck–Chamber interface (two-part hidden tongue-and-groove)

### Design intent

The chamber and the shoulder are TWO separately molded thin-walled CF
parts bonded at `y = Y_ST_HORIZ = 481.939` with a hidden tongue-and-
groove joint. The exterior surface reads as one continuous limaçon
loft — the joint is internal, and the only external indication is a
thin horizontal seam line hidden by a shallow chamfer. This is the
pivot away from an earlier plug+lip design: with two thin-walled
parts the vendor avoids the shell-to-solid transition that would
otherwise be required.

### Shared geometry at the interface plane

The limaçon loft runs from `s' = -131.59` to `s' = 1594.86`. At the
interface plane `y = Y_ST_HORIZ`:

- **Horizontal slice of the chamber** (opening in plan view): computed
  by solving `y(s', theta) = Y_ST_HORIZ` for each station
  `s' ∈ [L_CO_ST = 1558.86, S_TREBLE_CLEAR = 1594.86]`. The result is
  a **true limaçon lens** (pointed at both x-ends, widest near the
  middle, symmetric in z) — NOT an ellipse:
  - `x ∈ [838.78, 906.16]` mm (width 67.4 mm)
  - `z ∈ [-34.41, +34.41]` mm (width 68.8 mm)
  - Widest (`|z| ≈ 34.4`) near `x ≈ 872`
  - **West tip at ST** `(838.78, 481.94, 0)` — the limaçon's flat-
    face point at the ST station lies exactly on this plane.
  - **East tip at the bulge-tip clearance point** `(906.16, 481.94, 0)`.
- **Outer boundary** (seam ring / shoulder-underside mating line):
  lens offset outward along the local normal by the chamber wall
  thickness (default ~5 mm). Approximate outer x-range
  `[833.8, 911.2]`.
- **`D(s')` at the rim** = 63.23 mm (the limaçon value at
  `s' = S_TREBLE_CLEAR = 1594.86`). The shoulder's `D` at its lower
  edge must match this value for exterior surface continuity.

### Chamber side (molded as one CF part)

- Thin-walled limaçon shell, wall thickness ~3–6 mm, terminating upward
  at an annular rim at `y = Y_ST_HORIZ`.
- The rim's top face has a **TONGUE** extending upward by
  `SHOULDER_JOINT_TONGUE_HEIGHT = 8 mm`.
- Tongue thickness = `SHOULDER_JOINT_TONGUE_THICK = 2 mm` (roughly
  matching the CF wall thickness).
- Tongue follows the annular rim shape in plan view (lens-shaped).
- The rim also has through-holes for fasteners (see Fastening below).

### Shoulder side (molded as a separate CF part)

- Thin-walled limaçon-continuation shell, wall thickness matches
  chamber.
- Underside (the face at `y = Y_ST_HORIZ`) has a **GROOVE** sized to
  receive the chamber's tongue with a
  `SHOULDER_JOINT_BOND_CLEARANCE = 0.15 mm` gap for structural
  adhesive.
- Body rises `H_SHOULDER = 30 mm` above `y = Y_ST_HORIZ` along the
  extended generator (soundboard tangent from ST → fillet arc of
  radius `R_SHOULDER_FILLET = 5 mm` → F7-G7 south sharp-buffer tangent
  back toward the treble buffers, with `D(s')` continuing to shrink to
  D=0 at the apex).
- **Slots** in the shoulder's body receive the neck plates' ST→BT
  tangs. Two slots (one per plate in z), sized to plate thickness +
  0.2 mm sliding fit. **Slot mouth positioned at the rim plane**
  (y = Y_ST_HORIZ), where the shoulder's `D(s')` is 63.23 mm
  (the chamber's full width at the rim). Because the plate's total
  z-extent (16.7 mm = 12.7 gap + 2×2 mm plate thickness) is much
  smaller than the shoulder's 63 mm z-width at the rim, the shoulder's
  outer surface visibly **steps down** from its limaçon z-curve to the
  plate's 2 mm z-thickness at the slot mouth. The step is hidden by a
  local fillet of radius 3–5 mm. This trade keeps the plate geometry
  simple (straight ST→BT tang, ~20 mm engagement into the slot, no
  rising curve required) at the cost of a small visible cosmetic step
  at the plate/shoulder junction. Alternative (not adopted): mouth
  the slot at `s_arc = 1797.88` where `D_arc = 16.7 mm` for a
  z-flush transition, but that requires the plate tang to extend
  85.75 mm east of BT and rise ~162 mm above the rim — a significant
  plate complication deemed not worth the cosmetic benefit.
- Threaded inserts molded into the underside adjacent to the groove
  for the shoulder-to-chamber fasteners.

### External seam

At `y = Y_ST_HORIZ` the two parts meet in a thin horizontal seam on the
exterior. Hidden by a **chamfer of depth `SHOULDER_JOINT_CHAMFER = 1 mm`**
on both the chamber's upper edge and the shoulder's lower edge — the
chamfer reads as a design detail rather than a gap.

### Plate support

The neck plates' ST→BT south edge (at `y = 481.939`) rests directly on
the chamber rim's top face along its full length:

- Plate ST→BT spans `x ∈ [838.78, 906.63]`.
- Chamber rim outer boundary spans `x ∈ [~833.8, ~911.2]`.
- The plate's ST end sits *exactly* on the lens's west tip; the
  plate's BT end sits ~5 mm inside the rim's east outer boundary.
- **The plate is fully supported by the chamber rim alone** — the
  shoulder's underside does not need to reach west under the plate.
  (This is a consequence of the plate geometry: ST lies on the
  soundboard line, which is exactly the west tip of the lens.)

The chamber rim and the shoulder's underside are coplanar at
`y = Y_ST_HORIZ`, so where they abut the plate sees one continuous
horizontal pad.

### Fastening

- **Shoulder to chamber**: M4 or M5 cap screws pass from *inside the
  chamber* upward through the rim's through-holes into the threaded
  inserts in the shoulder's underside. Fasteners are invisible from
  outside. Default pattern: 4 fasteners, roughly at the lens's N/S/E/W
  extrema.
- **Plates to shoulder**: transverse through-bolts (M4) across the
  shoulder body, clamping the plate tangs in their slots. Default
  pattern: 2 bolts per slot.

## 2. Neck–Column interface (at the top of the column)

### What the soundbox side provides

The column is a 39 mm × 39 mm rectangular cross-section (`x`-width 39 mm,
`z`-width 39 mm centered on `z = 0`) whose **centerline follows a gentle
circular arc in the x-y plane** — no longer a straight prism. The bend
is controlled by two parameters in `geometry.py`:

- `COLUMN_BEND_ENABLED = True`
- `COLUMN_BEND_RADIUS = 10000.0` mm (large radius → gentle curve)

Arc geometry:

- Midpoint at `y_mid = (NT.y + CO.y) / 2 ≈ 975.24` is pinned at the
  ORIGINAL straight-column centerline `x = 32.2`. This preserves the
  C1 string clearance at the middle of the column.
- The arc is **tangent to vertical** at `y_mid` — locally vertical at
  the middle and symmetric about that plane.
- The arc **bulges outward toward `-x`** (away from the strings) at both
  the top (neck end) and the bottom (base end).
- Cross-section remains 39 mm × 39 mm at every y: the `x`-extent is
  `[column_outer_x(y), column_inner_x(y)]` and the `z`-extent is
  `[-19.5, +19.5]` at every y. Only the centerline curves.

At `COLUMN_BEND_RADIUS = 10000 mm` the outward shift at each end is
`≈ (y - y_mid)² / (2 R)`, giving these keypoint coordinates:

- `NT_BENT ≈ (-21.694, 146.563)` — top column outer face, shifted
  ~34.4 mm outward from the original `NT = (12.700, 146.563)`.
- `NB_BENT ≈ (-8.538, 323.844)` — lower column anchor, shifted
  ~21.2 mm outward from the original `NB = (12.700, 323.844)`.
- At `y = CO.y = 1803.91` (top of base / bass end of the soundboard
  slope), the outer face sits at `x ≈ -21.69`, symmetric with NT.
- At `y = FLOOR_Y = 1915.5`, the outer face sits at `x ≈ -31.60`.

Helpers in `geometry.py`:

- `column_outer_x(y)` — outer face x at height y
- `column_inner_x(y)` — inner face x at height y
- `column_centerline_x(y)` — centerline x at height y
- `_column_bend_x_offset(y)` — signed offset from the straight centerline

The column passes through the top-of-base cap at `y = Y_TOP_OF_BASE =
1803.91` (on its way to the floor) and through the base block as solid
material surrounding it. The base block's column socket must follow the
curved centerline through that interval, not a straight vertical socket.

The top anchor point for downstream neck routing is `NT_BENT`; the
legacy `NT = (12.700, 146.563)` is retained for backwards compatibility
with code that still assumes a straight column but should be migrated
to `NT_BENT`.

### What you need to specify

Where does the neck assembly meet the column? In traditional harps the
neck is a curved piece bridging the top of the column to the soundboard top
at ST. The neck carries the tuning mechanism (pedal discs, tuning pins).

The current project has NT_BENT specified but no geometry for how the neck
curves from NT_BENT to ST. That's your design problem.

### Neck outline leg 3 follows the curved column

The neck outline's closing leg 3 (NTO → NBO along the column outer face)
must track the curved column, not a straight x line. Downstream code
should evaluate `x_outer(y) = column_outer_x(y)` for each y ∈ [NT.y,
NB.y] when drawing or anchoring against that edge.

### Downstream files that need updates to adopt the bent column

These edits are NOT in this changeset; they are listed here so the
migration is tracked:

- `build_harp.py`: `NB.y` derivation (around line 202); `COLUMN_OUTER_X`
  references along any y-parameterized column-side geometry should be
  replaced with `column_outer_x(y)`; `NB` / `NT` imports should migrate
  to `NB_BENT` / `NT_BENT`.
- `optimize_v2.py`: the anchor points NBO, NBI, NTO reference
  `COLUMN_OUTER_X` / `COLUMN_INNER_X`; update each to
  `column_outer_x(y)` / `column_inner_x(y)` at the anchor's own y.
- `build_views.py`: the side-view column silhouette currently uses
  straight vertical x lines; redraw it to follow the arc.
- `neck_geodesic.py`: imports `NB` and `NT` from `build_harp`; once
  `build_harp` migrates, this follows automatically.

## 3. Base–Chamber interface (hidden tongue-and-groove, mirror of shoulder)

### Design intent

Mirror of the shoulder joint, applied at the bass end. The chamber is
OPEN at its bottom rim (`y = Y_TOP_OF_BASE = 1803.91`) — no flat cap.
The base is a discrete part that plugs UP into the chamber from below.
Polarity is OPPOSITE the top end: at the shoulder the chamber held the
tongue and the shoulder held the groove; here the BASE holds the tongue
and the chamber's bottom rim holds the GROOVE. The exterior surface
reads as one continuous limaçon loft, with a thin horizontal seam line
at `y = Y_TOP_OF_BASE` hidden by a shallow chamfer.

### Shared geometry at the interface plane

Horizontal slice of the chamber at `y = Y_TOP_OF_BASE = 1803.91`. By
construction CO sits at exactly this y-value, so the slice corresponds
to `s' = 0` on the soundboard generator (CO is at the bass end of the
extended soundboard).

The chamber loft begins lower down at `s' = S_BASS_CLEAR = -131.59`,
where the limaçon's flat face just meets the floor. The bass-end bulge
of the loft therefore extends BELOW `y = Y_TOP_OF_BASE` — the slice at
`y = 1803.91` is NOT the chamber's lower endpoint. It is a CLIP plane:
everything in the loft below this y belongs to the lofted shape but is
clipped off, and the resulting open bottom is what the base must mate
with. The cross-section at the clip plane is the limaçon at `s' = 0`,
and that is the lens shape the base's tongue and plug must follow.

`D(s'=0) = 231.84 mm` (from `D_of(0)`). This is a BIG opening — the
bass-end bulge is at its second-widest here — so the base is a large
plug, hundreds of millimetres across in plan view, not a small cap.

### Chamber side (the bottom rim)

- Thin-walled limaçon shell, wall thickness ~3–6 mm, terminating
  downward at an annular rim at `y = Y_TOP_OF_BASE`. No flat cap.
- The rim's underside (the face at `y = Y_TOP_OF_BASE`, looking down)
  has a **GROOVE** sized to receive the base's tongue with a
  `BASE_JOINT_BOND_CLEARANCE = 0.15 mm` gap for structural adhesive.
- Groove depth = `BASE_JOINT_TONGUE_HEIGHT = 8 mm`.
- Groove width = `BASE_JOINT_TONGUE_THICK + 2 * BASE_JOINT_BOND_CLEARANCE
  = 2.3 mm`.
- Groove follows the rim's lens shape in plan view.
- The rim also has through-holes for the chamber-to-base fasteners
  (see Fastening below), with **threaded inserts** molded into the
  inside (chamber-interior) surface so screws driven from below thread
  into the inserts.

### Base side (discrete CF or alternative material — vendor's call)

A separate structural part with several functional features:

- **Top face** at `y = Y_TOP_OF_BASE`, mating against the chamber rim's
  underside.
- **TONGUE** rising upward from the top face by
  `BASE_JOINT_TONGUE_HEIGHT = 8 mm`, wall thickness
  `BASE_JOINT_TONGUE_THICK = 2 mm`, following the chamber rim's lens
  shape in plan view, designed to land in the chamber's groove with
  the bond clearance gap.
- **PLUG** solid extending upward from the top face by
  `BASE_PLUG_DEPTH = 20 mm` into the chamber interior. Its horizontal
  cross-section at each `y ∈ [Y_TOP_OF_BASE - BASE_PLUG_DEPTH,
  Y_TOP_OF_BASE]` matches the chamber's interior cross-section at the
  same y (so the plug fills the chamber's open bottom up to that
  depth, restoring rigidity at the open end).
- **LOWER BODY** extending downward from the top face to
  `y = FLOOR_Y = 1915.5`, providing floor contact and structural mass.
- **COLUMN SOCKET** in the lower body, receiving the column's bottom
  end. The column extends from NT at the top of the harp through the
  chamber interior down into this socket. Socket cross-section matches
  the column prism (`x ∈ [12.7, 51.7]`, `z ∈ [-19.5, 19.5]`) plus a
  bond/sliding clearance.
- **THROUGH-HOLES** for the chamber-to-base fasteners, aligned with
  the threaded inserts in the chamber rim above.

### External seam

At `y = Y_TOP_OF_BASE` the two parts meet in a thin horizontal seam on
the exterior. Hidden by a **chamfer of depth `BASE_JOINT_CHAMFER = 1
mm`** on both the chamber's lower edge and the base's upper edge — the
chamfer reads as a design detail rather than a gap.

### Fastening

- **Base to chamber**: M4 or M5 cap screws enter from BELOW the
  instrument (the underside of the base), pass UP through the base's
  through-holes, through the chamber rim, and thread into the
  threaded inserts in the chamber rim's interior face. Default
  pattern: 4 fasteners, roughly at the lens's N/S/E/W extrema.
- Fasteners are invisible in normal use (underside of harp).

## 4. What you must not change

- Any of the points in `geometry.py` (`CO`, `CI`, `ST`, `NT`, `NB`, floor)
- The limaçon taper `D(s')` over `[S_BASS_CLEAR, S_TREBLE_CLEAR]`
- The clipping planes (`Y_FLOOR`, `Y_ST_HORIZ`, `Y_TOP_OF_BASE`)
- The grommet positions

If any of these need to change, we need a joint conversation about what
else shifts as a consequence.

## 5. What you're free to design

- Neck body profile from NT to ST
- Where the neck meets the column structurally (socket, mortise, cap)
- Tuning pin positions (one per string — 47 pins)
- Pedal disc / mechanism mounting (if this is pedal harp)
- Cap or socket geometry at the ST interface
- Decorative features (capital at column top, neck volute, etc.)

