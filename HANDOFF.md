# Clements 47 — handoff notes (2026-04-24)

Read this file and `NECK_STATUS.md` before touching anything. This file supersedes anything in NECK_STATUS that contradicts it.

**Sync contract:** this doc is the sync surface between the desktop Claude Code chat and the claude.ai home chat. Every meaningful design decision, parameter change, or pending task from either side lands here. When you finish a pass, update the TL;DR at the top and the Open Questions at the bottom.

## TL;DR — what changed in the most recent passes

**Pass 2026-04-24 evening — acoustic fine-tune, pitch-mechanism research, FreeCAD in-flight**

Follow-on to the morning's acoustic pass. All earlier "in-flight" items are now MERGED, plus several new items and two new design paths for the pitch mechanism. A FreeCAD parametric model is in-flight via a background agent.

MERGED on top of the morning pass:

- **Base scoop rim shrunk 128.25 → 120.75 mm** so the paraboloid fits inside the chamber (previously overshot by 3.9 mm z, 9.8 mm xy at east bulge). Vertex/focus/focal-length re-derive automatically. ~2 mm margin at both faces.
- **Shoulder diffuser clipped to the actual shoulder footprint** in `shoulder_diffuser_arc_xy()`. First with hard vertical walls at x=ST.x, x=BT.x; then refined to a SLOPED clip following the soundboard tangent (`slope = |u.x/u.y| = 0.625`) so the diffuser boundaries taper inward correctly as y decreases into the shoulder body.
- **Shoulder features sunk 8 mm above the tongue joint.** Added `SHOULDER_FEATURE_CLEARANCE_BASE = 8.0`. `SHOULDER_DIFFUSER_CENTER_XY_BASE y` moved 481.94 → 473.94. `TREBLE_SCOOP_HW y` similarly moved, sunk above the tongue-and-groove joint plane. Diffuser apex now at y=458.94, treble scoop vertex at y=457.55, both well clear of the 8 mm tongue rising from `Y_ST_HORIZ`.
- **Render order swap**: diffuser rendered FIRST, treble scoop ON TOP — so the scoop (smaller, deeper local pocket) reads as nested INSIDE the broader diffuser. Matches the physical geometry where the scoop is carved locally inside the diffuser's depression.
- **Base polygon has the scoop notch properly carved** into the tilted top edge. Walks HW → parabola through vertex → RIM_FAR → east-bulge intersection → down east bulge → floor → implicit close along soundboard.
- **Rear view fixes**: (a) silhouette "floor cap" bug fixed — the cap was inserted at the TREBLE end (via `upper_y[-1]`) instead of the BASS end, producing a spurious vertical white stripe at y=459. Changed to `insert(0, ...)` at the bass end. (b) Sound holes added to the rear view — 4 filled circles on the chamber silhouette at each hole's `center_xy.y` in the rear-view yz projection. (c) Column removed from the rear view (hidden behind the chamber bulge from the rear).

New design-path memos (research only, not integrated):

- **`pedal/dual_prong_toggle.md`** — disc-capture toggle modeled on real pedal-harp discs (see `images/pedal-harp-discs.jpg`). Ø10 disc inside the 12.7 mm plate gap, Ø3 axle through the plate, two Ø1.5 mm pegs on the disc's inboard face that SWING across the string's rest lane when the disc rotates 180°. Pegs GRIP the string between them (no backstop needed — pegs themselves are the pivot). Actuation: Ø12 mm knurled thumb-knob on the outboard plate face, rotated directly by the thumb. Bistable ball-and-cup detent, ~1.5 N. Replaces one clicky pen per pitch point with a smaller Ø3 hole (vs clicky's Ø6.5). Fits F7/G7 where clickies can't.
- **`pedal/ganged_disc_lever.md`** — pedal-harp-style hand-pull levers at the base of the neck, one per pitch class (C/D/E/F/G/A/B). Each lever pulls a rigid CF rod along the outboard plate face; rod connects to all discs of that pitch class via a 2 mm crank arm at every pitch point. 180° axle rotation per engagement. Ball-and-cup bistable detent per disc holds state. 8:1 mechanical advantage → 1.3 N peak at lever. Trades per-string independence for pitch-class speed (matches pedal harp UX but hand-operated).
- **New viewer panel** in `index.html`: bottom-split now has 3 columns (clicky pen | guitar tuner | ganged disc-lever sketch). `pedal/ganged_disc_lever.svg` shows the schematic of one pitch class with 6 discs linked on a rigid rod.

Pitch-mechanism decision (MADE 2026-04-24 evening):

- **GANGED DISC-LEVER is the chosen pitch mechanism.** Per-string disc toggles with thumb knobs, ganged by pitch class via rigid rods on the outboard plate face, driven by 7 hand-pull levers at the base of the neck. One lever per pitch class (C/D/E/F/G/A/B). Pedal-harp UX without foot pedals. See `pedal/ganged_disc_lever.md` for mechanical scheme + force/travel analysis.
- Clicky pens are **superseded**, not yet removed from the code. The existing clicky-pen buffer positions (`nat_buffer`, `sharp_buffer` in `build_harp.build_strings()`) translate directly to disc-toggle positions — same s' locations along each string, just a different actuator at each spot.
- Per-string disc toggles (`pedal/dual_prong_toggle.md`) remain documented as the underlying per-disc actuator — the ganged lever drives these discs via bell cranks. The two memos are complementary, not alternatives.
- Integration into `build_harp.py`, `build_views.py`, `build_step.py` is NOT done yet. Next pass: replace clicky-pen rendering with disc rendering, add the pitch-class rod visualization on the outboard plate face, add the hand-lever bank at the base. Hole count drops from 94 × Ø6.5 (clicky) to 94 × Ø3 (disc axles). Re-check neck-outline clearance in `optimize_v2.py` with the smaller R_BUFFER.

IN-FLIGHT (commit NOT landed on main yet):

- **FreeCAD parametric harp model** — background agent is building `build_freecad.py`. Intended to produce the full 3D harp assembly (chamber limaçon loft, base plug with scoop cut, shoulder with diffuser + treble-scoop cuts, bent round column, two neck plates with drill holes, 4 sound holes, elliptical soundboard column hole) parametrically from `soundbox/geometry.py` values, runnable as a FreeCAD macro. Not yet merged; commit on the agent's worktree branch. Check git log on return — if missing, re-dispatch.

Open issues (this pass):

- **FreeCAD model not tested in FreeCAD.** The agent can't run FreeCAD in its environment. Expect small API adjustments when first opened in FreeCAD; flagged in the generated file's docstring.
- **Disc-toggle, ganged-lever, and ganged+slip-clutch (hybrid) pitch mechanisms are documented but not integrated into `build_harp.py`, `build_views.py`, or `build_step.py`.** Choosing one for integration is a user-decision pending.
- **Sound-hole rear-view rendering** draws the full hole diameter as a circle at `(z=0, y=center_xy[1])`. In 3D the hole axis is local +n (perpendicular to the bulge face), so from directly behind the hole is shown foreshortened as an ellipse, not a circle. Cosmetic only for now; fix when a proper yz-projection pipeline lands.

---

**Pass 2026-04-24 — acoustic pass: base scoop, sound-hole resize, shoulder diffuser, treble scoop, tilted-base-top**

Acoustic-geometry session. The chamber exterior is unchanged in overall envelope but gains focused curvature features aimed at HF radiation. Two sister agents are still in-flight on clipping + rim-radius tuning; merge their work before claiming this pass is final.

New features + parameters (all in `soundbox/geometry.py`):

- **Base scoop (paraboloid of revolution)** — `SCOOP_*` block. Parabolic bowl cut into the base-block top. Anchor `HW` = midpoint of `CSB_E` (column-east edge meets soundboard) and `C1G` (C1 grommet). `rim_radius = 128.25 mm` (**in-flight: sister agent is shrinking this** — current radius overshoots the chamber by 3.9 mm in z and 9.8 mm in xy, so expect a slightly smaller final value, TBD), `depth = 60 mm`, `vertex = (140.65, 1812.64)`, `focus = (229.77, 1720.01)`. Aimed at the sound-hole cluster centroid `(669.12, 1263.30)` so the reflector focuses energy up and through the holes.
- **FLOOR_Y_BASE raised 1860 → 1870** to accommodate the 60 mm scoop depth without pushing through the floor plane.
- **Sound holes resized** — `SOUND_HOLES_BASE` list of `(label, s', diameter)`:
  - bass Ø130 @ s' = 480
  - mid Ø115 @ s' = 850
  - treble Ø140 @ s' = 1300 (enlarged from Ø100)
  - treble2 Ø75 @ s' = 1475 (new)
- **Shoulder diffuser** — `SHOULDER_DIFFUSER_*` block. Concave spherical depression in the shoulder underside, `R = 250`, `d = 15 mm`, centred at midpoint(ST, BT). Scatters HF arriving at the shoulder. `H_SHOULDER` raised 30 → 40 mm to host the depression. **In-flight:** sister agent is clipping the render to the ST–BT region and reordering the render stack so shoulder features draw on top of strings.
- **Treble scoop** — `TREBLE_SCOOP_*` block. BT-anchored paraboloid embedded in the shoulder; `r = 30`, `d = 12 mm`. Small, locally focused HF reflector in the treble region.
- **Base polygon top is now TILTED** (coincident with the base-scoop rim chord) rather than horizontal. Outline now walks HW → parabola through vertex → RIM_FAR → east-bulge intersection → down east bulge → floor → implicit close along soundboard. The old horizontal top-of-base segments are gone.
- **Rear view: column removed** — the column is hidden behind the chamber bulge from the rear, so the rear view no longer draws it. Only tuner bodies + column presence differentiate front vs rear otherwise.
- **New named points** `CSB_E`, `CSB_W` — column–soundboard intersection ellipse endpoints, used as anchors for the base-scoop walk.

Acoustic design decisions (the "why"):

- **Paraboloid wins over limaçon-shape bowl for HF focusing.** A paraboloid has a true focal point; the limaçon bowl would just be a generic concavity. Focusing is only acoustically meaningful when the rim diameter exceeds the wavelength — for the 256 mm rim that's **f > 1340 Hz** (λ < 256 mm). Below that, volume matters more than curvature, so the scoop is not a low-frequency feature; it's a treble/brightness lever.
- **Sound-hole enlargement is the bigger HF radiation win.** The treble hole went Ø100 → Ø140 and a new treble2 Ø75 was added. Geometry-for-radiation beats geometry-for-reflection in this band; the scoops are secondary focusing features.
- **Chamber volume stays approximately constant.** The scoop subtracts ~1.6% of the ~93 L chamber volume (numerically integrated limaçon loft). Not enough to change the low-frequency response.
- **Shoulder diffuser is a scatterer, not a focuser.** `R = 250` spherical concavity at the shoulder underside diffuses HF that would otherwise bounce between parallel shoulder and string plane.

Open issues (acoustic pass):

- **Base-scoop rim radius** — currently overshoots the chamber; sister agent is shrinking `rim_radius` to fit inside the limaçon envelope. Pending merge; do not lock the 128.25 value.
- **Shoulder diffuser render clipping** — overshoots ST–BT without clip; sister agent is adding ST–BT clip + render-order fix. Pending merge.
- **Rear view silhouette** = front view silhouette (chamber is z-symmetric); only tuner bodies + column absence differentiate. Acknowledged design feature of a z-symmetric instrument.

Won't fix / prototype accepted:

- **Front vs rear visual differentiation is intentionally subtle.** The chamber is z-symmetric; we are not introducing asymmetric geometry just to liven up the rear view.
- **STEP export (`build_step.py`) still only covers neck plates.** Chamber + base + shoulder STEP exports are deferred to a later vendor pass. Acceptable for the current prototype stage.
- **Sub-1340 Hz focusing** — paraboloid curvature is acoustically inactive below 1340 Hz. Accepted; the low-frequency response is volume-driven (chamber ≈ 93 L, mostly preserved).

---

**Pass 2026-04-23 — shoulder/base hidden joints + bent round column + vendor schedules (commits `1365e5f`, app-asset refresh after)**

Big structural pass. The chamber/column/base topology is now meaningfully different from v2 and the docs had to catch up.

1. **Hidden tongue-and-groove joints** at two places:
   - **Shoulder ↔ chamber** at `Y_ST_HORIZ`. The chamber and shoulder are two separately molded thin-wall CF parts that butt along a hidden tongue-and-groove so the exterior limaçon loft reads as one surface. Params: `SHOULDER_JOINT_*` in `soundbox/geometry.py`. Spec in `soundbox/interfaces.md §1`.
   - **Base ↔ chamber** at `Y_TOP_OF_BASE = 1699.49`. The chamber is **one continuous limaçon tube from `Y_ST_HORIZ` down to `FLOOR_Y`**; the base is an **internal plug** that slides up inside the chamber's bottom and carries the column socket. Params: `BASE_JOINT_*`. Spec in `soundbox/interfaces.md §3`. Do **not** re-introduce the old "chamber clipped at top of base" model — that got explicitly rejected ("the lemicon shape does not extend to the floor" → fixed by making chamber one tube; base is *inside* it).
2. **Column is now round Ø39 + gently bent**:
   - `COLUMN_IS_ROUND = True`, `COLUMN_Z_HALF_BASE = 19.5` = radius. Round because classical Erards are round and filament-wound CF tubing is easier than a square prism.
   - `COLUMN_BEND_ENABLED = True`, `COLUMN_BEND_RADIUS = 10000 mm`, `COLUMN_BEND_DIRECTION = +1` (arc bulges toward the strings). Tangent-vertical at `y_mid = 975.24`.
   - **Per-face vertical thresholds** (below these y-values each face goes vertical so the column-bottom slides straight into the base socket):
     - `COLUMN_INNER_VERTICAL_Y = 1699.49` (inner/east face meets the soundboard)
     - `COLUMN_OUTER_VERTICAL_Y = 1755.32` (outer/west face meets the soundboard further south)
     - Earlier mistake: using the same threshold for both faces was wrong ("why are you starting the angle into the base at the same heights for both the inside and outside?"). Per-face is correct.
   - Helper functions: `column_outer_x(y)`, `column_inner_x(y)`. Use these in every downstream view instead of the old `COLUMN_OUTER_X` / `COLUMN_INNER_X` literals (the literals are kept as the un-bent reference, but rendering the column must go through the helpers).
3. **FLOOR_Y raised 1915.5 → 1860.0**, `S_BASS_CLEAR_BASE = -66.14` (recompute as `(FLOOR_Y - CO.y) / u[1]` if FLOOR_Y changes again). No foot pedals means the base only needs ~56 mm of footprint, not the concert-harp 112 mm.
4. **`Y_TOP_OF_BASE_BASE = 1699.49`** (previously implicitly `CO[1] = 1803.91`). Matches the top of the column-soundboard intersection ellipse so the bent section is entirely above the base.
5. **Elliptical soundboard hole parameterized**: `SOUNDBOARD_COLUMN_HOLE_MINOR = 39.0`, `SOUNDBOARD_COLUMN_HOLE_MAJOR = 73.60` (= 39 / sin 32°), `SOUNDBOARD_COLUMN_HOLE_Y = 1727.40`. The hole is an ellipse because the cylindrical column pierces the sloped soundboard at ~32°. Not yet *rendered* as a cutout in `build_views.py`; parameterized only.
6. **NB anchor moved**: `NB = (31.746, 358.34)` (was `(12.700, 323.844)`). It now sits on the column arc at the intersection of the D1→C1 sharp-buffer tangent and the column's outer face. `build_harp.NB.y` is set to `358.34` directly; the x is `column_outer_x(358.34)`.
7. **`R_BUFFER = 8` (was 12)**. Molded CF holes get a smaller allowance than drilled plywood. Buffer count now **42 flat + 47 nat + 44 sharp = 133 feasible** grommet holes. `SKIPPED_BUFFERS` list adjusted accordingly.
8. **Canonical neck is now `erand47jc_v3_opt.svg`** (supersedes `erand47jc_v2_opt.svg`):
   - `optimize_v2.py` now derives all Inkscape-frame anchors (NBI/NBO/NTO) from `column_outer_x` / `column_inner_x` instead of hardcoded literals.
   - `w5_in` restored from 80 → **15** (the HANDOFF-documented value). The 80 value was a regression that caused a G7sbi→ST overshoot loop.
   - After running the optimizer, the **user hand-edited** the output: deleted nodes n1 (NBI) and n2, moved n0 (NBO) down to y=358.34, patched the closing cubic with arc-matching control points. **Do not re-run the optimizer without refactoring the topology first** — see Open Questions.
   - `build_views.py` now reads `erand47jc_v3_opt.svg` (via `NECK_SRC = 'erand47jc_v3_opt.svg'`). `NECK_CLOSING_CUBIC` uses `NT_BENT` to account for the column bend.
   - 0 buffer penetrations on the v3 hand-edited path (checked against dense sampling of every buffer).
9. **Vendor-package scaffolding** for the CF manufacturing partner:
   - `VENDOR_MEMO.md` — cover page for the design package.
   - `force_schedule.csv` — per-string tension/force table.
   - `hole_schedule.csv` — per-string hole diameters (tuner Ø16, clicky Ø6.5) and plate assignment (+z/−z by parity).
   - `generate_schedules.py` — regenerates the two CSVs from `strings.py` + `build_harp.py`.
   - `shoulder_sketch.py` + `shoulder_sketch.svg` — dedicated shoulder-region sketch with the hidden joint called out.
   - `build_step.py` — **WIP** STEP export of the two neck plates (`plate_pz.step`, `plate_mz.step`) via cadquery. Produces files but not yet fully reviewed; shoulder/chamber/base STEP exports not started.
10. **Android tablet app refreshed** (after the commit): regenerated view SVGs + the new `erand47jc_v3_opt.svg` copied into `erandapp/app/src/main/assets/`, old `erand47jc_v2_opt.svg` removed. Rebuilt + reinstalled on tablet `P90YPDU16Y251200164` via `./gradlew installDebug` (8 s build). User confirmed "looks fine."

**Still pending (do not claim these are done):**
- **Chamber-volume increase** — in-progress investigation. Three options on the table: (a) lower `Y_TOP_OF_BASE`, (b) angle the base top perpendicular to the soundboard at the inner-column/soundboard intersection, (c) enlarge limaçon `D_PEAK`. User proposed a fourth: replace the two horizontal top-of-base segments with concave **scoops** curving down into the base region (tangent-matched to the soundboard normal at the endpoints, preserving the tongue-and-groove lip). Not yet parameterized or rendered.
- **Rotary-prong clicker** — explicitly **not integrated**. Clicky pens stay as-is for now. Treble-collision problem at F7/G7 (nat/sharp holes closer than Ø6.5) is unresolved.
- **STEP export** — only neck plates drafted. Need shoulder, chamber, base exports.
- **`optimize_v2.py` topology refactor** — next re-run will *recreate* NBI/n1/n2 and clobber the user's hand-edit. Before running the optimizer again, remove those nodes from the topology so v3 is regeneratable.
- **Elliptical soundboard-hole cutout** — parameterized but not rendered in `build_views.py`.
- **`COLUMN_TOP_SLOT_*` params** — the two neck plates slot into the top of the column; slot dimensions still not parameterized. `interfaces.md §2` should describe the slot.
- **`construction.md` Steps 2, 5, 6, 7** — partially updated in this pass; a consistency sweep is still owed.

---

**Pass 2026-04-21 after latest — Android native app (verified working)**

Three parallel agents built a minimal Android app mirroring `HarpHymnal/jazzhymnal`'s structure, plus two follow-up fixes after the initial build failed on WebView quirks:

- **`erandapp/`** (new directory) — gradle 8.2.1 Android project, `com.harp.erandapp`, minSdk 24, targetSdk 34.
- **WebView wrapper**: `MainActivity` uses `androidx.webkit.WebViewAssetLoader` to serve bundled assets over a virtual `https://appassets.androidplatform.net/assets/` origin so `fetch()` works same-origin. Plain `file:///android_asset/` URLs cause fetch to fail by browser policy — the asset loader is the fix. Fully offline; the origin is synthetic, no server runs.
- **Dependency**: `implementation 'androidx.webkit:webkit:1.9.0'` in `app/build.gradle`.
- **Orientation**: `android:screenOrientation="landscape"` in `AndroidManifest.xml`. The viewer's CSS media query at ≤1300 px collapses to a 2-column mobile layout that conflicts with `.tall` panels spanning 2 rows. At the tablet's 1920 × 1200 landscape size, the 5-column desktop grid renders cleanly with all seven panels (side, top, clicky, tuner, front, rear, sbf) visible.
- **Asset sync**: `app/build.gradle` has a `syncErandAssets` Copy task that pulls `index.html`, `svg-pan-zoom.min.js`, all `erand47_*.svg`, and `pedal/*.svg` from the repo root into `app/src/main/assets/` at every build. Single source of truth; `assets/` is gitignored.
- **Local `svg-pan-zoom.min.js`** (new in repo root) — downloaded from jsdelivr once, replaces the old CDN `<script>` tag in `index.html`. Desktop `python3 -m http.server 8001` and Android app both use the same local file.
- **Launcher icons** — generated from `icon-src.svg` (harp silhouette on bronze). 5 densities + adaptive icon xml.
- **Build**: `cd erandapp && ./gradlew assembleDebug` → `app/build/outputs/apk/debug/app-debug.apk` (~210 KB).
- **Install**: `~/Android/Sdk/platform-tools/adb install -r erandapp/app/build/outputs/apk/debug/app-debug.apk` (verified working on tablet P90YPDU16Y251200164, all seven panels render correctly).
- **Launch**: `adb shell am start -n com.harp.erandapp/.MainActivity`.

---

**Pass 2026-04-21 latest — loose-ends cleanup + dual-clicky design + regression tests**

Four parallel agents landed:

1. **`build_harp.py` now imports `strings.py`** — the three 47-entry tables (`_RAW_GEOM`, `_NOTE_SEQUENCE`, `_STRING_WIDTHS`) are now list-comprehensions over `STRINGS`. No more duplication. String count is no longer hardcoded — editing `strings.py` changes the harp.
2. **`build_harp.py` NB parameterized**: `NB.y = _c1_sharp_y() + R_BUFFER` derived at runtime. Change `R_BUFFER` from 12 → 18 and NB shifts automatically. Added `COLUMN_OUTER_X = 12.700` and `COLUMN_INNER_X = 51.700` named constants (CO, CI, NT, NB all reference them).
3. **`optimize_v2.py` Inkscape-frame anchors derived** from `bh.NB`, `g.ST`, `bulge_tip_point(S_TREBLE_CLEAR)`, `bh.NT` via `inkscape_frame.to_inkscape()`. Local `U` literal replaced with `g.u`. Max drift from hardcoded values: 0.06 mm (BT.y — well inside buffer tolerance).
4. **`build_views.py` per-string tables dedup'd** (Agent B's earlier run): `PIN_XY`, `PIN_NOTES`, `GROMMET_Y`, `STRING_DIAMETERS` all derive from `STRINGS`. 41 lines removed. Byte-identical SVG output.
5. **`build_views.py` v2 closing-cubic parameterized**: column-top cap reads the closing cubic's control points from `erand47jc_v2_opt.svg` at runtime via a new 54-line `_extract_cubics()` parser + `_find_closing_cubic()` finder. 5.7e-14 mm drift (floating-point noise). Graceful fallback if file missing.
6. **Dual clicky pen design** — `pedal/dual_clicky.svg` (new, 23.5 KB). Shared 48×14 mm flange with 4× M2.5 screw ears. Two pushers 16 mm apart at top converge via taper to **3.4 mm shaft spacing** at paddle tips (= G7 nat→sharp distance). Drilled hole strategy: one shared oblong slot Ø 6.5 × 10 mm. Fits within 17 mm treble string pitch. Proposed solution for the treble-clicky collision problem.
7. **Regression test script** — `test_harp_regression.py` (12 KB, 9 checks, stdlib only). `python3 test_harp_regression.py` → `OK: 9 checks passed`. Covers strings config, build_harp integrity, buffer positions (incl B4 spot check), soundbox scalars, inkscape_frame roundtrip, v2 neck path presence, view regeneration, 141-buffer count in erand47.svg, and nat-buffer feasibility.

Minor note for home-laptop Claude: `soundbox.geometry.L_CO_ST` is 1558.852815 (not 1558.858 as mentioned in some older comments — a 0.005 mm discrepancy). Regression test uses a ±0.01 tolerance.

---

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

**No foot-pedal mechanism.** Pitch change is by **per-string clicky-pen assemblies** embedded in the two-CF neck plates. **Clicky pens are the current design** — the rotary-prong clicker was *identified* as a candidate for the F7/G7 treble collision (nat/sharp only ~3.4 mm apart vs. 6.5 mm hole) but is **not integrated**. Revisit after the vendor package is out.

The buffer circles (R = 8 mm as of 2026-04-23, was 12) in `build_harp.py` = guitar tuner pin centers (flat_buffer) + natural clicky centers (nat_buffer) + sharp clicky centers (sharp_buffer). Each buffer represents the CF material allowance around a molded hole. `SKIPPED_BUFFERS` trims the full 3×47=141 down to the feasible set of 133 (42 flat + 47 nat + 44 sharp). Clicky design detail lives in `pedal/` (`integration.md`, `paddle.svg`, `packing.svg`, `clicky_side.svg`, `dual_clicky.svg`).

## Current canonical neck: `erand47jc_v3_opt.svg`

Supersedes v2 as of 2026-04-23. The v3 path was produced by running `optimize_v2.py` with column-derived anchors + `w5_in=15`, then **hand-edited** by the user: deleted nodes n1 (NBI) and n2, moved n0 (NBO) down to y=358.34 on the column arc, and patched the closing cubic with arc-matching control points. 0 buffer penetrations on the current outline.

**Do not re-run the optimizer without first refactoring `optimize_v2.py` to remove n1 and n2 from the topology.** Re-running today would clobber the hand-edit. See Open Questions.

`build_views.py` reads `erand47jc_v3_opt.svg` via `NECK_SRC`. The closing cubic uses `NT_BENT` (bent column position at NT) rather than `g.NT`.

### Prior canonical: `erand47jc_v2_opt.svg` (legacy)

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

## Remaining cleanup (mostly done; see latest TL;DR)

**Completed in the latest pass:**
- `build_harp.py` now imports `strings.py` ✓
- `build_views.py` dedup'd against `strings.py` ✓
- `optimize_v2.py` anchors derived from `bh`/`g` constants ✓
- `NB.y` parameterized against `R_BUFFER` ✓
- v2 closing cubic parameterized from SVG ✓
- Regression tests added ✓
- Dual-clicky assembly designed (`pedal/dual_clicky.svg`) as the treble-collision solution ✓

**Still hardcoded (future pass):**

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
- **Neck outline (canonical):** `erand47jc_v3_opt.svg` — optimizer output + user hand-edits (n1/n2 deleted, NBO at y=358.34). This is what `build_views.py` reads.
- **Neck outline (legacy):** `erand47jc_v2_opt.svg`, `erand47jc_v2.svg`, `erand47jc_opt.svg`, `erand47jc.svg` — kept for reference only.
- **Optimizer:** `optimize_v2.py` — anchors derived from `column_outer_x/inner_x`, `w5_in=15`. **Not safe to re-run without topology refactor** (would recreate n1/n2).
- **View builder:** `build_views.py` + `index.html` + `svg-pan-zoom.min.js`.
- **Inner bound (geodesic):** `neck_geodesic.py`. Emits pink polyline into `erand47.svg`; terminates at G7sb/G7fb east poles with a connector line; brown Bezier wraps externally.
- **Soundbox source-of-truth:** `soundbox/geometry.py` (parameterized). **Do NOT edit `CO`, `CI`, `ST`, `NT`, `NB`, `FLOOR_Y`, `Y_TOP_OF_BASE`, `SOUNDBOARD_DIR`, column bend params, joint params without a joint conversation per `soundbox/interfaces.md` §§1–3** — the `_BASE` constants in `DESIGN PARAMETERS` are the edit surface.
- **Soundbox interface spec:** `soundbox/interfaces.md` §1 shoulder-chamber joint, §2 column (round, bent, per-face thresholds), §3 base-chamber joint.
- **Soundbox construction:** `soundbox/construction.md` — build order for chamber, shoulder, base, column. Needs consistency sweep on Steps 2/5/6/7.
- **Pedal/clicky design:** `pedal/integration.md`, `pedal/clicky_side.svg`, `pedal/dual_clicky.svg`, `pedal/tuner_side.svg`.
- **Vendor package (2026-04-23):** `VENDOR_MEMO.md`, `force_schedule.csv`, `hole_schedule.csv`, `generate_schedules.py`, `shoulder_sketch.{py,svg}`, `build_step.py` (WIP STEP export of neck plates).
- **Android app:** `erandapp/` (gradle project). `./gradlew installDebug` with tablet connected = rebuild + push. Assets auto-synced from repo root by `syncErandAssets` task.
- **Review file:** `erand47_review.svg` — scratch copy for user's Inkscape hand-edits. **Do not overwrite without asking** (caused a blowup earlier this session).

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

## Open questions (as of 2026-04-23)

1. **Chamber-volume increase** — active investigation. User's latest idea: replace the two horizontal top-of-base segments with concave **scoops** curving down into the base (tangent-matched to the soundboard normal at the endpoints, preserving the tongue-and-groove lip on the outside). Deepest-scoop constraint: minimum base-wall thickness (≥ 6–8 mm CF between scoop floor and `FLOOR_Y`). Not yet parameterized. Other options on the table: lower `Y_TOP_OF_BASE`; angle the base top perpendicular to the soundboard; enlarge limaçon `D_PEAK`.
2. **Elliptical soundboard-hole cutout** — `SOUNDBOARD_COLUMN_HOLE_*` params exist but `build_views.py` doesn't render the ellipse as a cutout yet. Add before STEP export of the chamber.
3. **`optimize_v2.py` topology refactor** — must remove n1 (NBI) and n2 from the topology before the optimizer can be re-run without clobbering the v3 hand-edit. Anchors from the user's edit: NBO at (12.70, 358.34) authoring, no NBI, outline goes NBO → arc-matching CPs → first interior node.
4. **`COLUMN_TOP_SLOT_*` parameters** — the two neck plates slot into the top of the column at NT. Slot dimensions (length, width, depth, orientation w.r.t. bend) still not parameterized. `interfaces.md §2` should describe the slot.
5. **Rotary-prong clicker** — on hold. Clicky pens stay for now. Treble-collision (F7/G7 sharp skipped) remains the compromise.
6. **STEP export (`build_step.py`)** — neck plates drafted; shoulder/chamber/base not started. Review the plate STEPs in CAD before sending to vendor.
7. **`construction.md` consistency sweep** — Steps 2, 5, 6, 7 need alignment with the one-tube chamber / internal-base-plug / bent-round-column model.
8. **`SKIPPED_BUFFERS` list** — review after any mechanism change (rotary clicker, buffer radius change, plate-parity flip).
9. **Flush-mount of the chamber vs. F7sb** — F7 sharp was skipped so the ST→BT line at y=481.939 doesn't penetrate it. If buffer radius changes, re-check which strings to skip.
10. **Android app ↔ repo sync** — `syncErandAssets` gradle task copies assets on every build. If you edit assets *in* `erandapp/app/src/main/assets/`, the next build overwrites your edit. Always edit at repo root.
