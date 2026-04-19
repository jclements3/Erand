# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Contents

This directory is an asset-only drop; there is no code, build system, or test suite.

- `erand.dxf` — AutoCAD 2000-format DXF (AC1015). Roughly 48 x 68 drawing units, consisting primarily of LINE entities (~236) with a handful of TEXT labels (~18). No blocks, hatches, or splines of significance.
- `erard-big.jpg` — High-resolution grayscale scan (10380 x 14740 px at 1200 DPI, ~15 MB). Likely the source reference for the DXF.

Note the filename inconsistency: the directory and DXF use `erand`, the JPEG uses `erard`. "Erard" is a historical French harp/piano maker, which aligns with the `harp/` sibling project in the parent workspace — treat this as harp-related reference material unless told otherwise.

## Working here

There are no commands to run. Typical tasks are inspection and conversion:

- DXF inspection: parse with `ezdxf` (Python) or any DXF viewer; the workspace has no preinstalled tooling for this.
- Image inspection: use `file`, `identify` (ImageMagick), or read directly.

If asked to extract geometry, generate derived files, or render the DXF, create outputs alongside these files and confirm placement with the user first — this directory has historically held only the two source assets.
