# Clements 47 — handoff notes (2026-04-21)

Read this file and `NECK_STATUS.md` before touching anything. Supersedes anything in NECK_STATUS that contradicts it.

## Big design change: no foot pedals

**The Clements 47 has no foot-pedal mechanism.** Pitch change is by **per-string clicky-pen assemblies** embedded in the two-plywood neck — one clicky per flat buffer (= natural) and one per sharp buffer, 94 total.

- The naming `flat_buffer` / `sharp_buffer` in `build_harp.py` and `soundbox/geometry.py` is historical. Those points are now **clicky engagement points**, not pedal engagement points. Don't rename yet — just understand they describe a different mechanism.
- Design work for the clicky + paddle lives in `pedal/`:
  - `pedal/paddle.svg` — 1:1 single-paddle engagement sketch (B4 sharp example).
  - `pedal/packing.svg` — top-view layout study, treble end (strings 38–47).
  - `pedal/integration.md` — mounting, stroke, sizing, open questions.
- Proposed layout: **flat paddles on north plywood, sharp paddles on south** — auto-distributes 94 clickies to ~47 per plywood face without odd/even stagger.

## Current canonical neck: `erand47jc_v2_opt.svg`

10-node Bezier path, optimizer-tuned by `optimize_v2.py`, fully buffer-feasible (zero penetration).

| Node | Authoring coord | Constraint |
|---|---|---|
| n0 NBO | (12.70, 323.84) | Locked. Horizontal out. |
| n1 NBI | (51.70, 323.84) | Locked. Horizontal in from NBO. |
| n2 D1sbi | on D1-sharp circle | Slide-on-circle (1 DoF). Cusp, handles on outside side of circle. |
| n3 E5s | on E5-sharp circle | Slide-on-circle. Collinear handles along tangent. |
| n4 G7sbi | on G7-sharp circle | Slide-on-circle. Collinear handles. |
| n5 ST | (838.78, 494.27) | Locked. In along +u (soundboard slope). Out horizontal. |
| n6 BT | (902.84, 494.27) | Locked. In horizontal. Out along +u. |
| n7 G7fbi | on G7-flat circle | Slide-on-circle. Collinear + symmetric handles. |
| n8 | free 2D | Collinear handles (smooth). |
| n9 NTO | (12.70, 146.56) | Locked. Closing leg 3 back to NBO. |

The sole straight segment is **ST→BT** (seg 5, horizontal line at y=494.27).

Area excess vs the pink geodesic: 13,100 mm² after optimization.

Buffer feasibility: all 94 circles respected. D1 sharp and E5 sharp are exactly tangent (12.000 mm). No graze deeper than rounding noise.

## Viewer (browser-based)

Serve the project folder from port 8001:

```
python3 -m http.server 8001
```

Open `http://localhost:8001/`. Shows 5 views side-by-side at full viewport height:
- Side (xy), Top (rotated −90°, bass-down/treble-up), Front (yz), Rear (yz mirrored), Soundboard-face (u,z).

`build_views.py` generates `erand47_{side,top,front,rear,sbf}.svg` + a combined `erand47_views.svg`. Re-run with `python3 build_views.py` after any neck-geometry change.

## Frames-of-reference gotcha

The **Inkscape frame → authoring frame** offset changed during v2:
- Before v2: `(DX, DY) = (+51.9, +121.64)`
- **After v2: `(DX, DY) = (+51.9, +81.27)`**

The user shifted everything +40.37 mm in Inkscape y when adjusting the v2 viewBox, but authoring coordinates are unchanged. `build_views.py` and `optimize_v2.py` use `DY = 81.27`. The old `/tmp/check_v2.py` and `debug_jc_cross.py` may still have 121.64 hard-coded — their *distance* math is frame-invariant (so feasibility checks still work), but their *printed authoring labels* will be 40 mm off in y. Update or re-derive before trusting those labels.

## Files that matter

- **Neck outline:** `erand47jc_v2_opt.svg` (canonical). Previous: `erand47jc_v2.svg` (user-edited baseline before optimizer).
- **Optimizer:** `optimize_v2.py`.
- **View builder:** `build_views.py`, `index.html`.
- **Buffer check:** `/tmp/check_v2.py` or `debug_jc_cross.py` (caveats above).
- **Pedal design:** `pedal/`.
- **Geometry source-of-truth (soundbox side):** `soundbox/geometry.py`. **DO NOT** change `CO`, `CI`, `ST`, `NT`, `NB`, `FLOOR_Y`, or `SOUNDBOARD_DIR` without a joint conversation per `soundbox/interfaces.md` §3.
- **Legacy v1 optimizer** (`optimize_jc.py`) and **legacy neck** (`erand47jc_opt.svg`, 8-node): kept in the tree for reference, **not** the current design.

## Open questions left by the pedal sub-agent

See `pedal/integration.md` §"Open questions". Summary:
1. Are these clickies **replacing** the user's foot action entirely (no foot pedals anywhere), or are they a per-string pre-set system driven by some other mechanism? Confirmed by the user on 2026-04-21: **no pedals at all**.
2. Does the **north-flat / south-sharp** auto-distribution hold for all 47 strings, or just the ones the agent sampled (B4)?
3. Paddle material and actuator force budget.
4. Clicky body diameter below 12 mm — 3D-printable at that scale?
5. Electrical (sensors, interlocks) — yes/no?
