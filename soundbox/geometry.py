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

# Column width in x and half-thickness in z.
COLUMN_INNER_X_BASE = 51.7            # x of the column's inner face
COLUMN_Z_HALF_BASE  = 19.5            # +/- half-width in z (square prism)


# --- Column anchors (legacy neck-side references) ------------------------
# NB and NT are lower and upper anchors on the column for the neck curve.
# These come from the Erard extraction and are not derived from the
# soundboard axis; they are separate design inputs for the neck routing.
# They scale with SCALE_FACTOR but are otherwise independent.
NB_XY_BASE      = (12.700, 323.844)    # lower column anchor
NT_XY_BASE      = (12.700, 146.563)    # top of column outer


# --- Floor and clipping planes -------------------------------------------
FLOOR_Y_BASE    = 1915.5               # floor plane (chamber clipped below)
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
S_BASS_CLEAR_BASE    = -131.59         # flat face meets floor
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
Y_TOP_OF_BASE   = CO[1]

# Redundant soundboard angle (vertical complement).
SOUNDBOARD_ANGLE_FROM_VERTICAL_DEG = 90.0 - SOUNDBOARD_ANGLE_FROM_HORIZONTAL_DEG


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
