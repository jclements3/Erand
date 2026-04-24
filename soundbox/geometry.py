"""
Authoritative geometry for the Clements 47 harp soundbox.

Single source of truth. Neck-design code should import from here rather than
re-deriving or hard-coding any of these numbers.

Coordinate system: millimeters. 2D harp plane is (x, y) with y increasing
downward (SVG convention). Third axis z is perpendicular to that plane.
Chamber is symmetric about z = 0.

Soundboard axis: from CO at the bass end of the extended soundboard slope,
up-right to ST at the neck.

Design posture
--------------
This module is organized into two sections:

  --- DESIGN PARAMETERS (edit these) ---
      The true independent inputs. Changing any of these should regenerate
      the whole chamber consistently. Examples: STRING_COUNT, PITCH_RANGE_LO,
      SCALE_FACTOR, SOUNDBOARD_ANGLE_DEG, D_PEAK, floor/ST planes, column
      geometry, Erard-reference grommet pitches.

  --- DERIVED QUANTITIES (do not edit) ---
      Everything computed from the parameters above: CO, CI, ST, NB, NT,
      u/n unit vectors, L_CO_ST, the full GROMMETS table, and the helper
      functions. Changes here should only happen by editing a parameter.
"""

import math


# ============================================================================
# --- DESIGN PARAMETERS (edit these) ---
# ============================================================================

# --- Global scale ---------------------------------------------------------
# All linear geometry is multiplied by SCALE_FACTOR. 1.0 reproduces the
# canonical 1901-Erard-derived Clements 47.
SCALE_FACTOR = 1.0


# --- String configuration -------------------------------------------------
# STRING_COUNT strings from PITCH_RANGE_LO (bass, string 1) upward in
# diatonic scientific pitch notation to PITCH_RANGE_HI (treble, last
# string). Intermediate notes are C, D, E, F, G, A, B.
STRING_COUNT    = 47
PITCH_RANGE_LO  = "C1"
PITCH_RANGE_HI  = "G7"


# --- Column and soundboard axis ------------------------------------------
# CO is fixed at the bass end of the extended soundboard slope. Everything
# else in the xy plane flows from CO + soundboard axis.
CO_XY = (12.700, 1803.910)    # column outer, soundboard slope extended (reference)

# Soundboard axis angle, measured from horizontal. At 58 deg the axis rises
# up and to the right (dy negative in SVG convention).
SOUNDBOARD_ANGLE_FROM_HORIZONTAL_DEG = 58.0

# Soundboard length CO -> ST (unscaled, before SCALE_FACTOR).
L_CO_ST_BASE    = 1558.852815       # hypot(ST - CO) from Erard extraction

# CI (column inner, where the actual soundboard starts) sits on the
# soundboard axis at this s' offset from CO (unscaled).
S_CI_OFFSET_BASE = 73.585053

# Column cross-section: now ROUND (cylindrical). Diameter 39 mm, same as the
# previous square prism's width. Classical Erard harps have round columns,
# and round is easier to manufacture in CF (filament-wound tube). The bent
# column is a swept circle along the centerline arc.
COLUMN_IS_ROUND     = True            # True = cylindrical, False = rectangular prism
COLUMN_INNER_X_BASE = 51.7            # x of the column's inner face (legacy;
                                       # for round column, implies diameter =
                                       # INNER_X - OUTER_X = 39 mm)
COLUMN_Z_HALF_BASE  = 19.5            # +/- half-width in z. For round column,
                                       # this equals the radius (19.5 mm);
                                       # the column cross-section is a circle
                                       # of radius COLUMN_Z_HALF at every y.


# --- Column anchors (legacy neck-side references) ------------------------
# NB and NT are lower and upper anchors on the column for the neck curve.
# These come from the Erard extraction and are not derived from the
# soundboard axis; they are separate design inputs for the neck routing.
# They scale with SCALE_FACTOR but are otherwise independent.
NB_XY_BASE      = (12.700, 323.844)    # lower column anchor
NT_XY_BASE      = (12.700, 146.563)    # top of column outer


# --- Floor and clipping planes -------------------------------------------
FLOOR_Y_BASE    = 1860.0               # floor plane. Raised from 1915.5 — no
                                       # pedals, so the base only needs to
                                       # house the column socket + structural
                                       # footing (~56 mm of base, not the
                                       # concert-harp 112 mm).
# Y_TOP_OF_BASE is where the chamber's bottom rim sits (chamber is clipped
# here). Originally equal to CO.y = 1803.91, but the chamber-clip can be
# raised so the base extends higher into the soundbox, capturing the region
# where the bent column would otherwise cross the soundboard. With
# COLUMN_BEND_RADIUS = 10000 and direction=+1, the column crosses the
# soundboard at y ≈ 1754, so Y_TOP_OF_BASE ≥ ~1700 puts the column's bottom
# entirely inside the base material, avoiding any chamber wall intersection.
# Defaults to CO[1] if None (original behavior). Set to a specific y to move.
Y_TOP_OF_BASE_BASE = 1699.49           # mm; matches the top of the column-
                                       # soundboard intersection ellipse (where
                                       # the column's east edge first touches
                                       # the soundboard). Column is vertical
                                       # from here down (inside the base),
                                       # straight-sliding into the base socket.
# Horizontal plane through ST is derived from ST[1] below.


# --- Limacon cross-section taper -----------------------------------------
# r(theta) = a + b*cos(theta) with a = 2b   (convex limacon, no inner loop)
# Flat face at theta=pi (r=b), on the grommet/soundboard line (-n direction).
# Bulge tip at theta=0 (r=3b), into chamber (+n direction).
# Max perpendicular width D = 4.404 * b.
# Axial depth (flat-face to bulge-tip) = 4b.
# Cross-section area A(b) = 0.7289 * D**2 = 14.137 * b**2.
D_PEAK_BASE          = 360.0           # max perpendicular width at peak
S_PEAK_BASE          = 523.59          # s' where D hits its maximum
S_BASS_FINAL_BASE    = -762.87         # where the rising cosine starts from D=0
S_TREBLE_FINAL_BASE  = 2002.22         # where the falling cosine reaches D=0
# Loft range to pass to FreeCAD (clean geometry at both clipping planes)
S_BASS_CLEAR_BASE    = -66.14          # flat face meets FLOOR_Y. The chamber
                                       # is ONE continuous tube extending from
                                       # Y_ST_HORIZ down to FLOOR_Y externally;
                                       # the base is an INTERIOR plug inside
                                       # the chamber's bottom (at Y_TOP_OF_BASE).
                                       # Previously -131.59 (for old FLOOR_Y
                                       # = 1915.5); now -66.14 for FLOOR_Y
                                       # = 1860. Recompute as
                                       # (FLOOR_Y - CO.y) / u[1] if FLOOR_Y
                                       # changes.
S_TREBLE_CLEAR_BASE  = 1594.86         # bulge tip meets ST horizontal


# --- Grommet scale: 1901 Erard reference data ----------------------------
# The 47 grommet s' positions (mm along soundboard from CO, unscaled) are
# laid out in "scale tiers" - consecutive strings in a tier share the same
# spacing, and the spacing shrinks as the harp climbs toward the treble.
# This is a classical Erard scale feature and is the fundamental design
# input for the string layout.
#
# S_PRIME_FIRST_BASE: s' of the bass string (string 1 = PITCH_RANGE_LO).
# GROMMET_PITCH_TIERS: list of (last_string_index, pitch_mm) describing the
# inter-string spacing. Entry (n, p) says "strings s..n have pitch p going
# from string (s-1) to s" where s = prev-entry's last+1. Strings are
# 1-indexed; the first string has no preceding pitch.
S_PRIME_FIRST_BASE   = 167.943
GROMMET_PITCH_TIERS  = [
    # (max_string_index_inclusive, pitch_mm_to_reach_this_string)
    (12, 33.8430),   # strings 2..12 (D1..G2)
    (16, 32.8848),   # strings 13..16 (A2..D3)
    (19, 30.9490),   # strings 17..19 (E3..G3)
    (26, 29.0176),   # strings 20..26 (A3..G4)
    (33, 27.0774),   # strings 27..33 (A4..G5)
    (47, 25.1483),   # strings 34..47 (A5..G7)
]
# Within each tier the spacings above differ from the Erard-drawing
# measurements by <= 0.01 mm per string. Per-string fine corrections
# relative to the piecewise-constant tier model:
GROMMET_PITCH_RESIDUALS = {
    # (index of this string, residual added to cumulative s') preserves
    # 1901 measurements exactly. Zero means 'follows tier pitch'.
    # Populated below from the original table so the 47-string config is
    # numerically identical to the pre-refactor values.
}


# --- Shoulder joint (treble end, two-part hidden tongue-and-groove) ------
# The chamber and shoulder are TWO separately molded thin-walled CF parts,
# bonded at Y_ST_HORIZ with a hidden tongue-and-groove joint so the
# exterior surface reads as one continuous limacon loft.
#
#   - CHAMBER: thin-walled limacon shell ending at an annular rim at
#     y = Y_ST_HORIZ. The rim's top face has a TONGUE extending upward
#     (in -y direction physically) by SHOULDER_JOINT_TONGUE_HEIGHT. The
#     tongue is SHOULDER_JOINT_TONGUE_THICK thick (roughly matching the
#     CF wall thickness) and follows the annular rim shape in plan view.
#   - SHOULDER: thin-walled limacon-continuation shell whose underside has
#     a matching GROOVE sized to receive the chamber's tongue with a
#     SHOULDER_JOINT_BOND_CLEARANCE gap for structural adhesive. Shoulder
#     body rises H_SHOULDER above Y_ST_HORIZ.
#   - EXTERNAL SEAM: at y = Y_ST_HORIZ, a thin horizontal line where the
#     two parts meet externally. Hidden (reads as a design feature, not a
#     gap) by a small chamfer of depth SHOULDER_JOINT_CHAMFER on both
#     sides of the joint.
#   - GENERATOR CONTINUITY: D(s') matches across the joint -- the
#     shoulder's D at its lower edge equals the chamber's D at the rim,
#     so the exterior reads as one continuous limacon. The generator path
#     continues past ST along the soundboard tangent, through a fillet
#     arc of radius R_SHOULDER_FILLET, then along the F7-G7 south sharp-
#     buffer tangent to the apex where D -> 0.
#   - FASTENING: threaded inserts molded into the shoulder's underside
#     adjacent to the groove. Through-holes in the chamber rim aligned
#     with the inserts. Fasteners pass from INSIDE the chamber upward
#     through the rim into the shoulder inserts -- invisible externally.
#   - SLOTS: two horizontal channels in the shoulder's body receiving
#     the neck plates' ST->BT tangs. Slot mouth positioned at a generator
#     station where D(s') ~= plate z-extent for visual continuity from
#     plate surface to shoulder surface.
#
# The base joint at y = Y_TOP_OF_BASE uses the same hidden tongue-and-
# groove pattern with opposite polarity (see BASE_JOINT_* block below).
SHOULDER_JOINT_STYLE           = "tongue_groove"  # see header notes
SHOULDER_JOINT_TONGUE_HEIGHT   = 8.0    # mm, tongue rises this far above Y_ST_HORIZ
SHOULDER_JOINT_TONGUE_THICK    = 2.0    # mm, tongue wall thickness
SHOULDER_JOINT_BOND_CLEARANCE  = 0.15   # mm, groove-vs-tongue gap for adhesive
SHOULDER_JOINT_CHAMFER         = 1.0    # mm, external chamfer at seam
H_SHOULDER                     = 30.0   # mm, shoulder body rises this far above Y_ST_HORIZ
R_SHOULDER_FILLET              = 5.0    # mm, fillet arc radius at tangent intersection


# --- Base joint (bass end, two-part hidden tongue-and-groove) ------------
# Mirror of the shoulder joint, at the bass end. The chamber and the base
# are TWO separately fabricated parts bonded at y = Y_TOP_OF_BASE with a
# hidden tongue-and-groove joint. Polarity is OPPOSITE the top end: at the
# shoulder the chamber holds the tongue; here the BASE holds the tongue
# and the chamber's bottom rim holds the GROOVE.
#
#   - CHAMBER: thin-walled limacon shell open at its bottom rim at
#     y = Y_TOP_OF_BASE (no flat cap). The rim's underside has a GROOVE
#     sized to receive the base's tongue with BASE_JOINT_BOND_CLEARANCE
#     gap for structural adhesive. The chamber's bass-end bulge extends
#     below Y_TOP_OF_BASE in the loft, but is clipped at this plane and
#     the open bottom is closed off by the base part below.
#   - BASE: a discrete structural part (CF or, vendor's call, an
#     alternative material such as machined aluminum). Its top face sits
#     at y = Y_TOP_OF_BASE. From that face a TONGUE rises UP by
#     BASE_JOINT_TONGUE_HEIGHT into the chamber's groove, following the
#     chamber rim's lens shape in plan view. A solid plug extends upward
#     by BASE_PLUG_DEPTH into the chamber interior. The body extends
#     DOWN to FLOOR_Y, contacts the floor, and contains a column socket
#     that receives the column's bottom end.
#   - EXTERNAL SEAM: at y = Y_TOP_OF_BASE, hidden by a chamfer of depth
#     BASE_JOINT_CHAMFER on both parts' exterior edges. Reads as a
#     design feature, not a gap.
#   - FASTENING: M4 or M5 cap screws enter from BELOW the instrument
#     (the underside of the base), pass through base through-holes, and
#     thread UP into threaded inserts molded into the chamber's bottom
#     rim. Fasteners are invisible in normal use.
BASE_JOINT_STYLE           = "tongue_groove"  # see header notes
BASE_JOINT_TONGUE_HEIGHT   = 8.0    # mm, tongue rises this far above Y_TOP_OF_BASE (part of base)
BASE_JOINT_TONGUE_THICK    = 2.0    # mm, tongue wall thickness
BASE_JOINT_BOND_CLEARANCE  = 0.15   # mm, groove-vs-tongue gap for adhesive
BASE_JOINT_CHAMFER         = 1.0    # mm, external chamfer at seam
BASE_PLUG_DEPTH            = 20.0   # mm, solid base plug extends this far above Y_TOP_OF_BASE into the chamber


# --- Column bend (gentle arc from base to neck) --------------------------
# The column's centerline follows a circular arc in the x-y plane.
#
# - Midpoint at y = y_mid = (NT.y + CO.y)/2 is unchanged (x = 32.2),
#   preserving C1 string clearance at the middle.
# - Arc is tangent to vertical at y_mid; the ends (top near neck, bottom
#   near base) curve in the direction set by COLUMN_BEND_DIRECTION.
# - COLUMN_BEND_DIRECTION = +1: ends bow TOWARD the strings (+x). The
#   waist of the column sits at the middle (original position); ends
#   flare inward toward the string band. Classical Erard-style shape.
# - COLUMN_BEND_DIRECTION = -1: ends bow AWAY from the strings (-x).
#   The column bulges outward at the waist.
# - Gentle curvature: COLUMN_BEND_RADIUS = 10000 mm gives ~34 mm shift
#   at NT and at y = CO.
# - The neck outline's leg 3 (NTO -> NBO closure along the column outer
#   face) follows the arc; build_harp.py / optimize_v2.py / build_views.py
#   all read column_outer_x(y) / column_inner_x(y) for leg 3 geometry.
#
# Set COLUMN_BEND_ENABLED = False to revert to a straight column.
#
# COLUMN_BEND_VERTICAL_Y: the column is bent only for y < this value (above
# this y physically). For y >= this value, the column's outer face is
# vertical, matching the offset at the threshold. Default: Y_TOP_OF_BASE —
# the column is vertical ONLY inside the base (below y = 1803.91, hidden
# from view), so it can slide straight into the base socket during assembly.
# The entire visible portion of the column (from NT at the top down through
# the chamber to the base's top surface) stays curved per the arc below.
COLUMN_BEND_ENABLED    = True
COLUMN_BEND_RADIUS     = 10000.0  # mm, larger = gentler
COLUMN_BEND_DIRECTION  = +1        # +1 = toward strings (Erard-style), -1 = away
COLUMN_BEND_VERTICAL_Y = 1699.49   # where the Ø39 column's east edge first
                                   # touches the soundboard — the top of the
                                   # column-soundboard intersection ellipse.
                                   # Below this y the column drops vertical
                                   # (centerline constant at x=58.47, cylinder
                                   # extent [38.97, 77.97]). The ellipse's
                                   # bottom is at y=1755.32 (west-edge
                                   # crossing); the column straddles the
                                   # soundboard between these two y values.


# --- Soundboard hole for the column --------------------------------------
# The round Ø39 column crosses the soundboard (chamber flat face) at
# y ≈ 1727.40 (center). Since the column axis is vertical and the
# soundboard plane is inclined at 32° from the column axis (58° from
# horizontal), their intersection is an ELLIPSE in the soundboard plane:
#   - minor axis = column diameter = 39 mm (in the z direction)
#   - major axis = 39 / sin(32°) = 73.60 mm (along the soundboard's tilt)
#   - hole center (authoring frame): (60.51, 1727.40)
#   - hole spans y from 1699.49 to 1755.32 on the inner and outer column
#     face crossings of the soundboard
# The chamber's flat face CF part must be CUT by this ellipse — the column
# passes through the hole and the interior of the chamber on its way from
# the visible curved portion down to the vertical portion inside the base.
SOUNDBOARD_COLUMN_HOLE_ENABLED = True
SOUNDBOARD_COLUMN_HOLE_MINOR   = 39.0     # mm, z-direction (= column Ø)
SOUNDBOARD_COLUMN_HOLE_MAJOR   = 73.60    # mm, soundboard-tilt direction
SOUNDBOARD_COLUMN_HOLE_Y       = 1727.40  # center y in authoring frame


# ============================================================================
# --- DERIVED QUANTITIES (do not edit) ---
# ============================================================================

# Scaled scalars ---------------------------------------------------------
L_CO_ST         = L_CO_ST_BASE * SCALE_FACTOR
S_CI_OFFSET     = S_CI_OFFSET_BASE * SCALE_FACTOR
FLOOR_Y         = FLOOR_Y_BASE * SCALE_FACTOR     # left unscaled in xy frame
COLUMN_Z_HALF   = COLUMN_Z_HALF_BASE * SCALE_FACTOR

D_PEAK          = D_PEAK_BASE * SCALE_FACTOR
S_PEAK          = S_PEAK_BASE * SCALE_FACTOR
S_BASS_FINAL    = S_BASS_FINAL_BASE * SCALE_FACTOR
S_TREBLE_FINAL  = S_TREBLE_FINAL_BASE * SCALE_FACTOR
S_BASS_CLEAR    = S_BASS_CLEAR_BASE * SCALE_FACTOR
S_TREBLE_CLEAR  = S_TREBLE_CLEAR_BASE * SCALE_FACTOR


# Reference points -------------------------------------------------------
# All xy points are scaled about the origin by SCALE_FACTOR.
def _scale_xy(p):
    return (p[0] * SCALE_FACTOR, p[1] * SCALE_FACTOR)

CO = _scale_xy(CO_XY)
NB = _scale_xy(NB_XY_BASE)
NT = _scale_xy(NT_XY_BASE)


# Soundboard axis unit vectors (dimensionless; unaffected by SCALE_FACTOR)
_theta_axis = math.radians(SOUNDBOARD_ANGLE_FROM_HORIZONTAL_DEG)
# u points up and to the right; dy negative in SVG convention.
u = (math.cos(_theta_axis), -math.sin(_theta_axis))
n = (-u[1], u[0])

# Preserve the historical (0.5299, -0.8480) exactly (the 58 deg figure is
# nominal; the actual axis was computed from (ST - CO) in the extraction).
# Override with the exact extraction-derived unit vector so the current
# 47-string config reproduces to sub-micron precision.
_EXACT_U_BASE = (
    (838.784 - CO_XY[0]) / L_CO_ST_BASE,
    (481.939 - CO_XY[1]) / L_CO_ST_BASE,
)
u = _EXACT_U_BASE
n = (-u[1], u[0])


# ST and CI derived from CO + soundboard axis ---------------------------
ST = (CO[0] + L_CO_ST * u[0], CO[1] + L_CO_ST * u[1])
CI = (CO[0] + S_CI_OFFSET * u[0], CO[1] + S_CI_OFFSET * u[1])

COLUMN_OUTER_X  = CO[0]
COLUMN_INNER_X  = COLUMN_INNER_X_BASE * SCALE_FACTOR
COLUMN_WIDTH    = COLUMN_INNER_X - COLUMN_OUTER_X

Y_ST_HORIZ      = ST[1]
Y_TOP_OF_BASE   = Y_TOP_OF_BASE_BASE * SCALE_FACTOR

# Redundant soundboard angle (vertical complement).
SOUNDBOARD_ANGLE_FROM_VERTICAL_DEG = 90.0 - SOUNDBOARD_ANGLE_FROM_HORIZONTAL_DEG


# ----------------------------------------------------------------------------
# Column bend (derived helpers)
# ----------------------------------------------------------------------------
def _column_bend_y_mid():
    """Y-midpoint of the column-bend arc."""
    return (NT_XY_BASE[1] + CO_XY[1]) / 2  # 975.2365 for the 1901 Erard reference

def _column_bend_offset_with_threshold(y, threshold):
    """Arc offset in x for the bent column, clamped to vertical below threshold."""
    if not COLUMN_BEND_ENABLED:
        return 0.0
    y_eff = y if y < threshold else threshold
    y_mid = _column_bend_y_mid()
    dy = y_eff - y_mid
    R = COLUMN_BEND_RADIUS
    inner = R * R - dy * dy
    if inner <= 0:
        return COLUMN_BEND_DIRECTION * R
    return COLUMN_BEND_DIRECTION * (R - math.sqrt(inner))

def _column_bend_x_offset(y):
    """Default (centerline / legacy) offset — uses COLUMN_BEND_VERTICAL_Y
    as the transition. Kept for downstream callers that don't care about
    the per-face split."""
    threshold = COLUMN_BEND_VERTICAL_Y if COLUMN_BEND_VERTICAL_Y is not None else Y_TOP_OF_BASE
    return _column_bend_offset_with_threshold(y, threshold)

# Per-face vertical thresholds. The Ø39 round column is a cylinder whose
# centerline follows the arc; it crosses the inclined soundboard plane in
# an ellipse whose SIDE-VIEW extremes are at:
#   - y = COLUMN_INNER_VERTICAL_Y (east edge first touches, top of ellipse)
#   - y = COLUMN_OUTER_VERTICAL_Y (west edge last touches, bottom)
# Each face drops to vertical at its own intersection y. Between these two
# y values the column tapers (inner vertical, outer still arcing).
COLUMN_INNER_VERTICAL_Y = 1699.49    # east-face / inner crossing
COLUMN_OUTER_VERTICAL_Y = 1755.32    # west-face / outer crossing

def column_outer_x(y):
    """x of column outer (west) face. Arc above COLUMN_OUTER_VERTICAL_Y,
    vertical below."""
    return COLUMN_OUTER_X + _column_bend_offset_with_threshold(y, COLUMN_OUTER_VERTICAL_Y)

def column_inner_x(y):
    """x of column inner (east) face. Arc above COLUMN_INNER_VERTICAL_Y,
    vertical below."""
    return COLUMN_INNER_X + _column_bend_offset_with_threshold(y, COLUMN_INNER_VERTICAL_Y)

def column_centerline_x(y):
    """x of column centerline. Uses the default (legacy) threshold —
    between the two face thresholds the centerline is not strictly
    midway between outer and inner (column tapers in that band)."""
    return (COLUMN_OUTER_X + COLUMN_INNER_X) / 2 + _column_bend_x_offset(y)


# Column-bend-aware neck anchors (downstream code should migrate to
# these once the bend is adopted; existing NT and NB are kept for
# backwards compat and assume a straight column).
NT_BENT = (column_outer_x(NT_XY_BASE[1]), NT_XY_BASE[1])
NB_BENT = (column_outer_x(NB_XY_BASE[1]), NB_XY_BASE[1])


# ----------------------------------------------------------------------------
# Limacon cross-section taper (functions)
# ----------------------------------------------------------------------------
def D_of(sp):
    """Limacon max perpendicular width at station sp (mm along soundboard from CO)."""
    if sp <= S_BASS_FINAL:
        return 0.0
    if sp <= S_PEAK:
        t = (sp - S_BASS_FINAL) / (S_PEAK - S_BASS_FINAL)
        return D_PEAK * (1 - math.cos(math.pi * t)) / 2
    if sp >= S_TREBLE_FINAL:
        return 0.0
    t = (sp - S_PEAK) / (S_TREBLE_FINAL - S_PEAK)
    return D_PEAK * (1 + math.cos(math.pi * t)) / 2


def b_of(sp):
    """Limacon b parameter at station sp (b = D/4.404)."""
    return D_of(sp) / 4.404


def a_of(sp):
    """Limacon a parameter at station sp (a = 2b)."""
    return 2 * b_of(sp)


def centerline_point(sp):
    """Point on the flat face / grommet / soundboard line at station sp.

    This is NOT the limacon's polar origin. It is the grommet line point.
    The limacon's polar origin is offset by +b(sp) in the +n direction.
    """
    return (CO[0] + sp * u[0], CO[1] + sp * u[1])


def limacon_3d(sp, theta):
    """3D point on the limacon surface at station sp and local angle theta.

    theta=0    -> bulge tip
    theta=pi   -> flat face (on grommet line)
    theta=pi/2 -> widest in +z
    theta=3pi/2-> widest in -z

    The cross-section plane is perpendicular to u_hat. Local coordinates in
    that plane are (n_local, z_local) where n_local = 0 at the flat face
    and n_local = 4b at the bulge tip.
    """
    b = b_of(sp)
    a = 2 * b
    r = a + b * math.cos(theta)
    n_local = r * math.cos(theta) + b   # 0 at flat face, 4b at bulge tip
    z_local = r * math.sin(theta)
    flat_x = CO[0] + sp * u[0]
    flat_y = CO[1] + sp * u[1]
    x = flat_x + n_local * n[0]
    y = flat_y + n_local * n[1]
    z = z_local
    return (x, y, z)


def flat_face_point(sp):
    """Point on the flat face = centerline_point (convenience alias)."""
    return centerline_point(sp)


def bulge_tip_point(sp):
    """Point at the bulge tip (deepest into chamber) at station sp."""
    b = b_of(sp)
    flat = centerline_point(sp)
    return (flat[0] + 4 * b * n[0], flat[1] + 4 * b * n[1], 0.0)


# ----------------------------------------------------------------------------
# Clipping planes - used by FreeCAD booleans
# ----------------------------------------------------------------------------
# Bass end: subtract everything at y > FLOOR_Y (i.e., below floor physically)
# Treble end: for x > ~840 mm (past ST), subtract everything at y < Y_ST_HORIZ
# Top of base: base block top surface is horizontal at y = Y_TOP_OF_BASE
# Column: rectangular prism at x in [12.7, 51.7], z in [-19.5, 19.5],
#         from some top y down to FLOOR_Y


# ----------------------------------------------------------------------------
# Grommets - STRING_COUNT string attachment points
# ----------------------------------------------------------------------------
# Note names: diatonic C-major sequence (C, D, E, F, G, A, B) across octaves,
# starting at PITCH_RANGE_LO. _NOTE_ORDER indexes into this scale.
_NOTE_ORDER = ("C", "D", "E", "F", "G", "A", "B")


def _parse_pitch(name):
    """'C1' -> (note_index=0, octave=1); 'G7' -> (4, 7)."""
    note = name[0]
    octave = int(name[1:])
    return _NOTE_ORDER.index(note), octave


def _pitch_to_scale_index(name):
    """Convert scientific pitch to a linear index in the diatonic scale.

    C1 -> 0, D1 -> 1, ..., B1 -> 6, C2 -> 7, ...
    """
    ni, oct_ = _parse_pitch(name)
    return (oct_ - 1) * 7 + ni


def note_of(string_index):
    """Scientific-pitch name for the 1-indexed string number.

    string_index=1 -> PITCH_RANGE_LO; subsequent strings step up the
    diatonic scale. For the default config: 1->C1, 2->D1, ..., 47->G7.
    """
    if not 1 <= string_index <= STRING_COUNT:
        raise IndexError(f"string_index {string_index} out of range [1, {STRING_COUNT}]")
    base_idx = _pitch_to_scale_index(PITCH_RANGE_LO)
    idx = base_idx + (string_index - 1)
    octave = idx // 7 + 1
    note = _NOTE_ORDER[idx % 7]
    return f"{note}{octave}"


# Sanity check: the stated PITCH_RANGE_HI must land on the last string.
assert note_of(STRING_COUNT) == PITCH_RANGE_HI, (
    f"Configured STRING_COUNT/PITCH_RANGE_* inconsistent: "
    f"note_of({STRING_COUNT}) = {note_of(STRING_COUNT)} but "
    f"PITCH_RANGE_HI = {PITCH_RANGE_HI}"
)


# --- Populate the residuals table from the original 1901 s' values -------
# The piecewise-constant tier model introduces up to ~0.065 mm drift per
# string relative to the Erard drawing values. We store per-string residuals
# to pin the 47-string configuration to its original measurements. These
# residuals are zero for a clean re-design from the tiers alone.
_ORIGINAL_SP_47 = [
    167.943,  201.786,  235.629,  269.486,  303.351,  337.194,  371.038,
    404.881,  438.738,  472.581,  506.446,  540.289,  573.175,  606.038,
    638.923,  671.808,  702.754,  733.723,  764.655,  793.684,  822.679,
    851.694,  880.724,  909.739,  938.735,  967.750,  994.828, 1021.905,
    1048.982, 1076.060, 1103.137, 1130.215, 1157.293, 1182.452, 1207.599,
    1232.738, 1257.899, 1283.025, 1308.185, 1333.332, 1358.470, 1383.631,
    1408.757, 1433.917, 1459.042, 1484.202, 1509.341,
]


def _grommet_sp_base(string_index):
    """Unscaled s' (mm along soundboard from CO) for a 1-indexed string.

    Derived from S_PRIME_FIRST_BASE + tier pitches + per-string residual.
    """
    if not 1 <= string_index <= STRING_COUNT:
        raise IndexError(f"string_index {string_index} out of range")
    sp = S_PRIME_FIRST_BASE
    prev_max = 1
    for max_idx, pitch in GROMMET_PITCH_TIERS:
        if string_index <= prev_max:
            break
        upto = min(string_index, max_idx)
        sp += (upto - prev_max) * pitch
        prev_max = upto
        if string_index <= max_idx:
            break
    return sp + GROMMET_PITCH_RESIDUALS.get(string_index, 0.0)


def grommet_sp(string_index):
    """Scaled s' (mm along soundboard from CO) for a 1-indexed string."""
    return _grommet_sp_base(string_index) * SCALE_FACTOR


# Populate residuals so _grommet_sp_base matches _ORIGINAL_SP_47 exactly
# for the default 47-string configuration. If the user changes STRING_COUNT
# or pitch tiers, this block is a no-op (residuals apply only where the
# tiers were calibrated against real measurements).
if STRING_COUNT == 47 and PITCH_RANGE_LO == "C1" and PITCH_RANGE_HI == "G7":
    for _i in range(1, STRING_COUNT + 1):
        _tier_sp = _grommet_sp_base(_i)   # residuals default to 0
        _measured = _ORIGINAL_SP_47[_i - 1]
        _resid = _measured - _tier_sp
        if abs(_resid) > 1e-6:
            GROMMET_PITCH_RESIDUALS[_i] = _resid


def grommet_s_from_CI(string_index):
    """Scaled s (mm along soundboard from CI) for a 1-indexed string."""
    return grommet_sp(string_index) - S_CI_OFFSET


# Build the GROMMETS table.
# Each tuple: (name, s_from_CI_mm, s_prime_from_CO_mm, (x_mm, y_mm))
# Kept as a tuple-list to match the legacy public API.
GROMMETS = [
    (
        note_of(i),
        grommet_s_from_CI(i),
        grommet_sp(i),
        centerline_point(grommet_sp(i)),
    )
    for i in range(1, STRING_COUNT + 1)
]


# ----------------------------------------------------------------------------
# Quick self-check when run directly
# ----------------------------------------------------------------------------
if __name__ == "__main__":
    print(f"Soundboard length CO to ST: {L_CO_ST:.3f} mm")
    print(f"Unit vector u: {u}")
    print(f"Perpendicular n: {n}")
    print()
    print("Key diameters:")
    for label, sp in [("bass clear", S_BASS_CLEAR), ("CO", 0.0), ("CI", 73.59),
                       ("C1", 167.94), ("peak", S_PEAK), ("G7", 1509.34),
                       ("ST", 1558.86), ("treble clear", S_TREBLE_CLEAR)]:
        print(f"  s'={sp:>8.2f}  D={D_of(sp):>6.2f}  b={b_of(sp):>6.2f}")
    print()
    print("Bulge tip at bass clear should sit below floor:")
    bx, by, bz = bulge_tip_point(S_BASS_CLEAR)
    print(f"  ({bx:.2f}, {by:.2f}, {bz:.2f}) vs floor y={FLOOR_Y}")
    print()
    print("Flat face at bass clear should sit on the floor:")
    fx, fy = flat_face_point(S_BASS_CLEAR)
    print(f"  ({fx:.2f}, {fy:.2f}) vs floor y={FLOOR_Y}")
    print()
    print(f"Grommet count: {len(GROMMETS)} strings")


# ----------------------------------------------------------------------------
# Extended generator path past S_TREBLE_CLEAR (curved shoulder generator)
# ----------------------------------------------------------------------------
# The chamber's limacon taper D_of(s') runs from CO (s'=0) along the straight
# soundboard axis to ST at s' = L_CO_ST = 1558.85, with the chamber proper
# ending at s' = S_TREBLE_CLEAR = 1594.86. Past that the shoulder continues
# the limacon along a CURVED generator path:
#
#   Segment 1: straight soundboard from CO to ST (length L_CO_ST)
#   Segment 2: straight soundboard tangent past ST until tangent-point of fillet
#   Segment 3: fillet arc of radius R_SHOULDER_FILLET, smoothly connecting the
#              soundboard tangent to the F7-G7 south sharp-buffer tangent
#   Segment 4: south sharp-buffer tangent toward the apex where D -> 0
#
# Design decision: treat s_arc (arc length along the FULL extended generator
# from CO) as the parameter passed to D_of. So D_arc(s_arc) = D_of(s_arc),
# which means D goes to 0 at s_arc = S_TREBLE_FINAL = 2002.22. That value
# fixes the apex of the generator path on the south tangent.

def _build_extended_generator():
    """Compute the geometric primitives of the extended generator path.

    Returns a dict with keys: u, ST, d_s, n_s, P, theta, tp_dist,
    arc_entry, arc_exit, arc_center, arc_angle, arc_dir, t_sb_ext,
    sum_seg123, south_tangent_length, apex, total_length, F7sb, G7sb.
    """
    # Local import to avoid a build_harp <-> geometry import cycle when
    # geometry.py is imported from inside build_harp's module load. Also
    # ensure the project root is on sys.path so build_harp is importable
    # whether geometry.py is run directly (`python3 soundbox/geometry.py`,
    # which puts only `soundbox/` on sys.path) or imported as a submodule.
    import os as _os
    import sys as _sys
    _proj_root = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
    if _proj_root not in _sys.path:
        _sys.path.insert(0, _proj_root)
    import build_harp as _bh

    _strings = _bh.build_strings()
    _F7 = next(s for s in _strings if s['note'] == 'F7')
    _G7 = next(s for s in _strings if s['note'] == 'G7')
    F7sb = _F7['sharp_buffer']
    G7sb = _G7['sharp_buffer']
    R_buf = _bh.R_BUFFER
    R_fillet = R_SHOULDER_FILLET

    # South tangent direction: unit vector along the F7sb -> G7sb chord.
    _dx, _dy = G7sb[0] - F7sb[0], G7sb[1] - F7sb[1]
    _L = math.hypot(_dx, _dy)
    d_s = (_dx / _L, _dy / _L)
    # Perpendicular with +y component (south side of the chord).
    _n1 = (-d_s[1], d_s[0])
    n_s = _n1 if _n1[1] > 0 else (-_n1[0], -_n1[1])
    # South tangent line passes through F7sb + R_buf * n_s, direction d_s.
    T_south = (F7sb[0] + R_buf * n_s[0], F7sb[1] + R_buf * n_s[1])

    # Intersection P of the south tangent with the soundboard tangent at ST.
    # Solve T_south + s * d_s == ST + t * u for s, t.
    _det = d_s[0] * (-u[1]) - d_s[1] * (-u[0])
    if abs(_det) < 1e-12:
        raise ValueError("south tangent is parallel to soundboard tangent")
    _rhs = (ST[0] - T_south[0], ST[1] - T_south[1])
    _s_param = (_rhs[0] * (-u[1]) - _rhs[1] * (-u[0])) / _det
    P = (T_south[0] + _s_param * d_s[0], T_south[1] + _s_param * d_s[1])

    # Interior angle theta between the two tangent lines.
    _cos_th = max(-1.0, min(1.0, d_s[0] * u[0] + d_s[1] * u[1]))
    theta = math.acos(_cos_th)

    # Tangent-point distance from P along each line.
    tp_dist = R_fillet / math.tan(theta / 2)

    # Arc-entry point (on soundboard tangent, between ST and P).
    arc_entry = (P[0] - tp_dist * u[0], P[1] - tp_dist * u[1])
    # Arc-exit point (on south tangent, between P and the apex).
    arc_exit = (P[0] - tp_dist * d_s[0], P[1] - tp_dist * d_s[1])

    # Arc center along the interior bisector from P. The interior of the V
    # opens away from P in the direction (-u - d_s).
    _bx, _by = -u[0] - d_s[0], -u[1] - d_s[1]
    _bL = math.hypot(_bx, _by)
    bisector = (_bx / _bL, _by / _bL)
    center_dist = R_fillet / math.sin(theta / 2)
    arc_center = (P[0] + center_dist * bisector[0],
                  P[1] + center_dist * bisector[1])

    # Arc swept angle = pi - theta.
    arc_angle = math.pi - theta

    # Direction of arc sweep: rotate (arc_entry - arc_center) toward
    # (arc_exit - arc_center). Sign via the 2D cross product.
    _v1 = (arc_entry[0] - arc_center[0], arc_entry[1] - arc_center[1])
    _v2 = (arc_exit[0] - arc_center[0], arc_exit[1] - arc_center[1])
    _cross = _v1[0] * _v2[1] - _v1[1] * _v2[0]
    arc_dir = +1.0 if _cross > 0 else -1.0   # +1 = CCW, -1 = CW

    # Arc lengths.
    t_sb_ext = math.hypot(arc_entry[0] - ST[0], arc_entry[1] - ST[1])
    L_arc = R_fillet * arc_angle
    sum_seg123 = L_CO_ST + t_sb_ext + L_arc

    # Apex: total generator length is fixed at S_TREBLE_FINAL because that's
    # where D_of reaches 0. Segment 4 length = S_TREBLE_FINAL - sum_seg123.
    south_tangent_length = S_TREBLE_FINAL - sum_seg123
    if south_tangent_length < 0:
        import sys as _sys
        print(f"WARNING: extended generator overshoots: "
              f"sum_seg123 = {sum_seg123:.2f} > S_TREBLE_FINAL = "
              f"{S_TREBLE_FINAL:.2f}", file=_sys.stderr)
    apex = (arc_exit[0] + south_tangent_length * d_s[0],
            arc_exit[1] + south_tangent_length * d_s[1])
    total_length = sum_seg123 + max(0.0, south_tangent_length)

    return {
        'u': u, 'ST': ST,
        'F7sb': F7sb, 'G7sb': G7sb,
        'd_s': d_s, 'n_s': n_s,
        'P': P, 'theta': theta, 'tp_dist': tp_dist,
        'arc_entry': arc_entry, 'arc_exit': arc_exit,
        'arc_center': arc_center, 'arc_angle': arc_angle,
        'arc_dir': arc_dir,
        't_sb_ext': t_sb_ext, 'sum_seg123': sum_seg123,
        'south_tangent_length': south_tangent_length,
        'apex': apex, 'total_length': total_length,
    }


_EXT_GEN = None  # cached at first call


def _ext_gen():
    """Lazy accessor for the extended generator primitives."""
    global _EXT_GEN
    if _EXT_GEN is None:
        _EXT_GEN = _build_extended_generator()
    return _EXT_GEN


def extended_generator_path(s_arc):
    """Return (x, y) on the full 2D generator curve at arc length s_arc from CO.

    Path segments (arc length measured continuously from CO):
      1. s_arc in [0, L_CO_ST]                       -- straight soundboard
      2. s_arc in [L_CO_ST, L_CO_ST + t_sb_ext]      -- soundboard tangent
                                                       extension past ST
      3. s_arc in [..., + R_SHOULDER_FILLET*arc_angle] -- fillet arc
      4. s_arc beyond that                           -- south sharp-buffer
                                                       tangent toward apex

    The apex is the point where D_arc(s_arc) -> 0, i.e. s_arc = S_TREBLE_FINAL.
    """
    G = _ext_gen()
    L1 = L_CO_ST
    L2_end = L1 + G['t_sb_ext']
    L_arc = R_SHOULDER_FILLET * G['arc_angle']
    L3_end = L2_end + L_arc

    if s_arc <= L1:
        return (CO[0] + s_arc * u[0], CO[1] + s_arc * u[1])
    if s_arc <= L2_end:
        t = s_arc - L1
        return (ST[0] + t * u[0], ST[1] + t * u[1])
    if s_arc <= L3_end:
        t = s_arc - L2_end                # arc length into the fillet
        ang = t / R_SHOULDER_FILLET       # rotation about arc_center
        cx, cy = G['arc_center']
        ex, ey = G['arc_entry']
        rx, ry = ex - cx, ey - cy
        # Rotate (rx, ry) by ang in the direction from arc_entry to arc_exit.
        s = G['arc_dir'] * ang
        c, sn = math.cos(s), math.sin(s)
        nx = c * rx - sn * ry
        ny = sn * rx + c * ry
        return (cx + nx, cy + ny)
    # Segment 4: south tangent from arc_exit toward apex.
    t = s_arc - L3_end
    return (G['arc_exit'][0] + t * G['d_s'][0],
            G['arc_exit'][1] + t * G['d_s'][1])


def D_arc(s_arc):
    """Limacon max perpendicular width at arc-length station s_arc.

    Semantics: s_arc is arc length along the FULL extended generator path
    from CO (segments 1+2+3+4: straight soundboard, tangent extension,
    fillet arc, south tangent). The taper function D_of() is reused as-is
    -- it already reaches 0 at s' = S_TREBLE_FINAL = 2002.22, which is now
    interpreted as the arc length of the apex. So D_arc(0) = D_of(0) at CO,
    D_arc(S_TREBLE_FINAL) = 0 at the apex on the south tangent.

    The implication is that the chamber's limacon shape (a function of how
    far along the generator we are) continues smoothly past the soundboard's
    end at ST and tapers to zero at the apex of the curved shoulder body.
    """
    return D_of(s_arc)


def slot_mouth_station():
    """Find the arc-length station where D_arc(s_arc) = 16.7 mm.

    16.7 = 12.7 (plate-to-plate gap) + 2 * 2 mm (plate thicknesses) is the
    plate's total z-extent. Where the shoulder's local z-width matches the
    plate's z-width, the plate surface and shoulder surface read as one
    continuous form -- this is the natural place to mouth the slot that
    receives the plate's tang.

    Returns (s_arc, x, y, D) at that station.
    """
    target = 16.7
    # D_arc decreases monotonically from the peak past S_TREBLE_CLEAR down
    # to 0 at S_TREBLE_FINAL. Bisect over the falling branch
    # [S_TREBLE_CLEAR, S_TREBLE_FINAL] for the unique root where D = target.
    lo = S_TREBLE_CLEAR
    hi = S_TREBLE_FINAL
    Dlo = D_arc(lo)
    Dhi = D_arc(hi)
    if Dlo < target:
        raise ValueError(
            f"Plate z-extent {target} > D at S_TREBLE_CLEAR ({Dlo:.2f}); "
            "no slot mouth exists on the falling branch.")
    if Dhi > target:
        raise ValueError(
            f"Plate z-extent {target} < D at apex ({Dhi:.2f}); "
            "unexpected (D should be 0 at apex).")
    for _ in range(120):
        mid = 0.5 * (lo + hi)
        if D_arc(mid) > target:
            lo = mid
        else:
            hi = mid
        if hi - lo < 1e-9:
            break
    s_arc = 0.5 * (lo + hi)
    x, y = extended_generator_path(s_arc)
    return (s_arc, x, y, D_arc(s_arc))


def plate_tang_length(slot_mouth_x):
    """Horizontal distance from BT.x = 906.632 to slot_mouth_x.

    BT is the east end of the plate's ST->BT edge resting on the chamber rim.
    The plate's tang must extend east of BT until it reaches the slot mouth
    in the shoulder body. Returns 0 (with no error) if the slot mouth lies
    west of BT, since in that case the plate's existing ST->BT edge already
    reaches into the shoulder body and no extra tang material is needed.
    """
    BT_X = 906.632
    delta = slot_mouth_x - BT_X
    return delta if delta > 0 else 0.0


# ----------------------------------------------------------------------------
# Self-check for the extended-generator helpers
# ----------------------------------------------------------------------------
if __name__ == "__main__":
    print()
    print("=== Extended generator path ===")
    for sa in [0, L_CO_ST, L_CO_ST + 10, L_CO_ST + 30,
               S_TREBLE_CLEAR, S_TREBLE_CLEAR + 50, S_TREBLE_FINAL]:
        try:
            p = extended_generator_path(sa)
            print(f"  s_arc={sa:.2f}: (x,y) = ({p[0]:.2f}, {p[1]:.2f}), "
                  f"D = {D_arc(sa):.2f}")
        except Exception as e:
            print(f"  s_arc={sa:.2f}: ERROR {e}")
    print()
    print("=== Slot mouth ===")
    sm = slot_mouth_station()
    print(f"  s_arc = {sm[0]:.2f}, (x, y) = ({sm[1]:.2f}, {sm[2]:.2f}), "
          f"D = {sm[3]:.2f}")
    BT_X = 906.632
    print(f"  Plate tang length required past BT.x={BT_X}: "
          f"{plate_tang_length(sm[1]):.2f} mm")
    print()
    G = _ext_gen()
    print("=== Extended-generator primitives ===")
    print(f"  L_CO_ST              = {L_CO_ST:.2f}")
    print(f"  Soundboard ext past ST (t_sb_ext) = {G['t_sb_ext']:.2f}")
    print(f"  Fillet arc length    = "
          f"{R_SHOULDER_FILLET * G['arc_angle']:.2f}  "
          f"(R={R_SHOULDER_FILLET}, angle={math.degrees(G['arc_angle']):.2f} deg)")
    print(f"  Sum segments 1+2+3   = {G['sum_seg123']:.2f}")
    print(f"  South-tangent length = {G['south_tangent_length']:.2f}")
    print(f"  Total generator len  = {G['total_length']:.2f}")
    print(f"  Apex (x, y)          = ({G['apex'][0]:.2f}, {G['apex'][1]:.2f})")

    print()
    print("=== Column bend ===")
    print(f"  y_mid = {_column_bend_y_mid():.2f}")
    print(f"  column_outer_x(NT.y = {NT_XY_BASE[1]:.2f}) = {column_outer_x(NT_XY_BASE[1]):.3f}")
    print(f"  column_outer_x(y_mid) = {column_outer_x(_column_bend_y_mid()):.3f}")
    print(f"  column_outer_x(NB.y = {NB_XY_BASE[1]:.2f}) = {column_outer_x(NB_XY_BASE[1]):.3f}")
    print(f"  column_outer_x(FLOOR_Y) = {column_outer_x(FLOOR_Y_BASE):.3f}")
    print(f"  NT_BENT = {NT_BENT}")
    print(f"  NB_BENT = {NB_BENT}")
