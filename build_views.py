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
NECK_SRC = os.path.join(HERE, "erand47jc_v2_opt.svg")

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

# Guitar-style tuner geometry (mini machine head, e.g. Gotoh SG381-05).
# Body mounts on the outside face of the plywood; spool shaft passes through
# the 6 mm plywood into the string gap; knob protrudes radially in the plywood
# plane (in xy; drawn in side view as a small knob).
TUNER_BODY_W     = 14.0        # mm, across the neck axis (xy-plane, perpendicular to string)
TUNER_BODY_H     = 35.0        # mm, along the string direction
TUNER_BODY_D     = 22.0        # mm, outward from plywood face (along ±z)
TUNER_KNOB_DIA   = 15.0        # mm, knob diameter
TUNER_KNOB_OUT   = 18.0        # mm, knob sticks out from body centerline

# Alternation convention: odd string numbers (1=C1, 3=E1, ...) go on +z side
# (right plywood); even numbers (2=D1, 4=F1, ...) on -z side (left plywood).
# Pin (pin_x, pin_y) positions, string 1..47 bass-to-treble.
PIN_XY = [
    (101.700, 146.563), (119.632, 143.109), (137.565, 139.654),
    (155.523, 136.200), (173.455, 137.775), (191.387, 139.375),
    (209.320, 140.975), (227.252, 142.575), (245.210, 149.230),
    (263.142, 160.914), (281.075, 152.380), (299.007, 159.035),
    (316.432, 206.888), (333.856, 234.574), (351.280, 272.319),
    (368.705, 310.088), (385.113, 344.455), (401.522, 388.879),
    (417.905, 423.245), (433.297, 464.266), (448.664, 485.120),
    (464.031, 511.028), (479.423, 531.856), (494.790, 547.629),
    (510.157, 558.399), (525.524, 569.143), (539.875, 576.484),
    (554.226, 583.799), (568.577, 586.085), (582.928, 588.371),
    (597.279, 590.657), (611.630, 582.834), (625.981, 585.120),
    (639.316, 578.947), (652.626, 572.775), (665.961, 566.603),
    (679.296, 560.431), (692.606, 554.259), (705.941, 548.086),
    (719.250, 541.889), (732.585, 530.687), (745.920, 519.435),
    (759.230, 508.234), (772.565, 496.982), (785.874, 485.780),
    (799.209, 474.553), (812.544, 463.327),
]
assert len(PIN_XY) == 47
PIN_NOTES = ["C1","D1","E1","F1","G1","A1","B1",
             "C2","D2","E2","F2","G2","A2","B2",
             "C3","D3","E3","F3","G3","A3","B3",
             "C4","D4","E4","F4","G4","A4","B4",
             "C5","D5","E5","F5","G5","A5","B5",
             "C6","D6","E6","F6","G6","A6","B6",
             "C7","D7","E7","F7","G7"]

FILL_TUNER_ODD  = "#d46a3a"    # orange, +z side (right plywood)
FILL_TUNER_EVEN = "#3a6fd4"    # blue,   -z side (left plywood)

# Per-string: pin (px, py), grommet (px, gy) — same x, different y.
# Grommet y values from _RAW_GEOM (3rd column).
GROMMET_Y = [
    1661.495, 1632.793, 1604.091, 1575.389, 1546.662, 1517.960, 1489.258,
    1460.556, 1431.854, 1403.152, 1374.425, 1345.723, 1317.833, 1289.970,
    1262.080, 1234.191, 1207.953, 1181.689, 1155.451, 1130.839, 1106.251,
    1081.639, 1057.026, 1032.414, 1007.826,  983.214,  960.252,  937.291,
     914.329,  891.367,  868.406,  845.444,  822.482,  801.147,  779.811,
     758.500,  737.164,  715.853,  694.517,  673.181,  651.871,  630.535,
     609.224,  587.888,  566.578,  545.242,  523.931,
]
assert len(GROMMET_Y) == 47
# Actual string diameters in mm (C-F register), from build_harp._STRING_WIDTHS.
STRING_DIAMETERS = [
    1.676, 1.549, 1.448, 1.270, 1.219, 1.219, 1.016, 1.016, 0.914, 2.642,
    2.489, 2.337, 2.184, 2.057, 2.057, 1.930, 1.676, 1.676, 1.549, 1.549,
    1.270, 1.270, 1.270, 1.143, 1.143, 1.143, 1.016, 1.016, 1.016, 0.914,
    0.914, 0.914, 0.813, 0.813, 0.813, 0.813, 0.762, 0.762, 0.762, 0.711,
    0.711, 0.660, 0.635, 0.635, 0.635, 0.635, 0.635,
]
assert len(STRING_DIAMETERS) == 47
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

    flat_floor = g.centerline_point(g.S_BASS_CLEAR)  # (-57.04, 1915.5)

    # East boundary: bulge-tip curve from sp_floor up to sp_topofbase.
    east_curve = [(p[0], p[1]) for sp, p in zip(sps, tip)
                  if sp_floor <= sp <= sp_topofbase]

    base_poly = (
        [(g.CO[0], base_top_y),                   # CO (top of base, west)
         (flat_floor[0], flat_floor[1]),          # flat face at floor
         (tip_floor[0], base_bot_y)]              # bulge tip on floor (east)
        + east_curve                               # east edge up bulge tip
        + [(tip_topofbase[0], base_top_y)]        # top of east edge
    )
    parts.append(
        f'<path d="{polygon_d(base_poly)}" '
        f'fill="{FILL_BASE}" stroke="{STROKE_BASE}" '
        f'stroke-width="{SW_LIGHT}" opacity="0.6"/>'
    )

    # Column: from NT down to the floor. The TOP of the column follows the
    # neck's lower curve (closing cubic n8→NTO) between x=COLUMN_OUTER_X
    # and x=COLUMN_INNER_X so the column flows into the neck instead of
    # meeting it with a flat-top corner.
    col_bot_y = g.FLOOR_Y
    # Sample the neck's closing-to-NTO cubic at many t, collect points where
    # x sits within the column's outer..inner range.
    def _bez_cubic(P0, P1, P2, P3, t):
        u = 1 - t
        return (u*u*u*P0[0] + 3*u*u*t*P1[0] + 3*u*t*t*P2[0] + t*t*t*P3[0],
                u*u*u*P0[1] + 3*u*u*t*P1[1] + 3*u*t*t*P2[1] + t*t*t*P3[1])
    # Authoring-frame control points of the n8→NTO cubic, from the v2 path:
    #   Inkscape frame: P0=(382.465, 258.445), P1=(282.039, -95.275),
    #                   P2=(120.944, -27.134),  P3=NTO=(-39.200, 65.288)
    # Authoring = Inkscape + (51.9, 81.27):
    _P0 = (382.465 + INKSCAPE_DX, 258.445 + INKSCAPE_DY)
    _P1 = (282.039 + INKSCAPE_DX,  -95.275 + INKSCAPE_DY)
    _P2 = (120.944 + INKSCAPE_DX,  -27.134 + INKSCAPE_DY)
    _P3 = (-39.200 + INKSCAPE_DX,   65.288 + INKSCAPE_DY)
    # Sample at fine resolution, collect (x, y) where x in [COLUMN_OUTER_X, COLUMN_INNER_X].
    cap_pts = []
    for k in range(2001):
        t = k / 2000
        x, y = _bez_cubic(_P0, _P1, _P2, _P3, t)
        if g.COLUMN_OUTER_X <= x <= g.COLUMN_INNER_X:
            cap_pts.append((x, y))
    # Order by x descending so the polygon goes inner→outer along the cap.
    cap_pts.sort(key=lambda p: -p[0])
    # Snap exact endpoints so the polygon corners sit on COLUMN_INNER_X and NTO.
    if cap_pts:
        # Inner: find y at exactly x=COLUMN_INNER_X by linear interp.
        for i in range(len(cap_pts) - 1):
            if (cap_pts[i][0] - g.COLUMN_INNER_X) * (cap_pts[i+1][0] - g.COLUMN_INNER_X) <= 0:
                x0, y0 = cap_pts[i]; x1, y1 = cap_pts[i+1]
                frac = (g.COLUMN_INNER_X - x0) / (x1 - x0) if x1 != x0 else 0
                cap_pts[i] = (g.COLUMN_INNER_X, y0 + frac*(y1-y0))
                cap_pts = cap_pts[i:]
                break
        cap_pts[-1] = (g.COLUMN_OUTER_X, g.NT[1])  # snap NTO endpoint
    # Column polygon: top cap curve + two verticals + floor line.
    col_poly = (
        [(g.COLUMN_INNER_X, col_bot_y)]           # bottom-right
        + [(g.COLUMN_INNER_X, cap_pts[0][1])]     # up to cap start (inner)
        + cap_pts                                   # curved top (inner → outer)
        + [(g.COLUMN_OUTER_X, col_bot_y)]         # down the west side to floor
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

    # Reference points (small dots + labels)
    for name, pt in [("CO", g.CO), ("CI", g.CI), ("NT", g.NT),
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

    # Neck outline from erand47jc_opt.svg — draw in authoring frame.
    if NECK_D:
        parts.append(
            f'<g transform="translate({INKSCAPE_DX},{INKSCAPE_DY})">'
            f'<path d="{NECK_D}" fill="{FILL_NECK}" fill-opacity="0.4" '
            f'stroke="{STROKE_NECK}" stroke-width="{SW_HEAVY}"/>'
            f'</g>'
        )

    # The 94 design buffers the neck outline is built around:
    #   - 47 guitar tuner pin centers  (at `flat_buffer` position)
    #   - 47 clicky pen centers        (at `sharp_buffer` position)
    # Each has R = 12 mm material allowance around the drilled hole.
    # The small filled dots inside each buffer mark the drill-hole center.
    import build_harp as _bh
    _strings = _bh.build_strings()
    R_BUF = _bh.R_BUFFER
    for idx, s in enumerate(_strings):
        string_num = idx + 1
        is_odd = string_num % 2 == 1
        color = FILL_TUNER_ODD if is_odd else FILL_TUNER_EVEN
        # Guitar tuner pin buffer (flat_buffer position).
        tx, ty = s['flat_buffer']
        parts.append(
            f'<circle cx="{tx:.3f}" cy="{ty:.3f}" r="{R_BUF}" '
            f'fill="none" stroke="#666" stroke-width="0.6"/>')
        parts.append(
            f'<circle cx="{tx:.3f}" cy="{ty:.3f}" r="2" '
            f'fill="{color}" stroke="#000" stroke-width="0.3"/>')
        # Clicky pen buffer (sharp_buffer position).
        cx, cy = s['sharp_buffer']
        parts.append(
            f'<circle cx="{cx:.3f}" cy="{cy:.3f}" r="{R_BUF}" '
            f'fill="none" stroke="#666" stroke-width="0.6"/>')
        parts.append(
            f'<circle cx="{cx:.3f}" cy="{cy:.3f}" r="2" '
            f'fill="{color}" stroke="#000" stroke-width="0.3"/>')

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

    # Column top-down: square centered on z=0 at x in [COLUMN_OUTER_X, COLUMN_INNER_X]
    parts.append(
        f'<rect x="{g.COLUMN_OUTER_X:.3f}" '
        f'y="{-g.COLUMN_Z_HALF:.3f}" '
        f'width="{g.COLUMN_WIDTH:.3f}" '
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

    # Guitar-style tuner bodies at each pin. In top view, x is horizontal and
    # z is vertical (SVG y). Each tuner body is TUNER_BODY_W wide (in x) by
    # TUNER_BODY_D deep (outward from plywood face, in z). Knob extends
    # further out as a small cylinder.
    for idx, (px, py) in enumerate(PIN_XY):
        string_num = idx + 1
        is_odd = string_num % 2 == 1
        color = FILL_TUNER_ODD if is_odd else FILL_TUNER_EVEN
        z_sign = +1 if is_odd else -1
        # Body rectangle on the outside face of the plywood.
        body_z = z_sign * NECK_Z_OUTER              # plywood outer face
        body_z2 = body_z + z_sign * TUNER_BODY_D    # out-end of body
        body_y = min(body_z, body_z2)
        body_h = abs(body_z2 - body_z)
        parts.append(
            f'<rect x="{(px - TUNER_BODY_W/2):.3f}" y="{body_y:.3f}" '
            f'width="{TUNER_BODY_W:.3f}" height="{body_h:.3f}" '
            f'fill="{color}" fill-opacity="0.55" '
            f'stroke="#000" stroke-width="0.3"/>')
        # Spool shaft (small circle at pin position)
        parts.append(
            f'<circle cx="{px:.3f}" cy="0" r="1.5" fill="#222"/>')

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
        color = FILL_TUNER_ODD if is_odd else FILL_TUNER_EVEN
        z_sign = +1 if is_odd else -1
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
        color = FILL_TUNER_ODD if is_odd else FILL_TUNER_EVEN
        z_sign = -1 if is_odd else +1    # mirrored from front view
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
