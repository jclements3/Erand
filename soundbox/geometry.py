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
FLOOR_Y_BASE    = 1870.0               # floor plane. Raised from 1915.5 to 1860
                                       # when pedals were removed; raised again
                                       # to 1870 on 2026-04-24 to fit the
                                       # parabolic scoop (see SCOOP_* below) —
                                       # the scoop's xy-plane rim endpoint sits
                                       # at y = 1858.32, and >= ~12 mm of CF
                                       # below that is needed for wall strength.
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
S_BASS_CLEAR_BASE    = -77.94          # flat face meets FLOOR_Y. The chamber
                                       # is ONE continuous tube extending from
                                       # Y_ST_HORIZ down to FLOOR_Y externally;
                                       # the base is an INTERIOR plug inside
                                       # the chamber's bottom (at Y_TOP_OF_BASE).
                                       # Recompute as (FLOOR_Y - CO.y) / u[1] if
                                       # FLOOR_Y changes. History:
                                       #   -131.59 for FLOOR_Y=1915.5
                                       #    -66.14 for FLOOR_Y=1860
                                       #    -77.94 for FLOOR_Y=1870 (current)
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
H_SHOULDER                     = 40.0   # mm, shoulder body rises this far above
                                        # Y_ST_HORIZ. Raised from 30.0 to 40.0 to
                                        # accommodate stacked shoulder-underside
                                        # features: the broadband spherical
                                        # diffuser (SHOULDER_DIFFUSER_*, 15 mm
                                        # sag) plus the local BT-treble
                                        # paraboloid pocket (TREBLE_SCOOP_*,
                                        # deeper). 40 mm gives enough shoulder
                                        # thickness to host both without
                                        # breaking through the top face.
R_SHOULDER_FILLET              = 5.0    # mm, fillet arc radius at tangent intersection


# --- Shoulder-underside broadband diffuser (concave spherical depression) --
# A shallow spherical cap molded into the underside of the shoulder over the
# ST-BT rim region. The sphere's center sits ABOVE Y_ST_HORIZ (smaller y, i.e.
# INSIDE the shoulder body); its lower surface dips below Y_ST_HORIZ into the
# chamber air space by SHOULDER_DIFFUSER_DEPTH at the deepest point. The
# result is a gentle concave pocket that scatters treble radiation toward
# the sound holes without introducing strong resonances -- a broadband
# diffuser, not a focused reflector.
SHOULDER_DIFFUSER_ENABLED             = True
SHOULDER_DIFFUSER_SPHERE_RADIUS_BASE  = 250.0   # mm, sphere radius (large R = gentle curvature)
SHOULDER_DIFFUSER_DEPTH_BASE          = 15.0    # mm, max sag of the pocket at its center
SHOULDER_DIFFUSER_CENTER_XY_BASE      = (872.70, 481.94)   # midpoint of ST-BT in authoring frame


# --- Treble paraboloid scoop (shoulder underside, aimed at treble hole) --
# A parabolic scoop cut INTO the shoulder's underside, concave side facing
# the treble sound hole. Treble analog of the base scoop, but anchored at
# BT (not at a rim midpoint): BT is the only anchor whose perpendicular foot
# keeps the rim chord inside [ST.x, BT.x] in the xy side view.
#
# Construction rule (identical to the base scoop):
#   given hw = rim endpoint, aim = axis target, rim radius r, depth d:
#     L         = |aim - hw|
#     tilt      = asin(r / L)
#     theta     = atan2(aim.y - hw.y, aim.x - hw.x)
#     axis_theta= theta - tilt
#     axis_u    = (cos(axis_theta), sin(axis_theta))
#     perp      = (-axis_u.y, axis_u.x)             # 90 deg CCW rotation
#     rim_mid   = hw + r * perp                     # perpendicular foot
#     rim_far   = rim_mid + r * perp = hw + 2r*perp
#     vertex    = rim_mid - d * axis_u
#     f         = r**2 / (4 d)
#     focus     = rim_mid + f * axis_u
TREBLE_SCOOP_ENABLED          = True
TREBLE_SCOOP_ANCHOR_MODE      = 'BT'        # rim endpoint hw = BT in xy
TREBLE_SCOOP_AIM_LABEL        = 'treble'    # SOUND_HOLES label to aim at
TREBLE_SCOOP_RIM_RADIUS_BASE  = 30.0        # mm, rim radius (chord = 60 mm)
TREBLE_SCOOP_DEPTH_BASE       = 12.0        # mm, vertex depth below rim chord


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


# --- Parabolic scoop in base top (chamber volume + HF reflector) ---------
# A paraboloid of revolution carved out of the top of the base plug. Adds
# chamber volume (lowers Helmholtz resonance, strengthens bass) and mildly
# collimates high-frequency partials toward the sound-hole cluster. The
# axis of revolution aims from the rim centre toward the hole centroid.
#
# Construction rule: CUT only. Subtract the paraboloid solid from the
# chamber-and-base primitive; no additive boolean fuse on curved surfaces.
#
# Anchor: HW = midpoint of CSB_E (column east edge meets soundboard) and
# C1G (C1 grommet) along the soundboard. HW is ONE rim endpoint (θ=π of
# the rim circle); the xy-plane mirror across the axis is the OTHER rim
# endpoint in the side-view chord. HW must sit EAST of the column-
# soundboard joint (it does, at s' ≈ 145.5 > s'(CSB_E) = 123.1).
#
# Geometric design inputs (authoring frame, unscaled mm). If SCALE_FACTOR
# changes, the scoop scales uniformly with the rest of the harp.
SCOOP_ENABLED            = True
SCOOP_CENTROID_XY_BASE   = (669.12, 1263.30)   # hole cluster aim point
SCOOP_RIM_MID_XY_BASE    = (182.25, 1769.40)   # centre of rim circle
SCOOP_AXIS_U             = (0.6933, -0.7207)   # unit vec, rim_mid -> centroid
SCOOP_RIM_RADIUS_BASE    = 120.75              # mm, rim circle radius
                                               # (shrunk from 128.25 so the
                                               # entire rim fits inside the
                                               # chamber walls; xy margin
                                               # ~2.1 mm to the east-bulge
                                               # curve at RIM_FAR.y and ~18.8
                                               # mm z margin to chamber half-
                                               # width at rim_mid)
SCOOP_DEPTH_BASE         = 60.0                # mm, rim -> vertex along -axis
# Derived quantities (vertex, focus, focal length, generating parabola,
# other rim endpoint) are computed in the DERIVED QUANTITIES section.


# --- Sound holes on east bulge wall --------------------------------------
# Circular holes on the chamber bulge face, centred on the limaçon bulge-
# tip curve at the listed s' stations. Hole axis is local +n at each
# station (perpendicular to the bulge face). Cut as circular cylinders
# through the chamber wall. The treble end carries an enlarged Ø140
# primary hole plus a second smaller Ø75 hole up near the shoulder for
# improved high-frequency radiation.
SOUND_HOLES_BASE = [
    # (label, s_prime_mm, diameter_mm)
    ('bass',    480.0,  130.0),
    ('mid',     850.0,  115.0),
    ('treble', 1300.0,  140.0),
    ('treble2', 1475.0,  75.0),
]


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


# --- Shoulder diffuser derived quantities -------------------------------
# Scaled versions of the SHOULDER_DIFFUSER_* DESIGN PARAMETERS above.
# Linear distances scale by SCALE_FACTOR; the center xy scales via _scale_xy.
SHOULDER_DIFFUSER_CENTER_XY    = _scale_xy(SHOULDER_DIFFUSER_CENTER_XY_BASE)
SHOULDER_DIFFUSER_SPHERE_RADIUS = SHOULDER_DIFFUSER_SPHERE_RADIUS_BASE * SCALE_FACTOR
SHOULDER_DIFFUSER_DEPTH        = SHOULDER_DIFFUSER_DEPTH_BASE * SCALE_FACTOR


def shoulder_diffuser_arc_xy(n_samples=60):
    """Sample the z=0 cross-section of the shoulder-underside spherical
    depression.

    Geometry: the diffuser is a spherical cap molded into the shoulder's
    underside. The pocket is carved UP into the shoulder material from
    the rim plane y = Y_ST_HORIZ; max sag (deepest point of the pocket)
    is `depth` above the rim plane (SMALLER y in authoring frame).

    Sphere center in 3D is BELOW the rim plane (larger y) so that the
    sphere's upper cap pokes UP through the rim plane by `depth` at its
    apex, forming the concave pocket:
        C = (cx, cy + (R - depth), 0)
    where (cx, cy) = SHOULDER_DIFFUSER_CENTER_XY with cy = Y_ST_HORIZ.
    The sphere's equation is
        (x - cx)^2 + (y - (cy + (R - depth)))^2 + z^2 = R^2.
    At z = 0 this reduces to a circle of radius R in the xy plane. The
    upper cap of this circle (from the west rim crossing, through the
    pocket apex at (cx, cy - depth), to the east rim crossing) is the
    z=0 cross-section of the depression.

    Parametrize by angle theta from the upward-pointing bisector (into
    the shoulder). At theta = 0 we are at the pocket apex
    (cx, cy - depth); at theta = +/- theta_edge we exit through the rim
    plane y = cy.

    Rim half-width (distance from cx to the rim crossings):
        a = sqrt(R^2 - (R - depth)^2) = sqrt(2*R*depth - depth^2)
    At R = 250 mm, depth = 15 mm this is a ~= 85.29 mm, so the diffuser
    footprint on the rim spans x in [cx - 85.29, cx + 85.29] -- wider
    than the ST-BT span (838.78..906.63, 67.85 mm wide). The pocket's
    footprint therefore extends a little past ST to the west and a
    little past BT to the east; downstream mold/loft code is expected
    to clip it to the actual shoulder-underside footprint.

    Returns a list of (x, y) points sampling this z=0 arc from the
    western rim crossing (smaller x, y = Y_ST_HORIZ) through the pocket
    apex (y = Y_ST_HORIZ - depth) to the eastern rim crossing (larger
    x, y = Y_ST_HORIZ).
    """
    cx, cy = SHOULDER_DIFFUSER_CENTER_XY
    R = SHOULDER_DIFFUSER_SPHERE_RADIUS
    depth = SHOULDER_DIFFUSER_DEPTH
    # Sphere-center y in xy (center sits BELOW the rim plane so the upper
    # cap pokes UP through the rim by `depth` at its apex).
    dc_y = cy + (R - depth)
    # Half-angle at which the upper cap exits the rim plane y = cy:
    # cos(theta_edge) = (R - depth) / R (distance from center to rim
    # divided by radius). Clamp defensively if R < depth (degenerate).
    cos_edge = max(-1.0, min(1.0, (R - depth) / R))
    theta_edge = math.acos(cos_edge)
    pts = []
    for k in range(n_samples + 1):
        t = k / n_samples
        # Sweep from -theta_edge (west rim crossing) through 0 (apex,
        # deepest into shoulder) to +theta_edge (east rim crossing).
        theta = -theta_edge + 2.0 * theta_edge * t
        x = cx + R * math.sin(theta)
        y = dc_y - R * math.cos(theta)   # y grows down; apex is at y = cy - depth
        pts.append((x, y))
    return pts


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


# Scaled scalars for the treble paraboloid scoop (see derivation block after
# bulge_tip_point() is defined — the derivation needs to call bulge_tip_point
# to locate BT, and bulge_tip_point depends on the limacon taper helpers
# defined further down).
TREBLE_SCOOP_RIM_RADIUS = TREBLE_SCOOP_RIM_RADIUS_BASE * SCALE_FACTOR
TREBLE_SCOOP_DEPTH      = TREBLE_SCOOP_DEPTH_BASE * SCALE_FACTOR


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
# Sound holes (derived)
# ----------------------------------------------------------------------------
# Each hole is centred on bulge_tip_point(s' * SCALE_FACTOR); diameter scales
# with SCALE_FACTOR. In 3D the hole axis is local +n at the bulge face. In
# side view (xy slice) the hole shows as a circle of the given diameter
# centred at its bulge-tip point.
SOUND_HOLES = [
    {
        'label':    lbl,
        's_prime':  sp * SCALE_FACTOR,
        'diameter': dia * SCALE_FACTOR,
        'center_xy': tuple(bulge_tip_point(sp * SCALE_FACTOR))[:2],
    }
    for (lbl, sp, dia) in SOUND_HOLES_BASE
]


# ----------------------------------------------------------------------------
# Treble paraboloid scoop (derived geometry)
# ----------------------------------------------------------------------------
# Apply the construction rule documented in the DESIGN PARAMETERS block.
# Anchor hw = BT (east end of the bulge-tip locus at y = Y_ST_HORIZ);
# aim = center of the SOUND_HOLES entry whose label == TREBLE_SCOOP_AIM_LABEL.
def _find_bt_xy():
    """BT = east end of bulge-tip locus at y = Y_ST_HORIZ (xy authoring frame).

    Binary search s' over [S_PEAK, S_TREBLE_FINAL] for bulge_tip_y == ST.y.
    Same trick as build_views.py's `_find_bt()`; kept here so downstream
    callers that need BT in 2D can import it directly from geometry without
    reaching into build_views.
    """
    target_y = ST[1]
    lo, hi = S_PEAK, S_TREBLE_FINAL
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if bulge_tip_point(mid)[1] < target_y:
            hi = mid
        else:
            lo = mid
        if hi - lo < 1e-9:
            break
    tip = bulge_tip_point(0.5 * (lo + hi))
    return (tip[0], tip[1])


def _sound_hole_center(label):
    """SOUND_HOLES is a list of dicts with keys label/center_xy/diameter
    (already scaled). Return center_xy for the matching label."""
    for h in SOUND_HOLES:
        if h['label'] == label:
            return h['center_xy']
    raise ValueError(
        f"SOUND_HOLES has no entry with label {label!r}; "
        f"available = {[h['label'] for h in SOUND_HOLES]}")


TREBLE_SCOOP_HW     = _find_bt_xy()                # rim endpoint = BT (xy)
TREBLE_SCOOP_AIM_XY = _sound_hole_center(TREBLE_SCOOP_AIM_LABEL)


def _treble_scoop_build():
    """Apply the construction rule. Returns a dict of derived geometry."""
    hw = TREBLE_SCOOP_HW
    aim = TREBLE_SCOOP_AIM_XY
    r = TREBLE_SCOOP_RIM_RADIUS
    d = TREBLE_SCOOP_DEPTH
    dx = aim[0] - hw[0]
    dy = aim[1] - hw[1]
    L = math.hypot(dx, dy)
    if L <= r:
        raise ValueError(
            f"TREBLE_SCOOP: |aim - hw| = {L:.3f} mm must exceed rim radius "
            f"r = {r:.3f} mm (else asin(r/L) is undefined).")
    tilt = math.asin(r / L)
    theta = math.atan2(dy, dx)
    axis_theta = theta - tilt
    axis_u = (math.cos(axis_theta), math.sin(axis_theta))
    perp = (-axis_u[1], axis_u[0])           # 90 deg CCW rotation of axis_u
    rim_mid = (hw[0] + r * perp[0], hw[1] + r * perp[1])
    rim_far = (rim_mid[0] + r * perp[0], rim_mid[1] + r * perp[1])
    vertex = (rim_mid[0] - d * axis_u[0], rim_mid[1] - d * axis_u[1])
    f = (r * r) / (4.0 * d)
    focus = (rim_mid[0] + f * axis_u[0], rim_mid[1] + f * axis_u[1])
    return {
        'axis_u': axis_u,
        'perp': perp,
        'rim_mid': rim_mid,
        'rim_far': rim_far,
        'vertex': vertex,
        'focus': focus,
        'focal_length': f,
        'tilt_rad': tilt,
        'tilt_deg': math.degrees(tilt),
    }


_TREBLE_SCOOP = _treble_scoop_build()
TREBLE_SCOOP_AXIS_U       = _TREBLE_SCOOP['axis_u']
TREBLE_SCOOP_PERP         = _TREBLE_SCOOP['perp']
TREBLE_SCOOP_RIM_MID      = _TREBLE_SCOOP['rim_mid']
TREBLE_SCOOP_RIM_FAR      = _TREBLE_SCOOP['rim_far']
TREBLE_SCOOP_VERTEX_XY    = _TREBLE_SCOOP['vertex']
TREBLE_SCOOP_FOCUS_XY     = _TREBLE_SCOOP['focus']
TREBLE_SCOOP_FOCAL_LENGTH = _TREBLE_SCOOP['focal_length']
TREBLE_SCOOP_TILT_DEG     = _TREBLE_SCOOP['tilt_deg']


def treble_scoop_parabola_xy(n_samples=60):
    """Sample the generating parabola of the treble scoop in the xy plane.

    Returns a list of (x, y) points running from the rim endpoint hw = BT,
    through the vertex (deepest point), to the far rim endpoint rim_far.
    n_samples + 1 points are emitted in total.

    The generating parabola has focal length f = r**2 / (4 d), focus at
    TREBLE_SCOOP_FOCUS_XY, axis along +axis_u, vertex at
    TREBLE_SCOOP_VERTEX_XY. Parameterized by the perpendicular coordinate
    v in [-r, +r] along axis_perp (= the rim-chord direction): the curve
    point is vertex + v*perp + (v**2 / (4 f))*axis_u.

    At v = -r the point is the rim endpoint nearest hw (= hw itself, by
    construction); at v = +r it is rim_far; at v = 0 it is vertex.
    """
    r = TREBLE_SCOOP_RIM_RADIUS
    f = TREBLE_SCOOP_FOCAL_LENGTH
    ux, uy = TREBLE_SCOOP_AXIS_U
    px, py = TREBLE_SCOOP_PERP
    vx, vy = TREBLE_SCOOP_VERTEX_XY
    pts = []
    for k in range(n_samples + 1):
        t = k / n_samples
        v = -r + 2 * r * t                 # v in [-r, +r]
        s = (v * v) / (4.0 * f)            # distance from vertex along axis
        x = vx + v * px + s * ux
        y = vy + v * py + s * uy
        pts.append((x, y))
    return pts


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
# Column-soundboard intersection ellipse: endpoints in xy
# ----------------------------------------------------------------------------
# The Ø39 round column crosses the sloped soundboard in an ellipse whose
# side-view (z=0) extremes are CSB_E (east face first touches the soundboard,
# top of ellipse) and CSB_W (west face last touches, bottom). These are the
# named points used as scoop anchors and construction references.
CSB_E = (column_inner_x(COLUMN_INNER_VERTICAL_Y), COLUMN_INNER_VERTICAL_Y)
CSB_W = (column_outer_x(COLUMN_OUTER_VERTICAL_Y), COLUMN_OUTER_VERTICAL_Y)


# ----------------------------------------------------------------------------
# Parabolic scoop (derived)
# ----------------------------------------------------------------------------
# Anchor HW = midpoint of CSB_E and C1G on the soundboard. HW sits east of
# the column-soundboard joint and lies on the rim circle of the paraboloid.
_C1G_XY = GROMMETS[0][3]                       # C1 grommet authoring xy
SCOOP_HW = (
    (CSB_E[0] + _C1G_XY[0]) / 2,
    (CSB_E[1] + _C1G_XY[1]) / 2,
)

SCOOP_CENTROID_XY = _scale_xy(SCOOP_CENTROID_XY_BASE)
SCOOP_RIM_MID_XY  = _scale_xy(SCOOP_RIM_MID_XY_BASE)
SCOOP_RIM_RADIUS  = SCOOP_RIM_RADIUS_BASE * SCALE_FACTOR
SCOOP_DEPTH       = SCOOP_DEPTH_BASE * SCALE_FACTOR

# xy-plane perpendicular to the axis (+90° rotation of axis_u).
_SCOOP_PERP_XY = (-SCOOP_AXIS_U[1], SCOOP_AXIS_U[0])

# Rim endpoints in xy (chord that appears in side view):
#   SCOOP_RIM_HW  = SCOOP_HW  (θ = π on the rim circle)
#   SCOOP_RIM_FAR = the xy mirror of HW across the axis (θ = 0)
SCOOP_RIM_HW  = SCOOP_HW
SCOOP_RIM_FAR = (
    SCOOP_RIM_MID_XY[0] + SCOOP_RIM_RADIUS * _SCOOP_PERP_XY[0],
    SCOOP_RIM_MID_XY[1] + SCOOP_RIM_RADIUS * _SCOOP_PERP_XY[1],
)

# Vertex (deepest point of cup) = rim_mid - depth * axis
SCOOP_VERTEX_XY = (
    SCOOP_RIM_MID_XY[0] - SCOOP_DEPTH * SCOOP_AXIS_U[0],
    SCOOP_RIM_MID_XY[1] - SCOOP_DEPTH * SCOOP_AXIS_U[1],
)

# Focal length f = r² / (4 d)
SCOOP_FOCAL_LENGTH = (SCOOP_RIM_RADIUS ** 2) / (4.0 * SCOOP_DEPTH)

# Focus = rim_mid + f * axis_u  (focal point inside the chamber)
SCOOP_FOCUS_XY = (
    SCOOP_RIM_MID_XY[0] + SCOOP_FOCAL_LENGTH * SCOOP_AXIS_U[0],
    SCOOP_RIM_MID_XY[1] + SCOOP_FOCAL_LENGTH * SCOOP_AXIS_U[1],
)


def scoop_parabola_xy(n_samples=60):
    """Sample the scoop's generating parabola in xy. Returns a list of (x, y)
    points from SCOOP_RIM_HW through SCOOP_VERTEX_XY to SCOOP_RIM_FAR. This
    is the z=0 cross-section of the paraboloid of revolution — useful for
    drawing the scoop silhouette in side view."""
    pts = []
    r = SCOOP_RIM_RADIUS
    f = SCOOP_FOCAL_LENGTH
    vx, vy = SCOOP_VERTEX_XY
    ax, ay = SCOOP_AXIS_U
    px, py = _SCOOP_PERP_XY
    for i in range(n_samples + 1):
        t = -r + (2.0 * r) * i / n_samples      # perpendicular offset, -r..+r
        axial = t * t / (4.0 * f)                # distance along +axis from vertex
        x = vx + axial * ax + t * px
        y = vy + axial * ay + t * py
        pts.append((x, y))
    return pts


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
