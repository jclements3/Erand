# Interfaces the Neck Chat Owns

The soundbox chamber geometry is fully specified in `geometry.py`. Your job
is to design the neck assembly and make sure it mates cleanly at the
two interfaces below.

## 1. Neck–Chamber interface (at ST horizontal plane)

### What the soundbox provides

The limaçon loft runs from `s' = -131.59` to `s' = 1594.86`. Past ST
(`s' = 1558.86`), the chamber continues for 36 mm and narrows from
D=74.13 at ST to D=63.23 at the clearance point, at which station the
bulge tip exactly touches the ST horizontal plane (`y = 481.939`).

### The interface plane

Horizontal plane at `y = Y_ST_HORIZ = 481.939`. Everything the neck
assembly adds must sit at `y ≤ 481.939` (at or above the plane, in the
physical upward direction). Everything the neck assembly subtracts from
the chamber must be at `y < 481.939` with `x` past ST.

### Footprint at the interface plane

Horizontal slice of the chamber at `y = 481.939`:

- Extent: `x ∈ [818.6, 891.4]` mm, `z ∈ [-35.8, +35.8]` mm
- Roughly 74 × 72 mm, lens/eye shaped
- ST point `(838.78, 481.94)` sits inside this slice, 20 mm from left edge,
  53 mm from right edge
- The neck rests on (or is bolted to) material at or around this footprint

### Recommended approach

Either:
1. Cap the chamber at `y = Y_ST_HORIZ` with a structural plate in the neck
   assembly (simplest — gives you a flat mounting surface).
2. Let the chamber open upward past ST and have the neck socket into the
   opening (more traditional on wooden harps).

Either way, the soundbox loft extends past ST into the cutoff zone, so your
Boolean subtraction will produce clean surfaces whichever approach you take.

## 2. Neck–Column interface (at the top of the column)

### What the soundbox side provides

The column is a rectangular prism:

- `x ∈ [12.7, 51.7]` (width 39 mm in x)
- `z ∈ [-19.5, 19.5]` (assumed width 39 mm in z — confirm if actual column
  is different; update `geometry.COLUMN_Z_HALF` if so)
- Extends from some top y (your choice) down through the base block to
  `y = FLOOR_Y = 1915.5`

The top anchor point per the legacy project data:
- `NT = (12.700, 146.563)` — top of column outer face

The column passes through the top-of-base cap at `y = 1803.91` (on its way
to the floor) and through the base block as solid material surrounding it.

### What you need to specify

Where does the neck assembly meet the column? In traditional harps the
neck is a curved piece bridging the top of the column to the soundboard top
at ST. The neck carries the tuning mechanism (pedal discs, tuning pins).

The current project has NT specified but no geometry for how the neck
curves from NT to ST. That's your design problem.

## 3. What you must not change

- Any of the points in `geometry.py` (`CO`, `CI`, `ST`, `NT`, `NB`, floor)
- The limaçon taper `D(s')` over `[S_BASS_CLEAR, S_TREBLE_CLEAR]`
- The clipping planes (`Y_FLOOR`, `Y_ST_HORIZ`, `Y_TOP_OF_BASE`)
- The grommet positions

If any of these need to change, we need a joint conversation about what
else shifts as a consequence.

## 4. What you're free to design

- Neck body profile from NT to ST
- Where the neck meets the column structurally (socket, mortise, cap)
- Tuning pin positions (one per string — 47 pins)
- Pedal disc / mechanism mounting (if this is pedal harp)
- Cap or socket geometry at the ST interface
- Decorative features (capital at column top, neck volute, etc.)

