# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

Design files for a 47-string Erard-style harp (Clements 47). The source reference is the 1901 Paris Erard drawing via Joseph Jourdain's 2019 analysis (see `ERAND.md` for specs). The repo extracts geometry from `erand.dxf`, builds a data-driven SVG of the harp, fits a smooth neck outline through buffer obstacles, and hands geometry to a sibling soundbox design package.

There is no build system, no test suite, and no package manifest. Scripts are run directly with `python3`.

Dependencies used across the scripts (install ad hoc as needed): `ezdxf`, `numpy`, `scipy`, `Pillow`, `opencv-python`.

## The rebuild pipeline

The canonical harp SVG is `erand47.svg`, produced by two steps in order:

```bash
python3 build_harp.py    # emits erand47.svg: strings, buffers, anchors, scalloped neck
python3 leg2_bezier.py   # overwrites the neck with the Bezier fit (current default)
```

Fallback and exploratory alternatives:

- `python3 neck_geodesic.py` — safe scalloped outline (tangent lines + arcs, feasible by construction). Use if the Bezier pipeline breaks.
- `python3 sweep.py` — emits `erand47_*_e*.svg` variants across Schneider max-error tiers (fast/smooth vs slow/tight-hug).
- `python3 decimate.py` — greedy anchor-removal racing-line variant, emits `erand47_dec_n*.svg` snapshots.

PNGs/JPGs are gitignored; regenerate locally.

## Architecture

### Single sources of truth

- **`build_harp.py`** — data-driven SVG emitter. All CONFIG for strings, buffers, pedal discs, anchor points, and handle constraints lives here. If something about the harp looks wrong, read the CONFIG and comments here before editing anything downstream. Reference points `CO`, `CI`, `NB`, `NT`, `ST`, `FLOOR_Y` and `R_BUFFER` are defined here and imported by the neck-fitting scripts.
- **`soundbox/geometry.py`** — authoritative for shared 3D geometry (same reference points in mm, plus the limaçon taper and clipping planes). The neck code may not mutate any of these points; see `soundbox/interfaces.md` §3.

### Neck-fitting stack

`neck_geodesic.py` → `leg2_bezier.py` → (optional) `decimate.py` / `sweep.py`. Each imports `build_harp` as `bh` so the reference points stay in one place.

The neck outline is three legs:
- **Leg 1** NB → ST, south side of sharp buffers
- **Leg 2** ST → NT, north side of flat buffers
- **Leg 3** NT → NB, straight line down the column

`leg2_bezier.py` names are slightly misleading: it refits **both** Beziered legs from the geodesic polyline using Schneider's algorithm (`bezierfit.py`), with a fixed hand-constructed ST→G7fb11 segment whose handle lengths (`L_st = 80 mm`, `L_g7 = 40 mm`) are user-approved — see `NECK_STATUS.md` before retuning them.

### Historical dead ends (don't revive)

`fitneck5.py` through `fitneck8.py` are failed constrained-optimization attempts preserved for context. Root causes are documented in `NECK_STATUS.md` §"Failed attempts". The current Schneider-fit approach in `leg2_bezier.py` sidesteps them.

`fitneck.py`, `optimize_neck.py`, `optimize_smooth.py`, `optimize_c2.py`, `compare_neck.py`, and `harp_profile*.py` are earlier exploratory work against the DXF/photo; they are not part of the current SVG pipeline.

## Conventions

- **Units**: millimeters in the SVG/soundbox pipeline. `points.md` and `points.csv` record the raw DXF extraction in **inches** — don't mix frames.
- **Coordinate system**: `(x, y)` with `y` increasing downward (SVG convention). Soundbox adds a `z` perpendicular to the string plane.
- **String numbering**: bass-to-treble in scientific pitch notation (C1=1, …, G7=47). C and F strings are drawn thicker.
- **Spelling**: the directory, DXF, and generated SVGs use `erand`; the original scan was labeled `erard` (the historical French maker). Both refer to the same instrument.
- **SKIPPED_BUFFERS** in `build_harp.py` is `{(string_num, "flat"|"sharp"), …}`. Requests like "remove a2fb" translate to `(13, "flat")` (A2 is string #13).

## Before touching shared geometry

The soundbox package under `soundbox/` is a handoff interface, not an internal dependency. Changes to `CO`, `CI`, `ST`, `NT`, `NB`, floor plane, or the limaçon taper require a joint conversation per `soundbox/interfaces.md` §3 — they cascade into the mold DXFs under `soundbox/mold/`. Read `NECK_STATUS.md` and `soundbox/interfaces.md` before proposing edits in this region.

## Orientation docs (read these first for context)

- `ERAND.md` — harp specifications (ranges, string diameters, tensions) from the 1901 drawing.
- `NECK_STATUS.md` — current neck-design state, locked constraints, open threads (BT point), failed attempts.
- `soundbox/README.md` and `soundbox/interfaces.md` — what the neck side owns vs. what the soundbox owns.
- `points.md` — the DXF extraction table (per-string landmarks in inches).
