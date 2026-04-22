# Thingiverse 6099101 — 3D-printed guitar tuners (noamtsvi)

Source: https://www.thingiverse.com/thing:6099101

Designer: **noamtsvi**
License: **CC-BY-NC** (Creative Commons, Attribution, *Non-Commercial*).
Any use in a future Erand/Clements-47 build that leaves the workshop for
money or trade needs to respect that: these parts, as printed from these
STLs, can't be sold. A clean-room redesign using only the dimensions
recorded here is fine for a commercial instrument; the STLs themselves
are reference only.

## Raw STL bounding boxes (mm)

Measured axis-aligned from the STL files as shipped. Units are millimeters.
`L × W × H` in STL file-axis order (not oriented for the harp — see the
role mapping below).

| Part                                          |   L   |   W   |   H   |
|-----------------------------------------------|------:|------:|------:|
| case_left.STL / case_right.STL                | 39.2  | 12.6  | 19.4  |
| case_left_thicker.STL / case_right_thicker.STL| 39.2  | 13.2  | 21.4  |
| cap_left.STL / cap_right.STL                  | 23.7  |  4.3  | 17.4  |
| cap_thicker_left.STL / cap_thicker_right.STL  | 23.7  |  4.3  | 18.4  |
| gear_post_single_thread_left.STL              | 15.4  | 42.6  | 15.4  |
| gear_post_single_thread_mirrored.stl          | 15.4  | 42.6  | 15.4  |
| gear_post_double_thread_left.STL              | 15.4  | 42.6  | 15.4  |
| gear_post_double_thread_mirrored.stl          | 15.4  | 42.6  | 15.4  |
| worm_driver_single_thread_left.STL            | 19.3  | 10.0  | 47.7  |
| worm_driver_single_thread_mirrored.stl        | 19.3  | 10.0  | 47.7  |
| worm_driver_double_thread_left.STL            | 19.3  | 10.0  | 47.7  |
| worm_driver_double_thread_mirrored.stl        | 19.3  | 10.0  | 47.7  |

"Thicker" variants are the designer's beefed-up casing option; the original
case/cap work fine if the print is solid. Single- vs double-thread gear-post
and worm-driver pairs give different mechanical advantage (double-thread
turns a string faster per knob rotation; single is finer).

## Role in the Clements 47 neck

The harp neck is two 6 mm plywood sides separated by a 12.7 mm (1/2") gap
(see `NECK_Z_INNER` / `NECK_Z_OUTER` in `build_views.py`). For each string
one of these tuners is mounted crosswise to the neck axis, with:

| Part          | Role in the harp                                                                 |
|---------------|----------------------------------------------------------------------------------|
| **case**      | Main body. Mounts on the **outer** face of the plywood side. Holds the worm.     |
| **cap**       | Retainer on the outer face of the case; keeps the worm driver from sliding out. |
| **gear_post** | **Tuning pin** — the cylinder the string wraps around. Passes through the 6 mm plywood into the string gap. Its 42.6 mm length is enough to span the 6 mm plywood plus a few turns of string inside the gap. |
| **worm_driver** | **Knob end**. 47.7 mm long, 19.3 mm across. Sticks outward from the plywood face; user turns this to tune. |

The "left" and "mirrored" / "right" files let us alternate which side of
the neck the knob sits on — matching the existing +z / -z alternation by
string number (odd strings → right plywood, even → left).

## Harp-side fit check

`build_harp.py` defines `R_BUFFER = 12 mm` — the radial clearance reserved
around each tuning-pin center so adjacent strings don't collide with the
tuner hardware. The gear post is Ø 15.4 mm, so its radius is 7.7 mm and
leaves 12 - 7.7 = **4.3 mm** of wall clearance between the post wall and
the next string's buffer. That is tight but workable for 3D-printed
hardware; a commercial brass pin would be much thinner.

The case (39.2 mm along the string direction, 12.6 mm across) sits on the
outer plywood face and does **not** intrude into the 12.7 mm inter-plywood
gap, so the string path inside the neck is unaffected.
