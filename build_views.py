"""build_views.py — generate erand47_views.svg with the four canonical
orthogonal projections of the full harp assembly.

Views (per soundbox/views_summary.md):
  A. Side view  — xy plane (project along z). Full 58° soundboard, chamber
                  silhouette, column, base block, floor.
  B. Top view   — xz plane (project along y). Chamber footprint pear,
                  column square, soundboard axis through the middle.
  C. Front view — yz plane (project along x). Chamber silhouette (tall
                  teardrop), column strip, base block.
  D. SBF view   — (u, z) plane, face-on to the tilted soundboard. Chamber
                  pear with grommet line on the centerline.

All geometry imported from soundbox/geometry.py (single source of truth).

Layout: 2×2 grid. Labels above each view. Axes/reference lines dashed.
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from soundbox import geometry as g

OUTPUT = os.path.join(HERE, "erand47_views.svg")
NECK_SRC = os.path.join(HERE, "erand47jc_v3_opt.svg")

# Inkscape frame -> authoring frame (erand47jc_opt.svg stores the neck curve
# translated by -(DX, DY); we add them back). Single source of truth lives in
# inkscape_frame.py so optimize_v2.py and this file stay in lockstep.
from inkscape_frame import INKSCAPE_DX, INKSCAPE_DY

# Neck physical build: two identical 6 mm plywood sides, 1/2" apart.
# Strings + pins live in the gap; the column is notched to accept both sides.
NECK_PLY_THICKNESS = 6.0        # mm
NECK_GAP           = 12.7       # mm (1/2")
NECK_Z_INNER       = NECK_GAP / 2.0                             # 6.35 mm
NECK_Z_OUTER       = NECK_Z_INNER + NECK_PLY_THICKNESS          # 12.35 mm

# Guitar-style tuner geometry, matched to Thingiverse 6099101 (noamtsvi,
# CC-BY-NC) — see pedal/reference/ for the STL sources. The tuner "case"
# mounts on the outer plywood face; the gear post passes through the
# plywood into the string gap; the worm driver sticks out as the knob.
TUNER_BODY_W     = 12.6        # case width, across the neck axis (into ±z)
TUNER_BODY_H     = 39.2        # case length along the string direction
TUNER_BODY_D     = 19.4        # case depth outward from plywood face (±z)
TUNER_KNOB_DIA   = 19.3        # worm-driver diameter (visible as the knob)
TUNER_KNOB_OUT   = 24.0        # worm-driver half-length protruding outward
GEAR_POST_DIA    = 15.4        # gear post (what the string wraps around)

# Alternation convention: odd string numbers (1=C1, 3=E1, ...) go on +z side
# (right plywood); even numbers (2=D1, 4=F1, ...) on -z side (left plywood).
# Per-string data (pin position, note name, grommet y, diameter) comes from
# strings.STRINGS -- the single source of truth. Do not hardcode duplicates
# here.
from strings import STRINGS
PIN_XY           = [(s.pin_x, s.pin_y) for s in STRINGS]
PIN_NOTES        = [s.note for s in STRINGS]
GROMMET_Y        = [s.grommet_y for s in STRINGS]
STRING_DIAMETERS = [s.diameter for s in STRINGS]
assert len(PIN_XY) == len(STRINGS)

FILL_TUNER_ODD  = "#d46a3a"    # orange, +z side (right plywood)
FILL_TUNER_EVEN = "#3a6fd4"    # blue,   -z side (left plywood)
STRING_COLOR_C = "#c00000"    # C strings red (matches build_harp)
STRING_COLOR_F = "#1060d0"    # F strings blue
STRING_COLOR_G = "#888"       # all other strings gray

def _string_stroke(note):
    c = note[0]
    if c == "C": return STRING_COLOR_C
    if c == "F": return STRING_COLOR_F
    return STRING_COLOR_G
OUTPUT_SIDE  = os.path.join(HERE, "erand47_side.svg")
OUTPUT_TOP   = os.path.join(HERE, "erand47_top.svg")
OUTPUT_FRONT = os.path.join(HERE, "erand47_front.svg")
OUTPUT_REAR  = os.path.join(HERE, "erand47_rear.svg")
OUTPUT_SBF   = os.path.join(HERE, "erand47_sbf.svg")

# ----- Style -----
STROKE_OUTLINE = "#222"            # chamber / column outline
STROKE_BASE    = "#6b4a2a"         # base block
STROKE_SOUND   = "#2e8b57"         # soundboard face / grommet line
STROKE_AXIS    = "#888"            # reference axes
STROKE_FLOOR   = "#4a7c2e"
FILL_CHAMBER   = "#e4d4b5"
FILL_COLUMN    = "#d4c59c"
FILL_BASE      = "#b89868"
FILL_NECK      = "#c79568"
STROKE_NECK    = "#8b4513"
# Scoop / acoustic features
FILL_SCOOP     = "#c4a06a"         # scoop pit (darker than base, lighter than outline)
STROKE_SCOOP   = "#3a2a14"         # scoop boundary
STROKE_SCOOP_AXIS = "#b8862b"      # dashed scoop axis toward hole centroid
FILL_HOLE      = "#1c1c1c"         # sound-hole through-cut
STROKE_HOLE    = "#000"
FILL_DIFFUSER  = "#c7e4f0"         # light blue-gray for the shoulder-underside
                                   # spherical diffuser pocket overlay

SW_HEAVY  = 3.0
SW_LIGHT  = 1.2
SW_AXIS   = 0.5
DASH_AXIS = "6 4"


# ----- Geometry sampling -----
def sample_chamber_outline(n_samples=400):
    """Return lists:
       grommet_line[i]  = (x, y) at flat face   = centerline_point(sp_i)
       bulge_tip[i]     = (x, y, z) at bulge tip in 3D (z=0 here)
       max_z[i]         = D_of(sp_i)/2          = half perpendicular width
       sp_values[i]     = sp_i                  = soundboard station
    """
    sp_min = g.S_BASS_CLEAR
    sp_max = g.S_TREBLE_CLEAR
    sps, grommet, tip, maxz = [], [], [], []
    for k in range(n_samples + 1):
        t = k / n_samples
        sp = sp_min + t * (sp_max - sp_min)
        sps.append(sp)
        grommet.append(g.centerline_point(sp))
        tip.append(g.bulge_tip_point(sp))
        maxz.append(g.D_of(sp) / 2)
    return sps, grommet, tip, maxz


def polyline_d(pts):
    """SVG 'd' attribute for a polyline through pts."""
    if not pts:
        return ""
    s = [f"M {pts[0][0]:.3f} {pts[0][1]:.3f}"]
    for p in pts[1:]:
        s.append(f"L {p[0]:.3f} {p[1]:.3f}")
    return " ".join(s)


def polygon_d(pts):
    return polyline_d(pts) + " Z"


def compound_evenodd_d(outer, inner):
    """SVG 'd' attribute for a compound path with one outer contour and one
    inner (hole) contour. Returns "M... Z M... Z". The inner contour is
    emitted in REVERSED order so that even/odd fill rule reads it as a hole
    regardless of the relative winding of `outer` and `inner`."""
    outer_d = polygon_d(outer)
    inner_rev = list(reversed(inner))
    inner_d = polygon_d(inner_rev)
    return outer_d + " " + inner_d


# ----- Neck outline (read from erand47jc_opt.svg) -----
import re as _re

def _load_neck_path():
    if not os.path.exists(NECK_SRC):
        return None, None
    with open(NECK_SRC) as fh:
        text = fh.read()
    m = _re.search(r'<path\s+d="([^"]+)"[^>]*?stroke="#8b4513"', text, _re.S | _re.I)
    if not m:
        m = _re.search(r'<path[^>]*?stroke="#8b4513"[^>]*?d="([^"]+)"', text, _re.S | _re.I)
    if not m:
        return None, None
    d = m.group(1)
    anchors = _anchor_points(d, INKSCAPE_DX, INKSCAPE_DY)
    return d, anchors


def _extract_cubics(d):
    """Return list of cubic Beziers from an SVG 'd' string as 4-tuples of
    absolute (x, y) control points: (P0, P1, P2, P3). P0 is the current
    point before the cubic (previous command's endpoint); P1/P2/P3 are the
    three points written into the cubic command itself. Handles 'C' (absolute)
    and 'c' (relative) commands, with command repetition and implicit
    subsequent L/l after M/m. No transforms applied — points are in the
    frame of the 'd' attribute (Inkscape frame for erand47jc_v3_opt.svg)."""
    toks = _re.findall(r'[MLCZmlczHhVv]|[-+]?\d+\.?\d*(?:[eE][-+]?\d+)?', d)
    cubics = []
    i = 0
    cmd = None
    cx = cy = sx = sy = 0.0
    while i < len(toks):
        t = toks[i]
        if t in 'MLCZmlczHhVv':
            cmd = t; i += 1
            continue
        if cmd == 'M':
            cx = float(toks[i]); cy = float(toks[i+1]); i += 2
            sx, sy = cx, cy
            cmd = 'L'
        elif cmd == 'm':
            cx += float(toks[i]); cy += float(toks[i+1]); i += 2
            sx, sy = cx, cy
            cmd = 'l'
        elif cmd == 'L':
            cx = float(toks[i]); cy = float(toks[i+1]); i += 2
        elif cmd == 'l':
            cx += float(toks[i]); cy += float(toks[i+1]); i += 2
        elif cmd == 'C':
            p0 = (cx, cy)
            p1 = (float(toks[i]),   float(toks[i+1]))
            p2 = (float(toks[i+2]), float(toks[i+3]))
            p3 = (float(toks[i+4]), float(toks[i+5]))
            i += 6
            cx, cy = p3
            cubics.append((p0, p1, p2, p3))
        elif cmd == 'c':
            p0 = (cx, cy)
            p1 = (cx + float(toks[i]),   cy + float(toks[i+1]))
            p2 = (cx + float(toks[i+2]), cy + float(toks[i+3]))
            p3 = (cx + float(toks[i+4]), cy + float(toks[i+5]))
            i += 6
            cx, cy = p3
            cubics.append((p0, p1, p2, p3))
        elif cmd in ('H', 'h'):
            nx = float(toks[i]); i += 1
            cx = nx if cmd == 'H' else cx + nx
        elif cmd in ('V', 'v'):
            ny = float(toks[i]); i += 1
            cy = ny if cmd == 'V' else cy + ny
        elif cmd in ('Z', 'z'):
            cx, cy = sx, sy
        else:
            i += 1
    return cubics


def _anchor_points(d, dx, dy):
    """Extract on-path anchors (M/L/C endpoints) from an SVG 'd' string,
    translated by (dx, dy). Good enough for bounding-box estimation — handles
    (P1, P2 of cubics) are skipped since they can lie far off-curve."""
    toks = _re.findall(r'[MLCZmlczHhVv]|[-+]?\d+\.?\d*(?:[eE][-+]?\d+)?', d)
    pts = []
    i = 0
    cmd = None
    cx = cy = sx = sy = 0.0
    while i < len(toks):
        t = toks[i]
        if t in 'MLCZmlczHhVv':
            cmd = t; i += 1
            continue
        if cmd in ('M', 'L'):
            cx = float(toks[i]); cy = float(toks[i+1]); i += 2
            if cmd == 'M':
                sx, sy = cx, cy
                cmd = 'L'          # subsequent pairs are implicit L
            pts.append((cx + dx, cy + dy))
        elif cmd in ('m', 'l'):
            cx += float(toks[i]); cy += float(toks[i+1]); i += 2
            if cmd == 'm':
                sx, sy = cx, cy
                cmd = 'l'
            pts.append((cx + dx, cy + dy))
        elif cmd == 'C':
            i += 4   # skip P1, P2
            cx = float(toks[i]); cy = float(toks[i+1]); i += 2
            pts.append((cx + dx, cy + dy))
        elif cmd == 'c':
            i += 4
            cx += float(toks[i]); cy += float(toks[i+1]); i += 2
            pts.append((cx + dx, cy + dy))
        elif cmd in ('H', 'h'):
            nx = float(toks[i]); i += 1
            cx = nx if cmd == 'H' else cx + nx
            pts.append((cx + dx, cy + dy))
        elif cmd in ('V', 'v'):
            ny = float(toks[i]); i += 1
            cy = ny if cmd == 'V' else cy + ny
            pts.append((cx + dx, cy + dy))
        elif cmd in ('Z', 'z'):
            cx, cy = sx, sy
        else:
            i += 1    # unrecognized — bail
    return pts


NECK_D, NECK_ANCHORS = _load_neck_path()
if NECK_ANCHORS:
    NECK_XMIN = min(p[0] for p in NECK_ANCHORS)
    NECK_XMAX = max(p[0] for p in NECK_ANCHORS)
    NECK_YMIN = min(p[1] for p in NECK_ANCHORS)
    NECK_YMAX = max(p[1] for p in NECK_ANCHORS)
else:
    # Fallback to the reference points if the file isn't there.
    NECK_XMIN, NECK_XMAX = g.NT[0], 903.173
    NECK_YMIN, NECK_YMAX = g.NT[1], g.ST[1] + 150


# Closing cubic (n8 → NTO) extracted from the neck path. The column top cap
# in the side view follows this cubic so it flows smoothly into the neck.
# Extracted at import time from erand47jc_v3_opt.svg so a re-optimization of
# the neck stays in sync automatically — the previous implementation had the
# four control points hardcoded as Inkscape-frame literals. We identify the
# cubic by its endpoint matching NTO (NT in authoring frame) to within a
# sub-mm tolerance; this is robust against trailing close-path cubics that
# the optimizer may emit alongside the n8→NTO segment.
def _find_closing_cubic(d, dx, dy):
    if d is None:
        return None
    cubics = _extract_cubics(d)
    if not cubics:
        return None
    # v3_opt uses the bent-column NTO position (NT_BENT), not the original
    # straight-column NT. Search for the cubic ending there.
    nto_auth = getattr(g, 'NT_BENT', g.NT)
    nto_ink = (nto_auth[0] - dx, nto_auth[1] - dy)
    tol = 0.1    # mm — matches the path's 3-decimal precision with slack
    for (p0, p1, p2, p3) in cubics:
        if (abs(p3[0] - nto_ink[0]) < tol
                and abs(p3[1] - nto_ink[1]) < tol):
            # Translate Inkscape-frame control points to authoring frame.
            return tuple((p[0] + dx, p[1] + dy) for p in (p0, p1, p2, p3))
    return None


NECK_CLOSING_CUBIC = _find_closing_cubic(NECK_D, INKSCAPE_DX, INKSCAPE_DY)


# ----- Each view -----
def side_view_content():
    """xy plane, x right, y down (SVG native). Return list of SVG elements."""
    parts = []
    sps, grommet, tip, maxz = sample_chamber_outline()

    # Strings. Each string passes through the 12.7 mm gap between the two
    # neck plywood sheets, so from the side view (project along z) the
    # portion inside the neck is HIDDEN behind the near plywood — drawn
    # dashed per standard engineering-drawing convention. The portion
    # south of the neck's south boundary is visible — drawn solid.
    # The neck's south boundary at each string's x is one R_BUFFER south
    # of the string's sharp_buffer center (since sharp_buffer is tangent
    # to the south boundary).
    import build_harp as _bh_strings
    _strings_for_lines = _bh_strings.build_strings()
    R_BUF_NECK = _bh_strings.R_BUFFER
    for idx, ((px, py), gy, dia, note, s_struct) in enumerate(
            zip(PIN_XY, GROMMET_Y, STRING_DIAMETERS, PIN_NOTES,
                _strings_for_lines)):
        fb_x, fb_y = s_struct['flat_buffer']
        sb_y = s_struct['sharp_buffer'][1]
        exit_y = sb_y + R_BUF_NECK  # where string emerges from the neck's south face
        stroke = _string_stroke(note)
        # Hidden segment: tuner → pin → neck south-boundary exit on string.
        parts.append(
            f'<polyline points="{fb_x:.3f},{fb_y:.3f} '
            f'{px:.3f},{py:.3f} {px:.3f},{exit_y:.3f}" '
            f'stroke="{stroke}" stroke-width="{dia:.3f}" '
            f'stroke-linecap="round" fill="none" '
            f'stroke-dasharray="3 2" opacity="0.6"/>')
        # Visible segment: neck exit → grommet.
        parts.append(
            f'<line x1="{px:.3f}" y1="{exit_y:.3f}" '
            f'x2="{px:.3f}" y2="{gy:.3f}" '
            f'stroke="{stroke}" stroke-width="{dia:.3f}" '
            f'stroke-linecap="round"/>')

    # Chamber silhouette: upper bound = grommet_line (flat face),
    # lower bound = bulge_tip (deepest into chamber). Clip at FLOOR_Y:
    # the bulge-tip locus dips below the floor at the bass end, so find
    # sp_floor where bulge_tip_y == FLOOR_Y and truncate there with a
    # horizontal close along y = FLOOR_Y.
    def _find_sp_at_tipy(target_y, lo, hi):
        """Binary search sp in [lo, hi] such that bulge_tip_point(sp)[1] == target_y.
        Assumes bulge_tip_y is monotonic in sp over [lo, hi]."""
        y_lo = g.bulge_tip_point(lo)[1]
        y_hi = g.bulge_tip_point(hi)[1]
        # Direction: if y_lo > target and y_hi < target, y decreases as sp increases.
        for _ in range(60):
            mid = 0.5 * (lo + hi)
            y_mid = g.bulge_tip_point(mid)[1]
            if (y_mid - target_y) * (y_lo - target_y) <= 0:
                hi = mid
            else:
                lo = mid
                y_lo = y_mid
        return 0.5 * (lo + hi)

    sp_floor = _find_sp_at_tipy(g.FLOOR_Y, g.S_BASS_CLEAR, g.S_PEAK)
    tip_floor = g.bulge_tip_point(sp_floor)

    # Build clipped chamber polygon. Two clippings applied:
    #  (a) Bass side: bulge tip dips below FLOOR_Y at bass end — clip to
    #      y <= FLOOR_Y and close with horizontal along FLOOR_Y.
    #  (b) Treble side: neck assembly mounts at y = Y_ST_HORIZ for x > ST.
    #      Per soundbox/interfaces.md §1, everything the neck subtracts is at
    #      y < Y_ST_HORIZ with x past ST — so clip the flat face at sp=L_CO_ST
    #      (which IS the ST point), then cross east horizontally at
    #      y = Y_ST_HORIZ to the bulge tip at S_TREBLE_CLEAR.
    #
    # Walk: flat face [S_BASS_CLEAR..L_CO_ST] → horizontal east to bulge tip at
    # S_TREBLE_CLEAR → bulge tip [S_TREBLE_CLEAR..sp_floor] → horizontal west
    # along FLOOR_Y back to flat face at S_BASS_CLEAR.
    upper = [p for sp, p in zip(sps, grommet) if sp <= g.L_CO_ST]
    # Ensure the last upper point is exactly ST.
    st_flat = g.centerline_point(g.L_CO_ST)   # == (838.784, 481.939) == ST
    upper.append((st_flat[0], st_flat[1]))
    # Horizontal segment at y = Y_ST_HORIZ east to the bulge tip east end.
    tip_treble = g.bulge_tip_point(g.S_TREBLE_CLEAR)
    upper.append((tip_treble[0], g.Y_ST_HORIZ))
    # Bulge tip from S_TREBLE_CLEAR down to sp_floor (reversed to walk west).
    lower_xy = [(p[0], p[1]) for sp, p in zip(sps, tip) if sp >= sp_floor]
    lower_xy.reverse()
    # Ensure the clip point is exactly on y=FLOOR_Y.
    if lower_xy:
        lower_xy[-1] = (tip_floor[0], g.FLOOR_Y)
    # Close with horizontal segment from (tip_floor.x, FLOOR_Y) back to the
    # bass end of the flat face (centerline at S_BASS_CLEAR, y == FLOOR_Y).
    chamber_poly = upper + lower_xy
    parts.append(
        f'<path d="{polygon_d(chamber_poly)}" '
        f'fill="{FILL_CHAMBER}" stroke="{STROKE_OUTLINE}" '
        f'stroke-width="{SW_HEAVY}"/>'
    )

    # Soundboard face line (CI -> ST)
    parts.append(
        f'<line x1="{g.CI[0]:.3f}" y1="{g.CI[1]:.3f}" '
        f'x2="{g.ST[0]:.3f}" y2="{g.ST[1]:.3f}" '
        f'stroke="{STROKE_SOUND}" stroke-width="{SW_HEAVY}"/>'
    )

    # Base block: fills the whole chamber footprint between Y_TOP_OF_BASE
    # and FLOOR_Y, wrapping around the column on both sides.
    #   - West edge follows the flat face (soundboard slope) from CO at
    #     Y_TOP_OF_BASE down to the flat face's floor intersection at
    #     sp=S_BASS_CLEAR (west of the column).
    #   - Bottom edge runs east along FLOOR_Y from the flat-face floor
    #     point to the bulge-tip floor point at sp_floor.
    #   - East edge follows the bulge-tip curve from sp_floor up to
    #     sp_topofbase (where bulge_tip_y == Y_TOP_OF_BASE).
    #   - Top edge runs west along Y_TOP_OF_BASE from the bulge-tip top-
    #     of-base point back to CO. The column (drawn AFTER the base)
    #     notches through.
    base_top_y = g.Y_TOP_OF_BASE
    base_bot_y = g.FLOOR_Y

    sp_topofbase = _find_sp_at_tipy(base_top_y, sp_floor, g.S_PEAK)
    tip_topofbase = g.bulge_tip_point(sp_topofbase)

    flat_floor = g.centerline_point(g.S_BASS_CLEAR)  # flat face at FLOOR_Y

    # Flat face at Y_TOP_OF_BASE (chamber's west wall at the base's top).
    # s' where flat_y == Y_TOP_OF_BASE:
    _sp_flat_topofbase = (g.Y_TOP_OF_BASE - g.CO[1]) / g.u[1]
    flat_topofbase = g.centerline_point(_sp_flat_topofbase)

    # East boundary: bulge-tip curve from sp_floor up to sp_topofbase.
    east_curve = [(p[0], p[1]) for sp, p in zip(sps, tip)
                  if sp_floor <= sp <= sp_topofbase]

    # Base is an INTERIOR plug inside the chamber tube — its outline in side
    # view is bounded by the chamber's interior cross-section at each y:
    # flat face (west) and bulge tip (east), between Y_TOP_OF_BASE and FLOOR_Y.
    base_poly = (
        [(flat_topofbase[0], base_top_y),         # west wall top (on flat face)
         (flat_floor[0], flat_floor[1]),          # flat face at floor
         (tip_floor[0], base_bot_y)]              # bulge tip on floor (east)
        + east_curve                               # east edge up bulge tip
        + [(tip_topofbase[0], base_top_y)]        # top of east edge
    )

    # Carve the parabolic scoop directly into the base polygon's top edge.
    # HW sits ~19 mm ABOVE Y_TOP_OF_BASE (inside the chamber), so only a
    # small triangular region of the scoop silhouette near HW pokes above
    # the base. The rest lives inside base material. Walking CCW around
    # the base, we replace the implicit top-edge segment (tip_topofbase
    # back to flat_topofbase) with a DETOUR: east-top -> west to the
    # chord/Y_TOP_OF_BASE crossing -> along the chord down to RIM_FAR ->
    # along the parabola back through VERTEX up to the parabola/Y_TOP_OF_BASE
    # crossing -> resume west along top edge to west-top. Result is a
    # single concave polygon with a scoop-shaped notch in its top edge.
    if g.SCOOP_ENABLED:
        Y_CUT = g.Y_TOP_OF_BASE
        hw = g.SCOOP_RIM_HW
        rf = g.SCOOP_RIM_FAR
        # Chord crosses Y_CUT at parameter s_chord along RIM_FAR -> HW.
        s_chord = (Y_CUT - rf[1]) / (hw[1] - rf[1])
        chord_cross = (rf[0] + s_chord * (hw[0] - rf[0]), Y_CUT)
        # Chord samples from chord_cross down toward RIM_FAR (exclude the
        # RIM_FAR endpoint; the first parabola sample below is RIM_FAR).
        chord_samples = []
        N_CHORD = 10
        for i in range(1, N_CHORD):
            s = s_chord * (1 - i / N_CHORD)
            chord_samples.append((
                rf[0] + s * (hw[0] - rf[0]),
                rf[1] + s * (hw[1] - rf[1]),
            ))
        # Parabola samples in reverse (RIM_FAR -> HW). Keep those with
        # y >= Y_CUT; interpolate the final crossing exactly at y = Y_CUT.
        para_rev = list(reversed(g.scoop_parabola_xy(80)))
        para_inside = []
        for i, p in enumerate(para_rev):
            if p[1] >= Y_CUT:
                para_inside.append(p)
                continue
            if i > 0:
                prev = para_rev[i - 1]
                frac = (Y_CUT - prev[1]) / (p[1] - prev[1])
                cross_x = prev[0] + frac * (p[0] - prev[0])
                para_inside.append((cross_x, Y_CUT))
            break
        # Stitch the notch into base_poly. base_poly currently ends at
        # tip_topofbase (east-top); the implicit Z closes to flat_topofbase
        # (west-top). Appending chord_cross + chord_samples + para_inside
        # before the close replaces the straight top edge with the notch.
        base_poly = base_poly + [chord_cross] + chord_samples + para_inside

    parts.append(
        f'<path d="{polygon_d(base_poly)}" '
        f'fill="{FILL_BASE}" stroke="{STROKE_BASE}" '
        f'stroke-width="{SW_LIGHT}" opacity="0.6"/>'
    )

    if g.SCOOP_ENABLED:
        # Scoop silhouette as a stroke-only outline over the carved base so
        # the full parabola + chord (including the portion above Y_TOP_OF_BASE
        # near HW) reads as one continuous curve.
        _full_sil = g.scoop_parabola_xy(80) + [g.SCOOP_RIM_HW]
        parts.append(
            f'<path d="{polygon_d(_full_sil)}" '
            f'fill="none" stroke="{STROKE_SCOOP}" '
            f'stroke-width="{SW_LIGHT}" opacity="0.85"/>'
        )
        # Dashed axis: from rim midpoint toward centroid.
        ax_end = g.SCOOP_CENTROID_XY
        parts.append(
            f'<line x1="{g.SCOOP_RIM_MID_XY[0]:.3f}" y1="{g.SCOOP_RIM_MID_XY[1]:.3f}" '
            f'x2="{ax_end[0]:.3f}" y2="{ax_end[1]:.3f}" '
            f'stroke="{STROKE_SCOOP_AXIS}" stroke-width="{SW_LIGHT}" '
            f'stroke-dasharray="{DASH_AXIS}" opacity="0.8"/>'
        )
        # Vertex, focus, HW, rim_far markers + labels.
        for name, pt, dy in [
            ("HW",     g.SCOOP_RIM_HW,  -8),
            ("RIM",    g.SCOOP_RIM_FAR,  14),
            ("VERTEX", g.SCOOP_VERTEX_XY, 14),
            ("FOCUS",  g.SCOOP_FOCUS_XY, -10),
        ]:
            parts.append(
                f'<circle cx="{pt[0]:.3f}" cy="{pt[1]:.3f}" r="3" fill="{STROKE_SCOOP}"/>'
            )
            parts.append(
                f'<text x="{pt[0]+6:.3f}" y="{pt[1]+dy:.3f}" '
                f'font-family="sans-serif" font-size="14" '
                f'fill="{STROKE_SCOOP}">{name}</text>'
            )

    # Sound holes on east bulge wall (bass / mid / treble). Drawn as filled
    # circles centred on bulge_tip_point(s'), with labels and diameter text.
    for h in g.SOUND_HOLES:
        cx, cy = h['center_xy']
        r = h['diameter'] / 2.0
        parts.append(
            f'<circle cx="{cx:.3f}" cy="{cy:.3f}" r="{r:.3f}" '
            f'fill="{FILL_HOLE}" stroke="{STROKE_HOLE}" stroke-width="{SW_LIGHT}" '
            f'fill-opacity="0.55"/>'
        )
        parts.append(
            f'<text x="{cx+r+4:.3f}" y="{cy+5:.3f}" '
            f'font-family="sans-serif" font-size="14" fill="#000">'
            f"{h['label']} Ø{h['diameter']:.0f}</text>"
        )

    # Column: from NT down to the floor. The TOP of the column follows the
    # neck's lower curve (closing cubic n8→NTO) between x=COLUMN_OUTER_X
    # and x=COLUMN_INNER_X so the column flows into the neck instead of
    # meeting it with a flat-top corner.
    #
    # Column centerline is a gentle arc (see geometry.COLUMN_BEND_*): pinned
    # at y_mid = (NT.y + CO.y)/2 with x = (outer+inner)/2, bulging toward
    # -x at both top and bottom. The outer and inner faces follow that arc
    # via column_outer_x(y) / column_inner_x(y). At the cap (top of column)
    # the neck-closing cubic still defines where column meets neck; below
    # the cap the two faces are sampled in 10 mm steps to draw the curve.
    col_bot_y = g.FLOOR_Y
    # Sample the neck's closing-to-NTO cubic at many t, collect points where
    # x sits within the column's outer..inner range AT THE CAP Y-ELEVATION.
    # Because the cap hugs the neck's closing cubic (which sits near y=NT.y),
    # the column-outer/inner bounds there are ~column_outer_x(NT.y). Use the
    # bent outer/inner at the cap for accurate clipping of the cap curve.
    def _bez_cubic(P0, P1, P2, P3, t):
        u = 1 - t
        return (u*u*u*P0[0] + 3*u*u*t*P1[0] + 3*u*t*t*P2[0] + t*t*t*P3[0],
                u*u*u*P0[1] + 3*u*u*t*P1[1] + 3*u*t*t*P2[1] + t*t*t*P3[1])
    # Authoring-frame control points of the n8→NTO cubic, parsed from
    # erand47jc_v3_opt.svg at import time (see NECK_CLOSING_CUBIC above).
    # If the neck file is missing, fall back to a degenerate cap — the cap_pts
    # loop below will then produce a flat-top column.
    cap_y = g.NT[1]
    cap_outer_x = g.column_outer_x(cap_y)
    cap_inner_x = g.column_inner_x(cap_y)
    if NECK_CLOSING_CUBIC is not None:
        _P0, _P1, _P2, _P3 = NECK_CLOSING_CUBIC
    else:
        _P0 = _P1 = _P2 = _P3 = (cap_outer_x, cap_y)
    # Sample at fine resolution, collect (x, y) where x in [cap_outer_x, cap_inner_x].
    cap_pts = []
    for k in range(2001):
        t = k / 2000
        x, y = _bez_cubic(_P0, _P1, _P2, _P3, t)
        if cap_outer_x <= x <= cap_inner_x:
            cap_pts.append((x, y))
    # Order by x descending so the polygon goes inner→outer along the cap.
    cap_pts.sort(key=lambda p: -p[0])
    # Snap exact endpoints so the polygon corners sit on cap_inner_x and NTO.
    if cap_pts:
        # Inner: find y at exactly x=cap_inner_x by linear interp.
        for i in range(len(cap_pts) - 1):
            if (cap_pts[i][0] - cap_inner_x) * (cap_pts[i+1][0] - cap_inner_x) <= 0:
                x0, y0 = cap_pts[i]; x1, y1 = cap_pts[i+1]
                frac = (cap_inner_x - x0) / (x1 - x0) if x1 != x0 else 0
                cap_pts[i] = (cap_inner_x, y0 + frac*(y1-y0))
                cap_pts = cap_pts[i:]
                break
        cap_pts[-1] = (cap_outer_x, cap_y)  # snap NTO endpoint

    # Sample the bent outer and inner faces from the cap y down to the floor
    # at 10 mm steps, so each face reads as a visibly curved banana shape.
    def _sample_column_face(face_fn, y_top, y_bot, step=10.0):
        pts = []
        n_steps = max(2, int(math.ceil((y_bot - y_top) / step)))
        for k in range(n_steps + 1):
            y = y_top + (y_bot - y_top) * k / n_steps
            pts.append((face_fn(y), y))
        return pts

    # Cap-curve top_y defines where the vertical "straight-down" portion
    # of each face begins; fall through to NT.y if cap_pts is empty.
    cap_inner_top_y = cap_pts[0][1] if cap_pts else cap_y
    cap_outer_top_y = cap_pts[-1][1] if cap_pts else cap_y

    inner_face = _sample_column_face(g.column_inner_x, cap_inner_top_y, col_bot_y)
    outer_face = _sample_column_face(g.column_outer_x, cap_outer_top_y, col_bot_y)

    # Column polygon, walking CCW:
    #   (inner face at floor) -> up inner face to cap start
    #   -> cap curve inner→outer
    #   -> (outer face at cap) down outer face to floor
    # inner_face runs top→bottom; reverse so we start at the bottom.
    col_poly = (
        list(reversed(inner_face))                 # bottom-right up to cap (inner face)
        + cap_pts                                  # curved top (inner → outer)
        + outer_face                               # top-left down outer face to floor
    )
    parts.append(
        f'<path d="{polygon_d(col_poly)}" '
        f'fill="{FILL_COLUMN}" stroke="{STROKE_OUTLINE}" '
        f'stroke-width="{SW_LIGHT}"/>'
    )

    # Floor line
    parts.append(
        f'<line x1="-100" y1="{g.FLOOR_Y:.3f}" '
        f'x2="1000" y2="{g.FLOOR_Y:.3f}" '
        f'stroke="{STROKE_FLOOR}" stroke-width="{SW_HEAVY}" '
        f'stroke-dasharray="8 4"/>'
    )

    # BT = east end of the bulge-tip locus at the ST horizontal plane.
    # Binary-search the sp value where bulge_tip.y == ST.y.
    def _find_bt():
        target_y = g.ST[1]
        lo, hi = g.S_PEAK, g.S_TREBLE_FINAL
        for _ in range(60):
            mid = 0.5 * (lo + hi)
            if g.bulge_tip_point(mid)[1] < target_y:
                hi = mid
            else:
                lo = mid
        tip = g.bulge_tip_point(0.5 * (lo + hi))
        return (tip[0], tip[1])
    BT = _find_bt()

    # Treble paraboloid scoop (shoulder underside, BT-anchored, aimed at
    # the treble sound-hole center). Mirrors the base-scoop side-view
    # pattern: a filled silhouette (parabola arc + rim chord), a dashed
    # axis line from rim_mid to the aim point, and four labeled markers
    # (HW_T = BT, RIM_T = rim_far, VERTEX_T, FOCUS_T). Suffix _T keeps
    # these from colliding with any base-scoop labels the bass-side
    # renderer emits.
    if getattr(g, 'TREBLE_SCOOP_ENABLED', False):
        _par_pts = g.treble_scoop_parabola_xy(60)
        # Closed silhouette: parabola arc (BT -> vertex -> rim_far) then
        # rim chord back to BT. Reuse the shared scoop fill/stroke.
        _scoop_poly = _par_pts + [g.TREBLE_SCOOP_HW]
        parts.append(
            f'<path d="{polygon_d(_scoop_poly)}" '
            f'fill="{FILL_SCOOP}" fill-opacity="0.55" '
            f'stroke="{STROKE_SCOOP}" stroke-width="{SW_LIGHT}"/>'
        )
        # Dashed axis line from rim_mid to the aim point (treble hole center).
        _rmx, _rmy = g.TREBLE_SCOOP_RIM_MID
        _aimx, _aimy = g.TREBLE_SCOOP_AIM_XY
        parts.append(
            f'<line x1="{_rmx:.3f}" y1="{_rmy:.3f}" '
            f'x2="{_aimx:.3f}" y2="{_aimy:.3f}" '
            f'stroke="{STROKE_SCOOP}" stroke-width="{SW_AXIS}" '
            f'stroke-dasharray="{DASH_AXIS}"/>'
        )
        # Markers + labels for the four scoop reference points. _T suffix
        # distinguishes from any base-scoop markers (HW/RIM/VERTEX/FOCUS).
        _t_markers = [
            ("HW_T",     g.TREBLE_SCOOP_HW),
            ("RIM_T",    g.TREBLE_SCOOP_RIM_FAR),
            ("VERTEX_T", g.TREBLE_SCOOP_VERTEX_XY),
            ("FOCUS_T",  g.TREBLE_SCOOP_FOCUS_XY),
        ]
        for _name, _pt in _t_markers:
            parts.append(
                f'<circle cx="{_pt[0]:.3f}" cy="{_pt[1]:.3f}" r="2.2" '
                f'fill="{STROKE_SCOOP}"/>')
            parts.append(
                f'<text x="{_pt[0]+5:.3f}" y="{_pt[1]-4:.3f}" '
                f'font-family="sans-serif" font-size="12" '
                f'fill="{STROKE_SCOOP}">{_name}</text>')

    # Reference points (small dots + labels). CO and CI removed — kept
    # internally as soundboard references but not drawn (they no longer
    # correspond visually to where the bent column meets the soundboard).
    for name, pt in [("NT", g.NT),
                     ("NB", g.NB), ("ST", g.ST), ("BT", BT)]:
        parts.append(
            f'<circle cx="{pt[0]:.3f}" cy="{pt[1]:.3f}" r="3" '
            f'fill="#000"/>')
        parts.append(
            f'<text x="{pt[0]+6:.3f}" y="{pt[1]+4:.3f}" '
            f'font-family="sans-serif" font-size="18" fill="#000">{name}</text>')

    # Grommets on soundboard (small marks)
    for name, _, _, (gx, gy) in g.GROMMETS:
        parts.append(
            f'<circle cx="{gx:.3f}" cy="{gy:.3f}" r="2" fill="{STROKE_SOUND}"/>')

    # Shoulder-underside broadband diffuser (concave spherical depression).
    # Rendered as a filled polyline bounded by the rim plane (y = Y_ST_HORIZ)
    # and the arc that runs from the west rim crossing through the pocket
    # apex (15 mm into the shoulder) to the east rim crossing.
    if getattr(g, 'SHOULDER_DIFFUSER_ENABLED', False):
        diff_pts = g.shoulder_diffuser_arc_xy(60)
        if diff_pts:
            west_x = diff_pts[0][0]
            east_x = diff_pts[-1][0]
            y_rim = g.Y_ST_HORIZ
            closed = [(west_x, y_rim)] + diff_pts + [(east_x, y_rim)]
            parts.append(
                f'<path d="{polygon_d(closed)}" '
                f'fill="{FILL_DIFFUSER}" fill-opacity="0.6" '
                f'stroke="{STROKE_BASE}" stroke-width="{SW_LIGHT}" '
                f'stroke-opacity="0.75"/>'
            )
            cx, cy = g.SHOULDER_DIFFUSER_CENTER_XY
            apex_y = cy - g.SHOULDER_DIFFUSER_DEPTH
            parts.append(
                f'<circle cx="{cx:.3f}" cy="{apex_y:.3f}" r="1.5" '
                f'fill="{STROKE_BASE}"/>'
            )
            parts.append(
                f'<text x="{cx + 4:.3f}" y="{apex_y - 2:.3f}" '
                f'font-family="sans-serif" font-size="10" '
                f'fill="{STROKE_BASE}">DIFF_C</text>'
            )

    # Neck outline from erand47jc_opt.svg — draw in authoring frame.
    if NECK_D:
        parts.append(
            f'<g transform="translate({INKSCAPE_DX},{INKSCAPE_DY})">'
            f'<path d="{NECK_D}" fill="{FILL_NECK}" fill-opacity="0.4" '
            f'stroke="{STROKE_NECK}" stroke-width="{SW_HEAVY}"/>'
            f'</g>'
        )

    # Per-string hardware:
    #   - Flat pin: a small nail at the `pin` position. The string flows
    #     over it; the bend in the string polyline IS at this point.
    #     Drawn as a 2 mm dark dot (a nail head in side view).
    #   - Nat clicky pen: R = R_BUFFER clicky hole centered on the `nat`
    #     pitch point on the string (one semitone south of the pin).
    #   - Sharp clicky pen: R = R_BUFFER clicky hole centered on the
    #     `sharp` pitch point (two semitones south of the pin).
    #   Both clicky circles represent the 12 mm material allowance the
    #   neck is designed around so the drilled shaft holes don't split
    #   the neck under string tension.
    import build_harp as _bh
    _strings = _bh.build_strings()
    R_BUF = _bh.R_BUFFER
    FLAT_PIN_R = 1.5  # mm, simple tuning-pin (nail) radius, string wraps around
    for idx, s in enumerate(_strings):
        string_num = idx + 1
        is_odd = string_num % 2 == 1
        # Convention: EVEN strings drill through the +z (right) plate (blue);
        # ODD through the -z (left) plate (orange). Parity color marks
        # which plate each string's tuner/nat/sharp holes are drilled in.
        parity_color = FILL_TUNER_ODD if is_odd else FILL_TUNER_EVEN
        px, py = s['pin']
        fb_x, fb_y = s['flat_buffer']
        # Guitar tuner at end of string: gear-post circle at flat_buffer,
        # filled with parity color. Ring shows the post OD (GEAR_POST_DIA).
        parts.append(
            f'<circle cx="{fb_x:.3f}" cy="{fb_y:.3f}" '
            f'r="{(GEAR_POST_DIA/2):.3f}" '
            f'fill="{parity_color}" fill-opacity="0.55" '
            f'stroke="#000" stroke-width="0.3"/>')
        # Flat pin (nail): small circle TANGENT to the string on its east
        # side, so the string wraps around the pin heading up-NE to the
        # tuner. Pin center is offset east by PIN_R from the string.
        parts.append(
            f'<circle cx="{(px + FLAT_PIN_R):.3f}" cy="{py:.3f}" '
            f'r="{FLAT_PIN_R:.3f}" '
            f'fill="#222" stroke="#000" stroke-width="0.3"/>')
        # Nat clicky buffer — 12 mm ring at nat pitch point on string.
        nx, ny = s['nat']
        parts.append(
            f'<circle cx="{nx:.3f}" cy="{ny:.3f}" r="{R_BUF}" '
            f'fill="none" stroke="#3366cc" stroke-width="0.6"/>')
        parts.append(
            f'<circle cx="{nx:.3f}" cy="{ny:.3f}" r="1.5" '
            f'fill="#3366cc"/>')
        # Sharp clicky buffer — 12 mm ring at sharp pitch point on string.
        shx, shy = s['sharp']
        parts.append(
            f'<circle cx="{shx:.3f}" cy="{shy:.3f}" r="{R_BUF}" '
            f'fill="none" stroke="#cc3333" stroke-width="0.6"/>')
        parts.append(
            f'<circle cx="{shx:.3f}" cy="{shy:.3f}" r="1.5" '
            f'fill="#cc3333"/>')

    return parts


def top_view_content():
    """xz plane: x right, z down (so +z goes "down" on the page).
       Y is projected out. Returns SVG elements in a local (x_local, z_local) frame."""
    parts = []
    sps, grommet, tip, maxz = sample_chamber_outline()

    # Chamber footprint: at each sp, the cross-section spans x in
    # [centerline_x, centerline_x + 4b*n_hat_x] and z in [-D/2, +D/2].
    # Upper envelope (z = +D/2) and lower envelope (z = -D/2), as a pear
    # closed by extreme sp.
    # For each sp, the projected x is the RANGE [centerline_x, bulge_tip_x];
    # the farthest-z points happen at some intermediate n_local (theta=pi/2
    # or 3pi/2). Their x at theta=pi/2 is centerline_x + b*n_hat_x
    # (since n_local = b at theta=pi/2).
    upper = []   # z = +D/2 outline
    lower = []   # z = -D/2 outline
    for sp in sps:
        b = g.b_of(sp)
        if b <= 0: continue
        # At theta = pi/2: n_local = b, z_local = 2b (max +z)
        x_here = g.centerline_point(sp)[0] + b * g.n[0]
        zhalf = g.D_of(sp) / 2
        upper.append((x_here, +zhalf))
        lower.append((x_here, -zhalf))
    footprint = upper + list(reversed(lower))
    parts.append(
        f'<path d="{polygon_d(footprint)}" '
        f'fill="{FILL_CHAMBER}" stroke="{STROKE_OUTLINE}" '
        f'stroke-width="{SW_HEAVY}"/>')

    # Soundboard axis (z = 0 running x = CO.x to ST.x)
    parts.append(
        f'<line x1="{g.CO[0]:.3f}" y1="0" '
        f'x2="{g.ST[0]:.3f}" y2="0" '
        f'stroke="{STROKE_SOUND}" stroke-width="{SW_HEAVY}"/>')

    # Column top-down: projected along y. Because the column is bent in x-y
    # (see geometry.column_outer_x), the projection onto the xz plane is the
    # union over y of [column_outer_x(y), column_inner_x(y)]. Both faces
    # shift together so the silhouette is a rectangle whose x-extent spans
    # the bend's range: from min column_outer_x (at y=NT.y or y=FLOOR_Y) to
    # column_inner_x at y_mid (where the offset is zero). Sample densely
    # along the column's vertical range to find the exact envelope.
    _col_y_top = g.NT[1]
    _col_y_bot = g.FLOOR_Y
    _samples_y = [_col_y_top + (_col_y_bot - _col_y_top) * k / 200
                  for k in range(201)]
    _proj_xmin = min(g.column_outer_x(y) for y in _samples_y)
    _proj_xmax = max(g.column_inner_x(y) for y in _samples_y)
    parts.append(
        f'<rect x="{_proj_xmin:.3f}" '
        f'y="{-g.COLUMN_Z_HALF:.3f}" '
        f'width="{(_proj_xmax - _proj_xmin):.3f}" '
        f'height="{2*g.COLUMN_Z_HALF:.3f}" '
        f'fill="{FILL_COLUMN}" stroke="{STROKE_OUTLINE}" '
        f'stroke-width="{SW_LIGHT}"/>')

    # Grommets (on centerline) for SP range where grommets exist
    for name, _, _, (gx, gy) in g.GROMMETS:
        parts.append(
            f'<circle cx="{gx:.3f}" cy="0" r="2" fill="{STROKE_SOUND}"/>')

    # Neck — two plywood strips at ±[NECK_Z_INNER, NECK_Z_OUTER],
    # x from NECK_XMIN to NECK_XMAX (the neck's authoring-frame x-range).
    for z_sign in (+1, -1):
        z0 = z_sign * NECK_Z_INNER
        z1 = z_sign * NECK_Z_OUTER
        y = min(z0, z1)
        h = abs(z1 - z0)
        parts.append(
            f'<rect x="{NECK_XMIN:.3f}" y="{y:.3f}" '
            f'width="{(NECK_XMAX - NECK_XMIN):.3f}" height="{h:.3f}" '
            f'fill="{FILL_NECK}" stroke="{STROKE_NECK}" stroke-width="{SW_LIGHT}"/>'
        )

    # Strings project to points at (px, 0) in top view. Draw small dots
    # colored by note — shows pin x-positions and lets you verify adjacent
    # tuners don't collide with their own strings.
    for (px, _), note, dia in zip(PIN_XY, PIN_NOTES, STRING_DIAMETERS):
        parts.append(
            f'<circle cx="{px:.3f}" cy="0" r="{max(1.0, dia/2):.3f}" '
            f'fill="{_string_stroke(note)}"/>')

    # Guitar-style tuner bodies, tuner drill holes, and clicky drill holes,
    # alternating plates by string parity so no single x has holes through
    # both plates (would split the neck under string tension).
    #   Convention: EVEN strings → +z (right) plate; ODD → -z (left) plate.
    # Each plate is 6 mm thick between z ∈ [NECK_Z_INNER, NECK_Z_OUTER]
    # on +z side (and the mirror on -z). Drilled holes are drawn centered
    # on the plate midline.
    import build_harp as _bh_top
    _strings_top = _bh_top.build_strings()
    TUNER_HOLE_DIA  = GEAR_POST_DIA + 0.6   # 16 mm clearance for the 15.4 post
    CLICKY_HOLE_DIA = 6.5                   # clicky shaft clearance
    for idx, ((px, py), s) in enumerate(zip(PIN_XY, _strings_top)):
        string_num = idx + 1
        is_odd = string_num % 2 == 1
        color = FILL_TUNER_ODD if is_odd else FILL_TUNER_EVEN
        z_sign = -1 if is_odd else +1
        plate_mid_z = z_sign * (NECK_Z_INNER + NECK_Z_OUTER) / 2
        # Tuner body (case) on the outside face of the active plate.
        body_z = z_sign * NECK_Z_OUTER
        body_z2 = body_z + z_sign * TUNER_BODY_D
        body_y = min(body_z, body_z2)
        body_h = abs(body_z2 - body_z)
        parts.append(
            f'<rect x="{(px - TUNER_BODY_W/2):.3f}" y="{body_y:.3f}" '
            f'width="{TUNER_BODY_W:.3f}" height="{body_h:.3f}" '
            f'fill="{color}" fill-opacity="0.55" '
            f'stroke="#000" stroke-width="0.3"/>')
        # Tuner gear-post drill hole through the active plate.
        parts.append(
            f'<circle cx="{px:.3f}" cy="{plate_mid_z:.3f}" '
            f'r="{(TUNER_HOLE_DIA/2):.3f}" '
            f'fill="#fff" stroke="#888" stroke-width="0.4"/>')
        # Nat clicky drill hole (at nat pitch point x — same as pin.x).
        parts.append(
            f'<circle cx="{s["nat"][0]:.3f}" cy="{plate_mid_z:.3f}" '
            f'r="{(CLICKY_HOLE_DIA/2):.3f}" '
            f'fill="#fff" stroke="#3366cc" stroke-width="0.4"/>')
        # Sharp clicky drill hole (at sharp pitch point x — same as pin.x).
        parts.append(
            f'<circle cx="{s["sharp"][0]:.3f}" cy="{plate_mid_z:.3f}" '
            f'r="{(CLICKY_HOLE_DIA/2):.3f}" '
            f'fill="#fff" stroke="#cc3333" stroke-width="0.4"/>')
        # Spool shaft marker (small dark dot at pin position, on z=0 centerline).
        parts.append(
            f'<circle cx="{px:.3f}" cy="0" r="1.0" fill="#222"/>')

    # Axis indicator (center line z=0)
    parts.append(
        f'<line x1="-150" y1="0" x2="950" y2="0" '
        f'stroke="{STROKE_AXIS}" stroke-width="{SW_AXIS}" '
        f'stroke-dasharray="{DASH_AXIS}"/>')

    return parts


def front_view_content():
    """yz plane: z right, y down. Returns SVG elements in (z_local, y) frame."""
    parts = []
    sps, grommet, tip, maxz = sample_chamber_outline()

    # Chamber silhouette: at each sp, y = centerline_y(sp), z ranges from
    # -D/2 to +D/2. The silhouette is a bilaterally-symmetric teardrop.
    # Because the chamber axis tilts 32° from vertical, the +z and -z
    # envelopes are slightly sheared in y — but since we project ALONG x,
    # all points at the same (y, z) collapse together, and the silhouette
    # is symmetric about z=0.
    # The y-range at each sp: chamber cross-section has n_local in [0, 4b];
    # n_local * n_y contributes to y. So y_range at sp is
    # [centerline_y(sp), centerline_y(sp) + 4b * n_y].
    # Since n_y = 0.5299 > 0, +n contributes +y (downward in SVG).
    # So each cross-section occupies a vertical strip in (z, y).
    # The full silhouette is the union of all such strips — bounded by
    # the envelope of (±D/2, y) over all sp.
    # Silhouette: for each sp, the widest point of the cross-section sits at
    # (±D/2, centerline_y + b·n_y). Clip at FLOOR_Y so the silhouette doesn't
    # dip below the floor at the bass end.
    upper_y = []
    lower_y = []
    for sp in sps:
        if g.D_of(sp) <= 0: continue
        b = g.b_of(sp)
        y_widest = g.centerline_point(sp)[1] + b * g.n[1]
        if y_widest > g.FLOOR_Y:
            continue
        upper_y.append((+g.D_of(sp)/2, y_widest))
        lower_y.append((-g.D_of(sp)/2, y_widest))
    # Cap the south end with a horizontal at FLOOR_Y so the silhouette
    # terminates cleanly on the floor instead of trailing into empty space.
    if upper_y:
        upper_y.append((upper_y[-1][0], g.FLOOR_Y))
        lower_y.append((lower_y[-1][0], g.FLOOR_Y))
    silhouette = upper_y + list(reversed(lower_y))
    parts.append(
        f'<path d="{polygon_d(silhouette)}" '
        f'fill="{FILL_CHAMBER}" stroke="{STROKE_OUTLINE}" '
        f'stroke-width="{SW_HEAVY}"/>')

    # Column strip (z ∈ [-19.5, +19.5], y ∈ [NT.y, FLOOR_Y])
    parts.append(
        f'<rect x="{-g.COLUMN_Z_HALF:.3f}" y="{g.NT[1]:.3f}" '
        f'width="{2*g.COLUMN_Z_HALF:.3f}" '
        f'height="{(g.FLOOR_Y - g.NT[1]):.3f}" '
        f'fill="{FILL_COLUMN}" stroke="{STROKE_OUTLINE}" '
        f'stroke-width="{SW_LIGHT}"/>')

    # Floor line
    parts.append(
        f'<line x1="-250" y1="{g.FLOOR_Y:.3f}" '
        f'x2="250" y2="{g.FLOOR_Y:.3f}" '
        f'stroke="{STROKE_FLOOR}" stroke-width="{SW_HEAVY}" '
        f'stroke-dasharray="8 4"/>')

    # Neck — two plywood strips at ±[NECK_Z_INNER, NECK_Z_OUTER], vertical
    # extent = NECK_YMIN..NECK_YMAX.
    for z_sign in (+1, -1):
        z0 = z_sign * NECK_Z_INNER
        z1 = z_sign * NECK_Z_OUTER
        x = min(z0, z1)
        w = abs(z1 - z0)
        parts.append(
            f'<rect x="{x:.3f}" y="{NECK_YMIN:.3f}" '
            f'width="{w:.3f}" height="{(NECK_YMAX - NECK_YMIN):.3f}" '
            f'fill="{FILL_NECK}" stroke="{STROKE_NECK}" stroke-width="{SW_LIGHT}"/>'
        )

    # Guitar-style tuner bodies at each pin. In front view, z is horizontal
    # (SVG x) and y is vertical (SVG y). Body extends out from plywood face
    # in the z direction, and has height TUNER_BODY_H along the string (y).
    for idx, (px, py) in enumerate(PIN_XY):
        string_num = idx + 1
        is_odd = string_num % 2 == 1
        # EVEN strings mount on +z (right) plate; ODD on -z (left).
        color = FILL_TUNER_ODD if is_odd else FILL_TUNER_EVEN
        z_sign = -1 if is_odd else +1
        body_z = z_sign * NECK_Z_OUTER
        body_z2 = body_z + z_sign * TUNER_BODY_D
        body_x = min(body_z, body_z2)
        body_w = abs(body_z2 - body_z)
        parts.append(
            f'<rect x="{body_x:.3f}" y="{(py - TUNER_BODY_H/2):.3f}" '
            f'width="{body_w:.3f}" height="{TUNER_BODY_H:.3f}" '
            f'fill="{color}" fill-opacity="0.55" '
            f'stroke="#000" stroke-width="0.3"/>')

    # Centerline — stop at the floor, not past it.
    parts.append(
        f'<line x1="0" y1="0" x2="0" y2="{g.FLOOR_Y:.3f}" '
        f'stroke="{STROKE_AXIS}" stroke-width="{SW_AXIS}" '
        f'stroke-dasharray="{DASH_AXIS}"/>')

    return parts


def rear_view_content():
    """Mirror of the front view (looking from -x toward +x — chamber belly
    facing the viewer). Silhouette is identical because the chamber is
    symmetric about z=0, but we flip the z axis so that "left" and "right"
    are exchanged compared to the front view (useful when sound-hole or
    strut asymmetries get added later)."""
    parts = []
    sps, grommet, tip, maxz = sample_chamber_outline()

    upper_y = []
    lower_y = []
    for sp in sps:
        if g.D_of(sp) <= 0: continue
        b = g.b_of(sp)
        y_widest = g.centerline_point(sp)[1] + b * g.n[1]
        if y_widest > g.FLOOR_Y:
            continue
        # Note: flipped z compared to front_view (rear looks at mirror image).
        upper_y.append((-g.D_of(sp)/2, y_widest))
        lower_y.append((+g.D_of(sp)/2, y_widest))
    if upper_y:
        upper_y.append((upper_y[-1][0], g.FLOOR_Y))
        lower_y.append((lower_y[-1][0], g.FLOOR_Y))
    silhouette = upper_y + list(reversed(lower_y))
    parts.append(
        f'<path d="{polygon_d(silhouette)}" '
        f'fill="{FILL_CHAMBER}" fill-opacity="0.8" stroke="{STROKE_OUTLINE}" '
        f'stroke-width="{SW_HEAVY}"/>')

    # Column strip (same as front — symmetric about z=0).
    parts.append(
        f'<rect x="{-g.COLUMN_Z_HALF:.3f}" y="{g.NT[1]:.3f}" '
        f'width="{2*g.COLUMN_Z_HALF:.3f}" '
        f'height="{(g.FLOOR_Y - g.NT[1]):.3f}" '
        f'fill="{FILL_COLUMN}" stroke="{STROKE_OUTLINE}" '
        f'stroke-width="{SW_LIGHT}"/>')

    # Floor line
    parts.append(
        f'<line x1="-250" y1="{g.FLOOR_Y:.3f}" '
        f'x2="250" y2="{g.FLOOR_Y:.3f}" '
        f'stroke="{STROKE_FLOOR}" stroke-width="{SW_HEAVY}" '
        f'stroke-dasharray="8 4"/>')

    # Neck plywood strips (same positions but flipped z-sense: tuner bodies
    # sit on the opposite sides compared to the front view).
    for z_sign in (+1, -1):
        z0 = z_sign * NECK_Z_INNER
        z1 = z_sign * NECK_Z_OUTER
        x = min(z0, z1)
        w = abs(z1 - z0)
        parts.append(
            f'<rect x="{x:.3f}" y="{NECK_YMIN:.3f}" '
            f'width="{w:.3f}" height="{(NECK_YMAX - NECK_YMIN):.3f}" '
            f'fill="{FILL_NECK}" stroke="{STROKE_NECK}" stroke-width="{SW_LIGHT}"/>'
        )

    # Tuner bodies — from the rear, odd strings (right plywood = +z) appear
    # on the LEFT side because we've mirrored z. Flip z_sign at the body
    # position so the visual matches "looking from behind".
    for idx, (px, py) in enumerate(PIN_XY):
        string_num = idx + 1
        is_odd = string_num % 2 == 1
        # Rear view: z is mirrored, so ODD strings (left plate = -z in
        # authoring) appear on the +z side here.
        color = FILL_TUNER_ODD if is_odd else FILL_TUNER_EVEN
        z_sign = +1 if is_odd else -1    # mirrored from front view
        body_z = z_sign * NECK_Z_OUTER
        body_z2 = body_z + z_sign * TUNER_BODY_D
        body_x = min(body_z, body_z2)
        body_w = abs(body_z2 - body_z)
        parts.append(
            f'<rect x="{body_x:.3f}" y="{(py - TUNER_BODY_H/2):.3f}" '
            f'width="{body_w:.3f}" height="{TUNER_BODY_H:.3f}" '
            f'fill="{color}" fill-opacity="0.55" '
            f'stroke="#000" stroke-width="0.3"/>')

    # Centerline — stop at the floor.
    parts.append(
        f'<line x1="0" y1="0" x2="0" y2="{g.FLOOR_Y:.3f}" '
        f'stroke="{STROKE_AXIS}" stroke-width="{SW_AXIS}" '
        f'stroke-dasharray="{DASH_AXIS}"/>')

    return parts


def sbf_view_content():
    """(u, z) plane, face-on to the tilted soundboard. u is the
    soundboard station (sp measured from CO along u_hat). z is
    perpendicular horizontal.

    Orientation: bass end (small sp) at the BOTTOM of the drawing, treble
    end (large sp) at the TOP — matches the physical harp orientation in
    the side view. SVG y-axis grows downward, so we map y = −sp (with an
    offset so values are positive-ish). That's equivalent to y = Ymax − sp
    where Ymax = S_TREBLE_CLEAR."""
    parts = []
    sps, _, _, _ = sample_chamber_outline()

    Y_OFF = g.S_TREBLE_CLEAR   # flips sp so treble is at top (small y)

    def ysp(sp):
        return Y_OFF - sp

    # Pear outline: at each sp, half-width D/2 in z.
    upper = []   # +z edge
    lower = []   # -z edge
    for sp in sps:
        if g.D_of(sp) <= 0:
            continue
        zhalf = g.D_of(sp)/2
        upper.append((+zhalf, ysp(sp)))
        lower.append((-zhalf, ysp(sp)))
    pear = upper + list(reversed(lower))
    parts.append(
        f'<path d="{polygon_d(pear)}" '
        f'fill="{FILL_CHAMBER}" stroke="{STROKE_OUTLINE}" '
        f'stroke-width="{SW_HEAVY}"/>')

    # Centerline (z=0) — this IS the grommet line in SBF view
    parts.append(
        f'<line x1="0" y1="{ysp(g.S_BASS_CLEAR):.3f}" '
        f'x2="0" y2="{ysp(g.S_TREBLE_CLEAR):.3f}" '
        f'stroke="{STROKE_SOUND}" stroke-width="{SW_HEAVY}"/>')

    # Grommets on the centerline at their s' values
    for name, _, sprime, _ in g.GROMMETS:
        parts.append(
            f'<circle cx="0" cy="{ysp(sprime):.3f}" r="3" fill="{STROKE_SOUND}"/>')
        # C and F string labels
        if name[0] in "CF":
            parts.append(
                f'<text x="-8" y="{(ysp(sprime)+3):.3f}" font-family="sans-serif" '
                f'font-size="11" fill="#666" text-anchor="end">{name}</text>')

    # Station labels at CO, CI, peak, ST, treble clear
    for label, sp in [("CO", 0.0), ("CI", 73.59), ("peak", g.S_PEAK),
                      ("ST", g.L_CO_ST), ("treble clear", g.S_TREBLE_CLEAR),
                      ("bass clear", g.S_BASS_CLEAR)]:
        parts.append(
            f'<text x="200" y="{ysp(sp)+3:.3f}" font-family="sans-serif" '
            f'font-size="11" fill="#333">s\'={sp:.1f} D={g.D_of(sp):.1f} ({label})</text>')

    return parts


# ----- Layout -----
def main():
    LABEL_FONT = 22
    GAP = 80

    # Per-view bounding boxes in view-local coordinates (pre-transform):
    #   side  : x ∈ [−60, 950], y ∈ [0, 1930]       (1010 × 1930)
    #   front : z ∈ [−220, 220], y ∈ [0, 1940]      (440 × 1940)
    #   top   : x ∈ [−150, 950], z ∈ [−200, 200]    (1100 × 400)
    #   sbf   : z ∈ [−200, 220], sp ∈ [−140, 1600]  (420 × 1740)
    #     + extra ~400 px for the station labels to the right of the pear

    # Layout: row 1 side + sbf + front, row 2 top.
    # Work in millimeters (source units); SVG viewBox spans the whole canvas.

    side_x, side_y, side_w, side_h = 0, 40, 1010, 1930
    sbf_x,  sbf_y,  sbf_w,  sbf_h  = side_x + side_w + GAP, 40, 820, 1740
    front_x, front_y, front_w, front_h = sbf_x + sbf_w + GAP, 40, 440, 1940
    top_x,  top_y,  top_w,  top_h  = 0, side_y + side_h + GAP + 40, 1100, 400

    canvas_w = max(front_x + front_w, top_x + top_w) + 40
    canvas_h = max(top_y + top_h, side_y + side_h) + 40

    out = [
        f'<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {canvas_w} {canvas_h}" '
        f'width="{canvas_w/3.5:.0f}" height="{canvas_h/3.5:.0f}" '
        f'preserveAspectRatio="xMidYMid meet">',
        f'<rect x="0" y="0" width="{canvas_w}" height="{canvas_h}" fill="#fff"/>',
    ]

    def view_frame(x, y, w, h, label):
        """Box + label + sub-SVG transform."""
        return [
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" '
            f'fill="none" stroke="#ccc" stroke-width="0.5"/>',
            f'<text x="{x+10}" y="{y-10}" font-family="sans-serif" '
            f'font-size="{LABEL_FONT}" font-weight="bold" fill="#000">{label}</text>',
        ]

    # --- Side view ---
    # Local coords: x ∈ [−60, 950], y ∈ [0, 1930]. Translate to fit into the frame.
    out.extend(view_frame(side_x, side_y, side_w, side_h,
                          "Side view (xy, project along z)"))
    out.append(f'<g transform="translate({side_x+60},{side_y})">')
    out.extend(side_view_content())
    out.append('</g>')

    # --- SBF view ---
    # Local: z ∈ [−200, 200], sp ∈ [S_BASS_CLEAR, S_TREBLE_CLEAR] with the
    # y-axis flipped so treble (large sp) is at the TOP and bass (small sp)
    # at the BOTTOM — matches the physical orientation in the side view.
    # Content y range: [0, S_TREBLE_CLEAR − S_BASS_CLEAR] ≈ [0, 1726.45].
    out.extend(view_frame(sbf_x, sbf_y, sbf_w, sbf_h,
                          "Soundboard-face view (u, z)"))
    sbf_cx = sbf_x + 220   # origin for z=0
    sbf_cy = sbf_y         # local y=0 (= sp=S_TREBLE_CLEAR, treble end) at top
    out.append(f'<g transform="translate({sbf_cx},{sbf_cy})">')
    out.extend(sbf_view_content())
    out.append('</g>')

    # --- Front view ---
    out.extend(view_frame(front_x, front_y, front_w, front_h,
                          "Front view (yz, project along x)"))
    fr_cx = front_x + 220  # origin z=0
    fr_cy = front_y        # origin y=0
    out.append(f'<g transform="translate({fr_cx},{fr_cy})">')
    out.extend(front_view_content())
    out.append('</g>')

    # --- Top view ---
    out.extend(view_frame(top_x, top_y, top_w, top_h,
                          "Top view (xz, project along y)"))
    top_cx = top_x + 150       # offset for x; local x=0 to local_x=150
    top_cy = top_y + top_h/2   # z=0 in middle
    out.append(f'<g transform="translate({top_cx},{top_cy})">')
    out.extend(top_view_content())
    out.append('</g>')

    out.append('</svg>')

    with open(OUTPUT, "w") as fh:
        fh.write("\n".join(out))

    # Individual SVGs for standalone zoom in the HTML viewer.
    def standalone(elements, minx, miny, w, h, title):
        hdr = [
            f'<?xml version="1.0" encoding="UTF-8"?>',
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'viewBox="{minx} {miny} {w} {h}" '
            f'preserveAspectRatio="xMidYMid meet">',
            f'<title>{title}</title>',
            f'<rect x="{minx}" y="{miny}" width="{w}" height="{h}" fill="#fff"/>',
        ]
        return "\n".join(hdr + elements + ["</svg>"])

    # Side: x in [-60, 950], y in [0, 1940]
    with open(OUTPUT_SIDE, "w") as fh:
        fh.write(standalone(side_view_content(), -100, -20, 1100, 1980, "Side view"))
    # Top: x in [-150, 950], z in [-220, 220]; rotate -90° so treble ends
    # up at top and bass at bottom (matches side view orientation).
    # After rotate(-90): orig (x, z) → new (z, -x), so new x ∈ [-220, 220],
    # new y ∈ [-1000, 200].
    _top_elts = top_view_content()
    _top_wrapped = ['<g transform="rotate(-90)">'] + _top_elts + ['</g>']
    with open(OUTPUT_TOP, "w") as fh:
        fh.write(standalone(_top_wrapped, -240, -1020, 480, 1240, "Top view (rotated)"))
    # Front: z in [-220, 220], y in [0, 1940]
    with open(OUTPUT_FRONT, "w") as fh:
        fh.write(standalone(front_view_content(), -240, -20, 480, 1980, "Front view"))
    # Rear: same bounds as front (symmetric silhouette)
    with open(OUTPUT_REAR, "w") as fh:
        fh.write(standalone(rear_view_content(), -240, -20, 480, 1980, "Rear view"))
    # SBF: z in [-220, 220], sp in [-140, 1600]
    with open(OUTPUT_SBF, "w") as fh:
        fh.write(standalone(sbf_view_content(), -240, -20,
                            480 + 500, g.S_TREBLE_CLEAR - g.S_BASS_CLEAR + 40,
                            "Soundboard-face view"))

    print(f"wrote {OUTPUT}")
    print(f"also wrote: {OUTPUT_SIDE}, {OUTPUT_TOP}, {OUTPUT_FRONT}, {OUTPUT_REAR}, {OUTPUT_SBF}")
    print(f"canvas: {canvas_w:.0f} x {canvas_h:.0f} mm")


if __name__ == "__main__":
    main()
