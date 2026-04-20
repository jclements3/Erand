"""
Authoritative geometry for the Clements 47 harp soundbox.

Single source of truth. Neck-design code should import from here rather than
re-deriving or hard-coding any of these numbers.

Coordinate system: millimeters. 2D harp plane is (x, y) with y increasing
downward (SVG convention). Third axis z is perpendicular to that plane.
Chamber is symmetric about z = 0.

Soundboard axis: from CO at the bass end of the extended soundboard slope,
up-right to ST at the neck.
"""

import math


# ----------------------------------------------------------------------------
# Reference points
# ----------------------------------------------------------------------------
CO = (12.700, 1803.910)     # column outer, soundboard slope extended
CI = (51.700, 1741.510)     # column inner, where actual soundboard starts
NT = (12.700,  146.563)     # top of column outer (legacy from project data)
NB = (12.700,  323.844)     # lower column anchor (legacy)
ST = (838.784, 481.939)     # soundboard top, at the neck

COLUMN_OUTER_X = 12.7
COLUMN_INNER_X = 51.7
COLUMN_WIDTH   = 39.0         # in x direction
COLUMN_Z_HALF  = 19.5         # assumed square prism, +/- half-width in z

FLOOR_Y         = 1915.5
Y_ST_HORIZ      = 481.939     # same as ST[1]
Y_TOP_OF_BASE   = 1803.910    # same as CO[1]; horizontal plane through CO


# ----------------------------------------------------------------------------
# Soundboard axis
# ----------------------------------------------------------------------------
L_CO_ST = math.hypot(ST[0] - CO[0], ST[1] - CO[1])    # 1558.858

# unit vectors (x, y) — z component is 0 for both
u = ((ST[0] - CO[0]) / L_CO_ST, (ST[1] - CO[1]) / L_CO_ST)   # (0.5299, -0.8480)
n = (-u[1], u[0])                                             # (0.8480, 0.5299)

# angles
SOUNDBOARD_ANGLE_FROM_HORIZONTAL_DEG = 58.0
SOUNDBOARD_ANGLE_FROM_VERTICAL_DEG   = 32.0


# ----------------------------------------------------------------------------
# Limaçon cross-section taper
# ----------------------------------------------------------------------------
# r(theta) = a + b*cos(theta) with a = 2b   (convex limaçon, no inner loop)
# Flat face at theta=pi (r=b), on the grommet/soundboard line (-n direction).
# Bulge tip at theta=0 (r=3b), into chamber (+n direction).
# Max perpendicular width D = 4.404 * b.
# Axial depth (flat-face to bulge-tip) = 4b.
# Cross-section area A(b) = 0.7289 * D**2 = 14.137 * b**2.

D_PEAK          = 360.0
S_PEAK          = 523.59       # s' where D hits its maximum
S_BASS_FINAL    = -762.87      # where the rising cosine starts from D=0
S_TREBLE_FINAL  = 2002.22      # where the falling cosine reaches D=0

# Loft range to pass to FreeCAD (clean geometry at both clipping planes)
S_BASS_CLEAR    = -131.59      # flat face meets floor; subtract everything below
S_TREBLE_CLEAR  = 1594.86      # bulge tip meets ST horizontal; subtract everything above past ST


def D_of(sp):
    """Limaçon max perpendicular width at station sp (mm along soundboard from CO)."""
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
    """Limaçon b parameter at station sp (b = D/4.404)."""
    return D_of(sp) / 4.404


def a_of(sp):
    """Limaçon a parameter at station sp (a = 2b)."""
    return 2 * b_of(sp)


def centerline_point(sp):
    """Point on the flat face / grommet / soundboard line at station sp.

    This is NOT the limaçon's polar origin. It is the grommet line point.
    The limaçon's polar origin is offset by +b(sp) in the +n direction.
    """
    return (CO[0] + sp * u[0], CO[1] + sp * u[1])


def limacon_3d(sp, theta):
    """3D point on the limaçon surface at station sp and local angle theta.

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
# Clipping planes — used by FreeCAD booleans
# ----------------------------------------------------------------------------
# Bass end: subtract everything at y > FLOOR_Y (i.e., below floor physically)
# Treble end: for x > ~840 mm (past ST), subtract everything at y < Y_ST_HORIZ
# Top of base: base block top surface is horizontal at y = Y_TOP_OF_BASE
# Column: rectangular prism at x in [12.7, 51.7], z in [-19.5, 19.5],
#         from some top y down to FLOOR_Y


# ----------------------------------------------------------------------------
# Grommets — 47 string attachment points
# ----------------------------------------------------------------------------
# Each tuple: (name, s_from_CI_mm, s_prime_from_CO_mm, (x_mm, y_mm))
GROMMETS = [
    ("C1",   94.353,  167.943, (101.700, 1661.495)),
    ("D1",  128.196,  201.786, (119.632, 1632.793)),
    ("E1",  162.039,  235.629, (137.565, 1604.091)),
    ("F1",  195.896,  269.486, (155.523, 1575.389)),
    ("G1",  229.761,  303.351, (173.455, 1546.662)),
    ("A1",  263.604,  337.194, (191.387, 1517.960)),
    ("B1",  297.448,  371.038, (209.320, 1489.258)),
    ("C2",  331.291,  404.881, (227.252, 1460.556)),
    ("D2",  365.148,  438.738, (245.210, 1431.854)),
    ("E2",  398.991,  472.581, (263.142, 1403.152)),
    ("F2",  432.856,  506.446, (281.075, 1374.425)),
    ("G2",  466.699,  540.289, (299.007, 1345.723)),
    ("A2",  499.585,  573.175, (316.432, 1317.833)),
    ("B2",  532.448,  606.038, (333.856, 1289.970)),
    ("C3",  565.333,  638.923, (351.280, 1262.080)),
    ("D3",  598.218,  671.808, (368.705, 1234.191)),
    ("E3",  629.164,  702.754, (385.113, 1207.953)),
    ("F3",  660.133,  733.723, (401.522, 1181.689)),
    ("G3",  691.065,  764.655, (417.905, 1155.451)),
    ("A3",  720.094,  793.684, (433.297, 1130.839)),
    ("B3",  749.089,  822.679, (448.664, 1106.251)),
    ("C4",  778.104,  851.694, (464.031, 1081.639)),
    ("D4",  807.134,  880.724, (479.423, 1057.026)),
    ("E4",  836.149,  909.739, (494.790, 1032.414)),
    ("F4",  865.145,  938.735, (510.157, 1007.826)),
    ("G4",  894.160,  967.750, (525.524,  983.214)),
    ("A4",  921.238,  994.828, (539.875,  960.252)),
    ("B4",  948.315, 1021.905, (554.226,  937.291)),
    ("C5",  975.392, 1048.982, (568.577,  914.329)),
    ("D5", 1002.470, 1076.060, (582.928,  891.367)),
    ("E5", 1029.547, 1103.137, (597.279,  868.406)),
    ("F5", 1056.625, 1130.215, (611.630,  845.444)),
    ("G5", 1083.703, 1157.293, (625.981,  822.482)),
    ("A5", 1108.862, 1182.452, (639.316,  801.147)),
    ("B5", 1134.009, 1207.599, (652.626,  779.811)),
    ("C6", 1159.148, 1232.738, (665.961,  758.500)),
    ("D6", 1184.309, 1257.899, (679.296,  737.164)),
    ("E6", 1209.435, 1283.025, (692.606,  715.853)),
    ("F6", 1234.595, 1308.185, (705.941,  694.517)),
    ("G6", 1259.742, 1333.332, (719.250,  673.181)),
    ("A6", 1284.880, 1358.470, (732.585,  651.871)),
    ("B6", 1310.041, 1383.631, (745.920,  630.535)),
    ("C7", 1335.167, 1408.757, (759.230,  609.224)),
    ("D7", 1360.327, 1433.917, (772.565,  587.888)),
    ("E7", 1385.452, 1459.042, (785.874,  566.578)),
    ("F7", 1410.612, 1484.202, (799.209,  545.242)),
    ("G7", 1435.751, 1509.341, (812.544,  523.931)),
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
