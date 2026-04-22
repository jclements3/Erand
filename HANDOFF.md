# Clements 47 — handoff notes (2026-04-21 late evening)

Read this file and `NECK_STATUS.md` before touching anything. This file supersedes anything in NECK_STATUS that contradicts it.

## TL;DR — what changed in the most recent passes

**Pass 2026-04-21 very-very late — visual-product detail drawings**

1. **Guitar tuner in side view** at each string end: small circle at `flat_buffer` position, Ø `GEAR_POST_DIA`, parity-colored (orange odd / blue even).
2. **`pedal/tuner_side.svg`** redrawn to match user's reference `guitartuner.png` — worm driver teardrop head + threaded shaft, visible product silhouette instead of busy engineering section. Case, cap, gear post, plywood shown with callouts.
3. **`pedal/clicky_side.svg`** redrawn to match user's reference `clickypen.jpg` — green pusher on top, translucent gray barrel, pink crenellated cam sleeve, blue tri-lobed mounting flange, shaft + paddle through plywood into the string gap. Product silhouette, gradient fills, no section hatching.

---

**Pass 2026-04-21 very late — alternation + tangent flat pin (commit `c8de11d`)**

1. **Hole alternation by string parity.** Convention: **EVEN strings** drill through the **+z (right) plate**; **ODD strings** through the **−z (left) plate**. No single x has holes through both plates — the neck would split under string tension otherwise.
2. **Top view** now draws three drill holes per string on the active plate: tuner gear-post (Ø 16 mm, white), nat clicky shaft (Ø 6.5 mm, blue), sharp clicky shaft (Ø 6.5 mm, red). Holes are centered on the plate midline.
3. **Front/rear views**: tuner body `z_sign` flipped to match the new convention (was odd=+z, now even=+z).
4. **Side view flat pin**: now drawn as a small circle (R = 1.5 mm) **tangent to the east side of the string**, not centered on it. String wraps around the pin's east side heading NE to the tuner. Clicky rings stay centered on the string (they press down to kill vibration).

**Pass 2026-04-21 evening — nat buffer + guitar tuner (commit `1fc0463`)**

1. **Third buffer per string added**: `nat_buffer = _natural(pin, grom)` in `build_harp.build_strings()`. Each string now has three R=12 buffer circles (flat = guitar tuner hole, nat = natural clicky, sharp = sharp clicky). `erand47.svg` now renders **141 buffer circles** (47 × 3) color-coded: gray for flat/tuner, blue for nat, red for sharp. After `SKIPPED_BUFFERS`, the actual feasible set is 36 flat + 47 nat + 38 sharp = 121.
2. **Neck outline still valid**: `neck_geodesic.py` now asserts all 47 nat buffers sit inside the pink-polyline envelope (they do — they're topologically interior to the region bounded by flat-side sharps and north-side flats). No neck redesign needed; the existing v2 Bezier still clears all three buffer sets.
3. **Guitar tuner design adapted**: Thingiverse 6099101 by noamtsvi (CC-BY-NC). STLs, PDF, and images live in `pedal/reference/thingiverse-6099101-noamtsvi-guitar-tuners/` — bulky files gitignored, attribution files + `dimensions.md` committed. `build_views.py` tuner constants (`TUNER_BODY_W/H/D`, `TUNER_KNOB_DIA`, `TUNER_KNOB_OUT`) updated to real STL dimensions, plus new `GEAR_POST_DIA = 15.4` constant. Gear post Ø 15.4 + 8 mm wall ≈ R=12 buffer allowance, confirming the buffer radius matches the hardware.
4. **Second detail panel in viewer**: `pedal/tuner_side.svg` (new, 1:1 dimensioned section view of the guitar tuner). `index.html` bottom-of-column-2 now splits horizontally into Clicky pen | Guitar tuner panels. `expand` fullscreens either; Escape returns.
5. **CC-BY-NC license**: the guitar tuner is non-commercial only. Clements 47 as DIY/research is fine, but flag if ever commercializing.

## Big design goal

Fully **parameterized** harp design. Editing a small set of inputs — primarily the per-string configuration in `strings.py` — should regenerate the neck, soundbox, column, and views consistently. The pipeline is:

```
strings.py                    ← single source of truth for per-string data
    ↓
build_harp.py                 ← neck + strings + buffers + emits erand47.svg
soundbox/geometry.py          ← chamber + grommets + clipping planes
inkscape_frame.py             ← Inkscape↔authoring DX/DY (shared)
    ↓
neck_geodesic.py              ← pink geodesic polyline (inner bound)
optimize_v2.py                ← brown Bezier neck (outer bound, ≥ R_BUFFER clearance)
    ↓
build_views.py                ← five orthogonal view SVGs for index.html
```

Change a string (diameter, position), change `R_BUFFER`, or scale the soundboard axis, and everything downstream derives. This refactor is in place but **not yet end-to-end wired** — see "Remaining cleanup" below.

## Big design change: no foot pedals

**No foot-pedal mechanism.** Pitch change is by **per-string clicky-pen assemblies** embedded in the two-plywood neck. Original plan: one clicky per natural and one per sharp = 94 total. **Open issue (2026-04-21):** at treble strings (F7, G7), the natural and sharp pitch points on the string are only ~3.4 mm apart — a 6.5 mm drilled shaft hole can't fit both. Mechanism needs rework at treble: either skip sharp on treble, single-hole multi-state cam, or rotating disc shared between states. Not yet decided.

The 94 buffer circles (R = 12 mm) in `build_harp.py` = guitar tuner pin centers (47, at `flat_buffer` positions) + clicky pen centers (47, at `sharp_buffer` positions). Each buffer represents the material allowance around a drilled hole so the neck doesn't split under string tension. Clicky design detail lives in `pedal/` (`integration.md`, `paddle.svg`, `packing.svg`, `clicky_side.svg` — new, cam-click bistable mechanism).

## Current canonical neck: `erand47jc_v2_opt.svg`

10-node cubic Bezier, optimizer-tuned by `optimize_v2.py`, plus **three manual post-optimizer tweaks** (the user directed these; do not revert via re-optimization):

| Node | Authoring coord | Constraint |
|---|---|---|
| n0 NBO | (12.70, 323.84) | Locked. Horizontal out. |
| n1 NBI | (51.70, 323.84) | Locked. Horizontal in from NBO. |
| n2 D1sbi | on D1-sharp circle | Slide-on-circle (1 DoF). Cusp, handles on outside side. |
| n3 E5s | on E5-sharp circle | Slide-on-circle. Collinear handles along tangent. |
| n4 G7sbi | on G7-sharp circle | Slide-on-circle. Handle length **locked at w4_out = 29 mm, w4_in = 78 mm** (user). |
| n5 ST | **(838.784, 481.939)** | Locked. Matches `soundbox.ST` (no longer lowered to 494.27). In along +u, out horizontal. **w5_in manually tweaked to 15 mm** for gentle arc. |
| n6 BT | **(906.632, 481.877)** | Locked. Derived from `bulge_tip_point(S_TREBLE_CLEAR)`. In horizontal, out along +u. |
| n7 G7fbi | on G7-flat circle | Slide-on-circle. Collinear + symmetric handles. |
| n8 | free 2D | Collinear handles (smooth). |
| n9 NTO | (12.70, 146.56) | Locked. Closing leg 3 back to NBO. |

**Changes since last handoff:**
- ST moved from (838.784, 494.265) → (838.784, 481.939) to match `soundbox.Y_ST_HORIZ`. BT moved from (902.84, 494.27) → (906.632, 481.877) — now derived from `bulge_tip_point(S_TREBLE_CLEAR)`. Neck is now flush with the chamber's flat top instead of dangling 12.33 mm below.
- F7 sharp added to `SKIPPED_BUFFERS` (the ST→BT horizontal line at y=481.939 passes through F7sb; no longer wrapped).
- `w4_out` and `w5_in` manually shortened from their optimizer values to tighten the ST approach into a smooth arc (no more self-intersecting hook between G7sbi and ST).
- BT→G7fb cubic handles left at their optimizer values (user confirmed the outer loop shape is correct).

## Refactor state (2026-04-21 cleanup pass)

Landed by three parallel agents:

1. **`strings.py` (new)** — single source of per-string data: 47 `StringSpec(note, pin_x, pin_y, grommet_y, diameter)` entries. Matches `build_harp._RAW_GEOM/_NOTE_SEQUENCE/_STRING_WIDTHS` exactly. Not yet wired into build_harp — `_RAW_GEOM` still duplicates it. Next cleanup pass: have build_harp.py `from strings import STRINGS` instead of maintaining its own table.

2. **`inkscape_frame.py` (new)** — single source for `INKSCAPE_DX = 51.9`, `INKSCAPE_DY = 81.27`, plus `to_authoring()` / `to_inkscape()` helpers. Both `build_views.py` and `optimize_v2.py` now import from here instead of redefining the offset locally.

3. **`build_harp.py`** — `_FLAT_BUFFER_CENTERS` table replaced by `pin + FLAT_BUFFER_OFFSET` computation. Default offset = (9.1, -38.1); strings 1-4 (C1-F1) keep a bass override of (11.1, -38.1) because collapsing them to uniform would shift 2.003 mm (at threshold). Max buffer drift from the original hand-set table: 0.025 mm. `erand47.svg` regenerates byte-identically except for the four affected strings.

4. **`optimize_v2.py`** — `R_BUF` now reads from `bh.R_BUFFER`. Circle anchors D1SB/E5S/G7SB/G7FB now resolved by note name from `bh.build_strings()` instead of by hardcoded SVG circle-order index. `INKSCAPE_DX/DY` now imported from `inkscape_frame`.

5. **`soundbox/geometry.py`** — split into `--- DESIGN PARAMETERS ---` and `--- DERIVED QUANTITIES ---` sections. `GROMMETS` table now computed via `grommet_sp(i)` from a six-tier pitch schedule + per-string residuals (residuals are zero in a clean design; preserved here for the 1901 Erard reference). `SCALE_FACTOR`, `STRING_COUNT`, `PITCH_RANGE_LO/HI`, `D_PEAK_BASE`, `CO_XY`, `NB_XY_BASE`, `NT_XY_BASE`, etc. are now editable top-level inputs. Output is numerically identical to pre-refactor within 0.024 mm.

## Remaining cleanup (for a future pass)

Per Agent 1's flagged list:

- `build_views.py:55-104` still has its own `PIN_XY`, `GROMMET_Y`, `STRING_DIAMETERS`, `PIN_NOTES` tables — duplicate `strings.py`. Switch to `from strings import STRINGS`.
- `build_views.py:387-390` hardcodes the v2 neck's closing cubic control points as Inkscape-frame literals (used by the column-top-cap calculation). If the v2 optimizer re-runs and the closing cubic moves, this silently goes stale. Refactor to read the cubic from `erand47jc_v2_opt.svg` at runtime.
- `optimize_v2.py:68-72` hardcodes NBO/NBI/ST/BT/NTO in Inkscape frame. Should derive from `bh.NB`, `bh.ST`, `bh.NT` via `inkscape_frame.to_inkscape()`.
- `optimize_v2.py:38` — `U = (0.52992, -0.84800)` duplicates `soundbox.geometry.u`. Import it.
- `build_harp.py:54` — `NB = (12.700, 323.844)` with the comment noting `323.844 = C1_sharp_buffer_y + R_BUFFER`. This literal locks NB to R_BUFFER=12; the stated refactor goal is to let R_BUFFER change freely. Parameterize, but requires coordinating with `soundbox/interfaces.md` §3 (NB is on the locked-points list).
- `strings.py` not yet imported by `build_harp.py` — table is duplicated there.

## Drawing state (for reference)

All the view-side clip/conformance fixes landed:
- Chamber clipped at `FLOOR_Y` (bass end) and at `Y_ST_HORIZ` past ST (treble end) — gives the chamber a flat top that the neck sits on flush.
- Base block now conforms to the bulge-tip curve on the east and to the flat face on the west, wrapping the column on both sides from `Y_TOP_OF_BASE` to `FLOOR_Y`.
- Column top is no longer a flat horizontal; follows the neck's closing cubic between `COLUMN_OUTER_X` and `COLUMN_INNER_X` so the column blends into the neck.
- Front/rear view silhouettes clipped at `FLOOR_Y` (no more below-floor dangling).
- Side view shows the full 94 buffer circles plus filled tuner/clicky centers colored by odd/even string.
- Viewer has a sixth panel (`index.html`): clicky-pen detail in column 2 beneath the top view.

## Files that matter

- **Per-string config:** `strings.py` (authoritative, 47 `StringSpec` entries).
- **Neck outline:** `erand47jc_v2_opt.svg` (canonical, includes the three manual post-opt tweaks). `erand47jc_v2.svg` = user-edited baseline before optimizer.
- **Optimizer:** `optimize_v2.py` — cleaned up but still has the `w4_out`/`w5_in` locks and the hardcoded Inkscape coords flagged above.
- **View builder:** `build_views.py` + `index.html`.
- **Inner bound (geodesic):** `neck_geodesic.py`. Emits pink polyline into `erand47.svg`; now terminates at G7sb/G7fb east poles (per user) with a connector line between them; brown Bezier wraps externally.
- **Soundbox source-of-truth:** `soundbox/geometry.py` (now parameterized). **Do NOT edit `CO`, `CI`, `ST`, `NT`, `NB`, `FLOOR_Y`, `SOUNDBOARD_DIR` without a joint conversation per `soundbox/interfaces.md` §3** — the `_BASE` constants in `DESIGN PARAMETERS` are the edit surface.
- **Pedal/clicky design:** `pedal/integration.md`, `pedal/clicky_side.svg` (new: cam-click bistable mechanism, dimensioned).
- **Legacy:** `erand47jc.svg`, `erand47jc_opt.svg`, `optimize_jc.py` kept for reference only. Not current.

## Transport archive

`erandharp.txt` — ai-tar v2 format, ~1.3 MB, 38 files. Generated by:
```bash
ai-tar.py . --include-ext .py .md .svg .html .json .csv \
    --exclude "*.png" "*.jpg" "*.dxf" "*.odg" "fitneck*.py" "harp_profile*.py" \
              "erand47_dec_*" "erand47_fast*" "erand47_med*" "erand47_slow*" \
              "erand47_{side,top,front,rear,sbf,views}.svg" \
              "erand47jc.svg" "erand47jc_opt*" \
              [... see commit for full list] \
    -o erandharp.txt
```
Contains all source code, docs, canonical SVGs, and configs needed to continue design work. Excludes regeneratable view SVGs, failed-fit explorations, binaries, and reference images.

## Open questions

1. **Treble clicky mechanism** — 6.5 mm holes for nat + sharp physically collide on F7/G7 because semitone spacing < hole diameter. Design decision pending.
2. `SKIPPED_BUFFERS` list — review after the clicky mechanism choice above.
3. Whether to wire `strings.py` → `build_harp.py` in the next pass (eliminates `_RAW_GEOM` / `_NOTE_SEQUENCE` / `_STRING_WIDTHS` duplication).
4. Whether to parameterize `NB.y = C1_sharp_south_pole + R_BUFFER` — coupling flagged by Agent 1, but `NB` is on the locked-points list in `interfaces.md` §3.
5. Flush-mount of the chamber vs. F7sb — F7 sharp was skipped so the ST→BT line at y=481.939 doesn't penetrate it. Stress analysis if buffer radius increases will need to reconsider which strings to skip.
