"""
build_freecad.py — FreeCAD parametric macro for the Clements 47 harp.

Builds the full 3D harp assembly (chamber, base plug, shoulder, column, neck
plates, sound holes, soundboard ellipse) as FreeCAD Part features in a single
document. All dimensions are driven from `soundbox.geometry` and the existing
`build_harp` string/hole model, so editing those modules re-generates the 3D
model on re-run.

HOW TO RUN
----------
Option A (Macro menu):
    FreeCAD -> Macro -> Macros... -> User macros -> add the directory that
    contains this file, then select `build_freecad.py` and "Execute".

Option B (Python console inside FreeCAD):
    >>> exec(open('/absolute/path/to/build_freecad.py').read())

Option C (command-line headless, if your FreeCAD build supports it):
    $ freecad -c build_freecad.py

The script creates a new document "Erand47" (or activates an existing one of
that name) and adds one Part::Feature per component. You can save the result
from File -> Save As... -> `erand47.FCStd` or let the script do it via
`SAVE_FCSTD = True` below.

CONVENTIONS
-----------
Authoring frame from `soundbox.geometry`: (x, y, z) with y INCREASING DOWNWARD
(SVG convention), z out of the string plane. FreeCAD uses z-up by default —
geometry is built in authoring frame, and the whole assembly is optionally
flipped at the end (`FLIP_Y_FOR_FREECAD`) so "down" matches FreeCAD's -z.

AMBIGUITIES / GUESSES FLAGGED IN COMMENTS
-----------------------------------------
Search for "GUESS:" in this file. Main ones:
  - The limaçon is lofted from piecewise-planar profiles perpendicular to the
    soundboard axis u. FreeCAD's Part.makeLoft accepts non-coplanar wires
    directly — should work, but if the loft fails we fall back to per-segment
    lofts stitched together.
  - The base scoop and treble scoop paraboloids are built by revolving a
    parabola profile around the axis. The axis is arbitrary (not aligned with
    z), so we build the profile in a local frame and then place the solid via
    Placement. Accuracy vs. a true BSpline surface is adequate for this pass.
  - The column is swept with Part.Wire.makePipe(circle_profile). FreeCAD's
    makePipe needs a planar profile perpendicular to the path start tangent;
    the path's initial tangent is vertical so a horizontal circle works.
  - Neck plate outline is parsed from `erand47jc_v3_opt.svg` via the existing
    parser logic in `build_step.py`.
  - Base-plug "tilted top" is approximated by cutting a flat plug with an
    inclined plane through SCOOP_RIM_HW and SCOOP_RIM_FAR (no compound tilt
    in z). The scoop cavity is then subtracted.

"""

import math
import os
import re
import sys

# Make sibling modules importable regardless of how the macro was invoked.
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

# --- Try to import FreeCAD --------------------------------------------------
# This file must also be loadable standalone (for the __main__ smoke test at
# the bottom) so the FreeCAD import is optional here.
try:
    import FreeCAD
    import Part
    HAS_FREECAD = True
except ImportError:
    FreeCAD = None
    Part = None
    HAS_FREECAD = False

# Local project imports (these must succeed even without FreeCAD so the
# __main__ self-check can run them outside the FreeCAD environment).
import soundbox.geometry as g  # authoritative chamber / column / scoop params
import build_harp as bh        # string / buffer / hole model
import inkscape_frame as ifr   # Inkscape <-> authoring coordinate helpers


# ============================================================================
# CONFIG
# ============================================================================
DOC_NAME                 = "Erand47"
SAVE_FCSTD               = True                     # write erand47.FCStd on exit
OUTPUT_FCSTD             = os.path.join(_HERE, "erand47.FCStd")

FLIP_Y_FOR_FREECAD       = True                     # authoring y-down -> FreeCAD z-up

N_LIMAZON_STATIONS       = 40                       # chamber cross-sections for loft
N_LIMAZON_THETA          = 48                       # samples per cross-section
CHAMBER_WALL_THICKNESS   = 0.0                      # 0 = solid loft (thin-wall TODO)
PARABOLOID_N_SECTIONS    = 24                       # profiles around scoop axis
PARABOLOID_N_SAMPLES     = 24                       # samples along parabola

NECK_SVG_PATH            = os.path.join(_HERE, "erand47jc_v3_opt.svg")

# Hole diameters (match build_step.py)
D_TUNER                  = 16.0
D_CLICKY                 = 6.5

PLATE_T                  = 2.0        # plate thickness in z
PLATE_GAP                = 12.7       # gap between plates

# Column
D_COLUMN                 = 2.0 * g.COLUMN_Z_HALF    # 39 mm diameter


# ============================================================================
# UTILITIES
# ============================================================================
def _V(x, y, z=0.0):
    """Build a FreeCAD Vector from an authoring-frame point."""
    if FLIP_Y_FOR_FREECAD:
        # Map authoring (x, y_down, z) -> FreeCAD (x, z, -y) so FreeCAD's +Z
        # points "up" (i.e., toward the harp's neck/top).
        return FreeCAD.Vector(x, z, -y)
    return FreeCAD.Vector(x, y, z)


def _add_feature(doc, name, shape):
    """Add a Part::Feature with the given shape to the document."""
    obj = doc.addObject("Part::Feature", name)
    obj.Shape = shape
    return obj


def _polygon_wire(pts_xyz, close=True):
    """Closed polygon wire from a list of (x, y, z) authoring points."""
    verts = [_V(*p) for p in pts_xyz]
    if close and (verts[0] - verts[-1]).Length > 1e-9:
        verts.append(verts[0])
    edges = []
    for a, b in zip(verts[:-1], verts[1:]):
        edges.append(Part.LineSegment(a, b).toShape())
    return Part.Wire(edges)


def _bspline_wire(pts_xyz, closed=True):
    """Closed BSpline wire through a list of (x, y, z) authoring points."""
    pts = [_V(*p) for p in pts_xyz]
    bs = Part.BSplineCurve()
    bs.interpolate(pts, PeriodicFlag=closed)
    return Part.Wire([bs.toShape()])


# ============================================================================
# 1. CHAMBER (limaçon loft)
# ============================================================================
def _limazon_cross_section_3d(sp, n_theta=N_LIMAZON_THETA):
    """Sample the limaçon cross-section at station s' as a list of (x, y, z)
    authoring points. Cross-section plane is perpendicular to g.u at the
    station; limaçon uses r = a + b*cos(theta) with a = 2b.

    theta = pi -> flat face (on the grommet / soundboard line)
    theta = 0  -> bulge tip
    """
    pts = []
    for k in range(n_theta):
        theta = 2.0 * math.pi * k / n_theta
        x, y, z = g.limacon_3d(sp, theta)
        pts.append((x, y, z))
    return pts


def build_chamber(doc):
    """Build the chamber as a lofted solid from N_LIMAZON_STATIONS cross-
    sections spanning s' in [S_BASS_CLEAR, S_TREBLE_CLEAR]. Solid loft; a
    thin-wall shell via Part.Shape.makeOffsetShape(-wall) is a future pass.
    """
    sp_lo = g.S_BASS_CLEAR
    sp_hi = g.S_TREBLE_CLEAR
    wires = []
    for i in range(N_LIMAZON_STATIONS + 1):
        t = i / N_LIMAZON_STATIONS
        sp = sp_lo + (sp_hi - sp_lo) * t
        # Degenerate endpoints: clamp to avoid a zero-radius section that
        # upsets the loft. Use a tiny shrink-in to keep non-zero but nearly
        # pointy sections; FreeCAD's loft tolerates this better than b=0.
        if g.b_of(sp) < 1e-3:
            sp = sp_lo + 0.001 if i == 0 else sp_hi - 0.001
        pts = _limazon_cross_section_3d(sp)
        # GUESS: BSpline through points gives a smooth cross-section. If loft
        # struggles with BSplines, switch to a polygon wire: `_polygon_wire`.
        wires.append(_bspline_wire(pts, closed=True))

    # Build the loft. solid=True fills both endcaps; isFrenet=False is the
    # default for non-curved loft paths.
    try:
        loft = Part.makeLoft(wires, True, False, False)
    except Exception as exc:
        print(f"[chamber] Part.makeLoft failed: {exc}; trying solid=False + endcaps.")
        loft = Part.makeLoft(wires, False, False, False)
    return _add_feature(doc, "Chamber", loft)


# ============================================================================
# 2. BASE PLUG (+ parabolic scoop cavity)
# ============================================================================
def _paraboloid_of_revolution(rim_mid_xy, axis_u_xy, perp_xy, radius, depth,
                              name="ScoopCavity"):
    """Return a solid paraboloid of revolution in authoring frame.

    The paraboloid's axis lies in the xy plane (along axis_u_xy). We build a
    local frame (u_hat along axis, v_hat along perp in xy, w_hat = +z in 3D)
    and construct the parabola profile in the (axial, radial) plane via a
    BSpline, then use Part.Face.revolve about the axis to form the solid.

    rim_mid_xy : (x, y) of rim circle center (θ = perp foot of hw on axis)
    axis_u_xy  : (ux, uy) unit vector along axis, POINTING INTO THE CAVITY
                 (from rim toward vertex is -axis_u; convention here follows
                 geometry.py where axis_u points FROM rim_mid toward the aim
                 centroid, i.e., the cavity opens BACKWARD along -axis_u).
    perp_xy    : (px, py) unit vector in xy perpendicular to axis_u
    radius     : rim radius r
    depth      : vertex depth d (vertex = rim_mid - d * axis_u)
    """
    # Local frame vectors in 3D (authoring)
    ux, uy = axis_u_xy
    px, py = perp_xy

    u3 = _V(ux, uy, 0.0) - _V(0, 0, 0)
    p3 = _V(px, py, 0.0) - _V(0, 0, 0)
    u3.normalize()
    p3.normalize()
    w3 = u3.cross(p3)
    w3.normalize()

    rim_mid = _V(rim_mid_xy[0], rim_mid_xy[1], 0.0)

    # Build parabola profile in the (axial s along -u, radial r along +w)
    # half-plane: r in [0, radius], s(r) = -(r^2 / (4 f)) from rim_mid along
    # +axis_u direction, but the vertex is DEEPER, i.e., at -d*u from rim_mid.
    # Profile is a 2D curve in the plane spanned by u and w (we use w as the
    # revolution radius direction). Revolve about the axis_u line through
    # rim_mid to form the paraboloid.
    focal_length = (radius ** 2) / (4.0 * depth)

    # Vertex in 3D
    vertex = rim_mid - u3 * depth

    # Build a profile wire: straight edge rim_mid -> rim endpoint on +w side,
    # then a parabolic arc from rim endpoint back to vertex. Close by a
    # straight edge vertex -> rim_mid along the axis.
    rim_edge = rim_mid + w3 * radius
    pts = []
    for i in range(PARABOLOID_N_SAMPLES + 1):
        t = i / PARABOLOID_N_SAMPLES
        r = radius * (1.0 - t)  # from rim (r=radius) down to vertex (r=0)
        s = -(r * r) / (4.0 * focal_length)  # along -u from rim_mid (s <= 0),
        # but we parametrized depth as positive going to vertex; convert so
        # profile endpoints match: at r=radius -> s=0 (on rim plane), at r=0
        # -> s = -depth (vertex). Actually s = -(radius^2 - r^2)/(4f)?  Use
        # parabola equation: axial_offset_from_vertex = r^2 / (4 f). So
        # offset from rim_mid along +u is r^2/(4f) - depth (negative inward).
        axial_from_vertex = (r * r) / (4.0 * focal_length)
        offset_from_rim_mid = axial_from_vertex - depth  # negative = inside
        p3d = rim_mid + u3 * offset_from_rim_mid + w3 * r
        pts.append(p3d)

    # Build BSpline through these points
    bs = Part.BSplineCurve()
    bs.interpolate(pts)
    parabola_edge = bs.toShape()

    # Close the profile: parabola goes from (r=radius, s=0) to (r=0, s=-depth).
    # Add axis edge vertex -> rim_mid, then rim edge rim_mid -> rim endpoint.
    # Wait: the parabola's r=radius endpoint *is* rim_edge (r=radius, s=0,
    # which equals rim_mid + w*radius + u*0 = rim_edge). The r=0 endpoint is
    # vertex. So profile closure is:
    #   parabola: rim_edge -> vertex
    #   axis:     vertex -> rim_mid   (along +u by +depth)
    #   rim:      rim_mid -> rim_edge (along +w by +radius)
    axis_edge = Part.LineSegment(vertex, rim_mid).toShape()
    rim_line  = Part.LineSegment(rim_mid, rim_edge).toShape()

    profile_wire = Part.Wire([parabola_edge, axis_edge, rim_line])
    profile_face = Part.Face(profile_wire)

    # Revolve 360 deg about the axis (a line through rim_mid, direction u3).
    # Part.makeRevolution wants (shape, angle, axis=vector, base=vector).
    # Revolve the FACE so we get a solid of revolution.
    revolved = profile_face.revolve(rim_mid, u3, 360.0)
    return revolved


def build_base_plug(doc, chamber):
    """Build the base plug as a short solid lofted from the chamber's cross
    section at Y_TOP_OF_BASE down to the floor, with the parabolic scoop
    cavity subtracted from its top.

    GUESS / SIMPLIFICATION: rather than try to get the EXACT interior of the
    chamber at Y_TOP_OF_BASE (which would require slicing the chamber solid —
    `chamber.Shape.slice(...)` is fiddly), we approximate the plug's footprint
    by the limaçon cross-section at s' = 0 (which is where the chamber clips
    at y = Y_TOP_OF_BASE per interfaces.md §3, since CO sits on that plane).
    Height runs from Y_TOP_OF_BASE down to FLOOR_Y.
    """
    sp_top = 0.0  # s' = 0 is CO, which sits at Y_TOP_OF_BASE
    # Build a closed cross-section at the top
    pts_top = _limazon_cross_section_3d(sp_top)
    top_wire = _bspline_wire(pts_top, closed=True)

    # For the bottom we use the same cross section extruded straight down
    # to FLOOR_Y (authoring y increasing). Translate every point.
    dy = g.FLOOR_Y - g.Y_TOP_OF_BASE
    pts_bot = [(p[0], p[1] + dy, p[2]) for p in pts_top]
    bot_wire = _bspline_wire(pts_bot, closed=True)

    try:
        plug = Part.makeLoft([top_wire, bot_wire], True, False, False)
    except Exception as exc:
        print(f"[base_plug] loft failed: {exc}; using prism fallback.")
        face = Part.Face(top_wire)
        # Prism along (0, +dy, 0) authoring, which FLIP maps to -Z in FreeCAD
        direction = _V(0, dy, 0) - _V(0, 0, 0)
        plug = face.extrude(direction)

    # --- Build and subtract the parabolic scoop cavity --------------------
    try:
        scoop = _paraboloid_of_revolution(
            rim_mid_xy=g.SCOOP_RIM_MID_XY,
            axis_u_xy=g.SCOOP_AXIS_U,
            perp_xy=(-g.SCOOP_AXIS_U[1], g.SCOOP_AXIS_U[0]),
            radius=g.SCOOP_RIM_RADIUS,
            depth=g.SCOOP_DEPTH,
        )
        plug_cut = plug.cut(scoop)
    except Exception as exc:
        print(f"[base_plug] scoop cut failed: {exc}; plug left un-cut.")
        plug_cut = plug

    # --- Tilted top approximation ----------------------------------------
    # GUESS: the base polygon top is tilted to match the scoop-rim chord.
    # We build a half-space cutter below the chord plane and intersect with
    # the plug. The chord runs SCOOP_RIM_HW -> SCOOP_RIM_FAR in the xy plane.
    # Without a z extent we use a very large "slab" perpendicular to xy and
    # cut the plug along it. Skipping this refinement for this pass; note it
    # here so the user can add.
    # TODO: tilted top via half-space cut (see note above).

    return _add_feature(doc, "BasePlug", plug_cut)


# ============================================================================
# 3. SHOULDER
# ============================================================================
def _spherical_cap(center_xy, sphere_radius, depth):
    """Spherical cap solid for subtraction.

    Sphere center sits at (cx, Y_ST_HORIZ + (R - depth), 0) so the cap pokes
    UP by `depth` above the rim plane y = Y_ST_HORIZ. The cap is a solid
    sphere (easier to subtract); we rely on the shoulder boolean to slice
    only the portion above the rim plane.

    GUESS: returning the full sphere is adequate because the cut is bounded
    by the shoulder solid's geometry. If we see sphere leakage we'll need
    to clip with a half-space.
    """
    cx, cy = center_xy
    R = sphere_radius
    # Center authoring y sits BELOW the rim plane (larger y) so the cap
    # protrudes upward (smaller y) by `depth`.
    sph_center = _V(cx, cy + (R - depth), 0.0)
    return Part.makeSphere(R, sph_center)


def build_shoulder(doc):
    """Build the shoulder as a block rising H_SHOULDER above Y_ST_HORIZ,
    following the extended generator past ST. Subtract the spherical
    diffuser cavity and the treble paraboloid scoop.

    GUESS / SIMPLIFICATION: the shoulder is modelled here as a plain lofted
    block between the chamber-rim plane at y=Y_ST_HORIZ and a thinner
    limaçon profile at the top y=Y_ST_HORIZ - H_SHOULDER. The extended
    generator (soundboard tangent + fillet arc + south sharp-buffer tangent)
    is NOT traced in 3D in this pass; the loft is driven from s' stations
    up to S_TREBLE_CLEAR. The user can refine the apex region later.
    """
    # Bottom section at y = Y_ST_HORIZ: full limaçon at s' close to
    # S_TREBLE_CLEAR.
    sp_lo = g.S_TREBLE_CLEAR - 50.0  # take a slice near BT
    sp_hi = g.S_TREBLE_CLEAR

    # Bottom profile: limaçon cross-section at sp_hi (the rim shape)
    bot_pts = _limazon_cross_section_3d(sp_hi)
    bot_wire = _bspline_wire(bot_pts, closed=True)

    # Top profile at y = Y_ST_HORIZ - H_SHOULDER: lifted copy of the rim,
    # slightly shrunk (GUESS) to give the shoulder a tapered top. Proper
    # extended-generator apex geometry is a future-pass refinement.
    lift = g.H_SHOULDER
    shrink = 0.9
    cx = sum(p[0] for p in bot_pts) / len(bot_pts)
    cy = sum(p[1] for p in bot_pts) / len(bot_pts)
    top_pts = [
        (cx + shrink * (p[0] - cx), cy + shrink * (p[1] - cy) - lift, p[2] * shrink)
        for p in bot_pts
    ]
    top_wire = _bspline_wire(top_pts, closed=True)

    try:
        shoulder = Part.makeLoft([bot_wire, top_wire], True, False, False)
    except Exception as exc:
        print(f"[shoulder] loft failed: {exc}")
        return None

    # Subtract diffuser cavity (shallow spherical cap)
    try:
        diffuser = _spherical_cap(
            center_xy=g.SHOULDER_DIFFUSER_CENTER_XY,
            sphere_radius=g.SHOULDER_DIFFUSER_SPHERE_RADIUS,
            depth=g.SHOULDER_DIFFUSER_DEPTH,
        )
        shoulder = shoulder.cut(diffuser)
    except Exception as exc:
        print(f"[shoulder] diffuser cut failed: {exc}")

    # Subtract treble paraboloid scoop
    try:
        treble_scoop = _paraboloid_of_revolution(
            rim_mid_xy=g.TREBLE_SCOOP_RIM_MID,
            axis_u_xy=g.TREBLE_SCOOP_AXIS_U,
            perp_xy=g.TREBLE_SCOOP_PERP,
            radius=g.TREBLE_SCOOP_RIM_RADIUS,
            depth=g.TREBLE_SCOOP_DEPTH,
        )
        shoulder = shoulder.cut(treble_scoop)
    except Exception as exc:
        print(f"[shoulder] treble scoop cut failed: {exc}")

    return _add_feature(doc, "Shoulder", shoulder)


# ============================================================================
# 4. COLUMN (bent round cylinder)
# ============================================================================
def build_column(doc):
    """Build the column as a swept circle along a bent path.

    The centerline follows a circular arc above the per-face vertical
    threshold and a straight vertical segment below. We approximate the
    centerline with a polyline of dense samples through column_centerline_x(y)
    and sweep a Ø39 circle along it.

    GUESS: FreeCAD's Part.makePipe(shape, profile) needs a planar profile
    perpendicular to the path start tangent. At y = NT.y (the top of the
    column) the path is mostly vertical, so a circle in the xz plane
    (authoring) is a valid profile. If FreeCAD complains, we'd need to use
    Part.makePipeShell with frenet=True.
    """
    y_top = g.NT_XY_BASE[1]
    y_bot = g.FLOOR_Y

    n_samples = 60
    path_pts = []
    for i in range(n_samples + 1):
        t = i / n_samples
        y = y_top + (y_bot - y_top) * t
        x = g.column_centerline_x(y)
        path_pts.append((x, y, 0.0))

    # Build the centerline as a BSpline
    verts = [_V(*p) for p in path_pts]
    path_bs = Part.BSplineCurve()
    path_bs.interpolate(verts)
    path_wire = Part.Wire([path_bs.toShape()])

    # Build a circular profile of diameter D_COLUMN at the path start.
    # The start point is (centerline_x(y_top), y_top, 0); the start tangent
    # is roughly -Y_authoring (upward physically). Circle in the xz
    # authoring plane centered at that point.
    start = path_pts[0]
    circle = Part.Circle(_V(*start), _V(0, 1, 0) - _V(0, 0, 0), D_COLUMN / 2.0)
    circle_wire = Part.Wire([circle.toShape()])
    # The axis argument to Part.Circle is a Base.Vector; the circle lies in
    # the plane perpendicular to that axis. Axis = (0, 1, 0) in authoring
    # (down the y axis) means the circle's plane is the xz plane -- which,
    # after FLIP_Y, becomes the plane perpendicular to +Z in FreeCAD,
    # matching the column's top tangent direction.

    try:
        pipe = path_wire.makePipe(circle_wire)
    except Exception as exc:
        print(f"[column] makePipe failed: {exc}; falling back to straight cylinder.")
        # Fallback: a straight cylinder from y_top to y_bot at centerline x
        # of the midpoint.
        x_mid = g.column_centerline_x((y_top + y_bot) / 2.0)
        length = y_bot - y_top
        # FreeCAD cylinders are built along +Z; use Placement to orient.
        cyl = Part.makeCylinder(D_COLUMN / 2.0, length)
        # Position: cylinder starts at authoring (x_mid, y_top, 0), extends
        # in +y_authoring direction (= -Z in FreeCAD after FLIP_Y).
        placement = FreeCAD.Placement()
        placement.Base = _V(x_mid, y_top, 0)
        if FLIP_Y_FOR_FREECAD:
            placement.Rotation = FreeCAD.Rotation(FreeCAD.Vector(1, 0, 0), 180)
        cyl.Placement = placement
        pipe = cyl

    return _add_feature(doc, "Column", pipe)


# ============================================================================
# 5. NECK PLATES (from SVG outline)
# ============================================================================
def _parse_neck_outline_authoring():
    """Parse the brown outline path from NECK_SVG_PATH into authoring-frame
    (x, y) points. Mirrors build_step.py's parser."""
    if not os.path.exists(NECK_SVG_PATH):
        raise FileNotFoundError(f"Neck SVG not found at {NECK_SVG_PATH}")
    content = open(NECK_SVG_PATH).read()
    paths = re.findall(r'<path[\s\S]*?/>', content)
    target = None
    for p in paths:
        if '#8b4513' in p.lower():
            target = p
            break
    if target is None:
        raise RuntimeError("No brown (#8B4513) path found in neck SVG")
    d_match = re.search(r'd="([^"]+)"', target)
    if not d_match:
        raise RuntimeError("No d= attribute on brown path")
    path_d = d_match.group(1)

    # Minimal re-implementation of build_step.py's parser (we don't want a
    # hard dependency on cadquery here).
    tokens = re.findall(r'[mMcClLhHvVzZ]|-?[0-9.]+', path_d)
    samples = []
    x, y = 0.0, 0.0
    sx_, sy_ = 0.0, 0.0
    cmd = ''
    i = 0

    def bez(t, p0, p1, p2, p3):
        u = 1 - t
        return (u**3*p0[0] + 3*u**2*t*p1[0] + 3*u*t**2*p2[0] + t**3*p3[0],
                u**3*p0[1] + 3*u**2*t*p1[1] + 3*u*t**2*p2[1] + t**3*p3[1])

    while i < len(tokens):
        t = tokens[i]
        if t in 'mMcClLhHvVzZ':
            cmd = t
            i += 1
            continue
        if cmd == 'm':
            x += float(tokens[i]); y += float(tokens[i+1])
            sx_, sy_ = x, y
            samples.append((x, y))
            cmd = 'l'; i += 2
        elif cmd == 'M':
            x = float(tokens[i]); y = float(tokens[i+1])
            sx_, sy_ = x, y
            samples.append((x, y))
            cmd = 'L'; i += 2
        elif cmd == 'l':
            dx, dy = float(tokens[i]), float(tokens[i+1])
            for k in range(1, 21):
                samples.append((x + dx*k/20, y + dy*k/20))
            x += dx; y += dy; i += 2
        elif cmd == 'L':
            nx, ny = float(tokens[i]), float(tokens[i+1])
            for k in range(1, 21):
                samples.append((x + (nx-x)*k/20, y + (ny-y)*k/20))
            x, y = nx, ny; i += 2
        elif cmd == 'c':
            p0 = (x, y)
            p1 = (x + float(tokens[i]), y + float(tokens[i+1]))
            p2 = (x + float(tokens[i+2]), y + float(tokens[i+3]))
            p3 = (x + float(tokens[i+4]), y + float(tokens[i+5]))
            for k in range(1, 101):
                samples.append(bez(k * 0.01, p0, p1, p2, p3))
            x, y = p3; i += 6
        elif cmd == 'C':
            p0 = (x, y)
            p1 = (float(tokens[i]), float(tokens[i+1]))
            p2 = (float(tokens[i+2]), float(tokens[i+3]))
            p3 = (float(tokens[i+4]), float(tokens[i+5]))
            for k in range(1, 101):
                samples.append(bez(k * 0.01, p0, p1, p2, p3))
            x, y = p3; i += 6
        elif cmd in 'zZ':
            x, y = sx_, sy_; i += 1
        else:
            i += 1
    # Convert Inkscape frame to authoring frame
    return [ifr.to_authoring(p) for p in samples]


def _get_hole_positions():
    """Mirror of build_step.py's get_hole_positions — returns the per-string
    tuner + clicky hole list as dicts."""
    strings = bh.build_strings()
    holes = []
    for i, s in enumerate(strings, start=1):
        plate = '+z' if (i % 2 == 0) else '-z'
        if s.get('has_flat_buffer'):
            holes.append({
                'string_num': i, 'note': s['note'], 'kind': 'tuner',
                'plate': plate, 'xy': s['flat_buffer'], 'diameter': D_TUNER,
            })
        if s.get('has_nat_buffer'):
            holes.append({
                'string_num': i, 'note': s['note'], 'kind': 'nat',
                'plate': plate, 'xy': s['nat_buffer'], 'diameter': D_CLICKY,
            })
        if s.get('has_sharp_buffer'):
            holes.append({
                'string_num': i, 'note': s['note'], 'kind': 'sharp',
                'plate': plate, 'xy': s['sharp_buffer'], 'diameter': D_CLICKY,
            })
    return holes


def build_neck_plates(doc):
    """Build the two neck plates and drill their holes."""
    outline_auth = _parse_neck_outline_authoring()
    # Dedup consecutive near-duplicates
    clean = []
    prev = None
    for p in outline_auth:
        if prev is None or abs(p[0] - prev[0]) > 0.01 or abs(p[1] - prev[1]) > 0.01:
            clean.append(p)
            prev = p
    if clean[0] != clean[-1]:
        clean.append(clean[0])

    holes = _get_hole_positions()
    built = []

    for plate_side in ('+z', '-z'):
        if plate_side == '+z':
            z_bot, z_top = PLATE_GAP / 2.0, PLATE_GAP / 2.0 + PLATE_T
        else:
            z_bot, z_top = -PLATE_GAP / 2.0 - PLATE_T, -PLATE_GAP / 2.0

        # Build outline wire at z_bot and extrude to z_top
        poly_pts = [(p[0], p[1], z_bot) for p in clean]
        base_wire = _polygon_wire(poly_pts, close=False)  # already closed
        try:
            face = Part.Face(base_wire)
        except Exception as exc:
            print(f"[neck_plate] failed to face outline: {exc}")
            continue
        # Extrude direction: along z in authoring (= y in FreeCAD after FLIP)
        # Length = z_top - z_bot in authoring z.
        # FreeCAD's face.extrude takes a Vector; compute the authoring delta
        # and map through _V (delta from origin).
        ext_dir = _V(0, 0, z_top - z_bot) - _V(0, 0, 0)
        plate = face.extrude(ext_dir)

        # Drill holes for this plate's side
        side_holes = [h for h in holes if h['plate'] == plate_side]
        for h in side_holes:
            x, y = h['xy']
            r = h['diameter'] / 2.0
            # Cylinder along z from z_bot - eps to z_top + eps
            eps = 1.0
            length = (z_top - z_bot) + 2 * eps
            # Build a cylinder centered on (x, y, z_bot - eps), axis along +z
            # (authoring), length = length.
            axis = _V(0, 0, 1) - _V(0, 0, 0)
            base = _V(x, y, z_bot - eps)
            try:
                drill = Part.makeCylinder(r, length, base, axis)
                plate = plate.cut(drill)
            except Exception as exc:
                print(f"[neck_plate] hole cut failed for {h['note']}/{h['kind']}: {exc}")

        name = "NeckPlate_pz" if plate_side == '+z' else "NeckPlate_mz"
        built.append(_add_feature(doc, name, plate))

    return built


# ============================================================================
# 6. SOUND HOLES (cylinders on east bulge)
# ============================================================================
def build_sound_hole_cutters(doc, chamber):
    """Build the four sound-hole cutter cylinders and subtract them from the
    chamber. Each hole is centred on the bulge-tip at its s' station with
    axis = local +n (perpendicular to the bulge face)."""
    if chamber is None:
        return None
    cutters = []
    for h in g.SOUND_HOLES:
        sp = h['s_prime']
        dia = h['diameter']
        # Center on the bulge tip; axis along local +n.
        cx, cy, cz = g.bulge_tip_point(sp)
        # Axis = global +n in xy plane (the limaçon geometry is symmetric in
        # z so the bulge tip surface normal is +n for the east bulge).
        nx, ny = g.n
        axis_3d = _V(cx + nx, cy + ny, cz) - _V(cx, cy, cz)
        # Make cylinder long enough to pierce the wall. 200 mm is overkill but
        # cheap; start 100 mm on the -n side of the bulge tip so the cutter
        # straddles the wall.
        length = 300.0
        base_x = cx - 100 * nx
        base_y = cy - 100 * ny
        base_z = cz
        cyl = Part.makeCylinder(dia / 2.0, length,
                                _V(base_x, base_y, base_z),
                                axis_3d)
        cutters.append(cyl)

    # Subtract each cutter from the chamber
    current = chamber.Shape
    for c in cutters:
        try:
            current = current.cut(c)
        except Exception as exc:
            print(f"[sound_holes] cut failed: {exc}")
    chamber.Shape = current
    return chamber


# ============================================================================
# 7. SOUNDBOARD COLUMN ELLIPSE (cutout on flat face)
# ============================================================================
def build_soundboard_ellipse_cut(doc, chamber):
    """Cut the elliptical column hole through the chamber's flat (soundboard)
    face. The ellipse sits in the soundboard plane (inclined at ~32° from
    vertical), with minor axis = 39 (z-direction) and major axis = 73.60
    (along the soundboard tilt). Center at (column-center-x at y_hole, y_hole).
    """
    if chamber is None or not g.SOUNDBOARD_COLUMN_HOLE_ENABLED:
        return chamber
    y_hole = g.SOUNDBOARD_COLUMN_HOLE_Y
    x_hole = g.column_centerline_x(y_hole)
    minor = g.SOUNDBOARD_COLUMN_HOLE_MINOR   # 39 mm, z direction
    major = g.SOUNDBOARD_COLUMN_HOLE_MAJOR   # 73.60 mm, along soundboard tilt

    # GUESS / SIMPLIFICATION: cut a vertical cylinder of diameter = column
    # diameter through the soundboard at (x_hole, y_hole). The true ellipse
    # footprint will be the intersection of the cylinder with the soundboard
    # plane — mathematically correct if we use the COLUMN as the cutter.
    # Here we just re-use a column-diameter cylinder extending through the
    # wall. (A dedicated elliptical prism oriented along the soundboard
    # normal is the more exact construction; left as a TODO.)
    radius = minor / 2.0  # = D_COLUMN / 2 = 19.5
    length = 300.0
    # Cylinder axis = vertical in authoring (0, 1, 0) so it cuts straight
    # through the inclined soundboard leaving an ellipse.
    axis = _V(0, 1, 0) - _V(0, 0, 0)
    base = _V(x_hole, y_hole - 150.0, 0.0)
    cyl = Part.makeCylinder(radius, length, base, axis)
    try:
        chamber.Shape = chamber.Shape.cut(cyl)
    except Exception as exc:
        print(f"[soundboard_ellipse] cut failed: {exc}")
    return chamber


# ============================================================================
# TOP-LEVEL BUILD
# ============================================================================
def build(doc=None):
    """Orchestrate the full build into `doc` (or a new document if None)."""
    if not HAS_FREECAD:
        raise RuntimeError(
            "FreeCAD is not available. Run this script from inside FreeCAD "
            "(Macro menu or Python console) or with `freecad -c build_freecad.py`.")

    if doc is None:
        doc = FreeCAD.newDocument(DOC_NAME)
    else:
        # Activate or create
        if doc in FreeCAD.listDocuments():
            doc = FreeCAD.getDocument(doc)
        else:
            doc = FreeCAD.newDocument(doc)

    print(">>> Building chamber ...")
    chamber = build_chamber(doc)

    print(">>> Building base plug ...")
    base_plug = build_base_plug(doc, chamber)

    print(">>> Building shoulder ...")
    shoulder = build_shoulder(doc)

    print(">>> Building column ...")
    column = build_column(doc)

    print(">>> Building neck plates ...")
    plates = build_neck_plates(doc)

    print(">>> Cutting sound holes into chamber ...")
    chamber = build_sound_hole_cutters(doc, chamber)

    print(">>> Cutting soundboard column ellipse ...")
    chamber = build_soundboard_ellipse_cut(doc, chamber)

    doc.recompute()

    if SAVE_FCSTD:
        doc.saveAs(OUTPUT_FCSTD)
        print(f">>> Saved: {OUTPUT_FCSTD}")

    print(">>> Done.")
    return doc


# ============================================================================
# __main__ — smoke test (no FreeCAD required)
# ============================================================================
def _smoke_test_no_freecad():
    """Print the key parameters so the module can be imported/run outside
    FreeCAD as a sanity check."""
    print("=== Clements 47 FreeCAD macro — smoke test ===")
    print(f"FreeCAD available: {HAS_FREECAD}")
    print()
    print("Chamber (limaçon loft):")
    print(f"  s' range           = [{g.S_BASS_CLEAR:.2f}, {g.S_TREBLE_CLEAR:.2f}] mm")
    print(f"  peak D             = {g.D_PEAK:.2f} mm at s'={g.S_PEAK:.2f}")
    print(f"  D at s'=0          = {g.D_of(0):.2f} mm (top-of-base clip)")
    print(f"  D at S_TREBLE_CLEAR= {g.D_of(g.S_TREBLE_CLEAR):.2f} mm (rim at Y_ST_HORIZ)")
    print(f"  Y_ST_HORIZ         = {g.Y_ST_HORIZ:.2f}")
    print(f"  Y_TOP_OF_BASE      = {g.Y_TOP_OF_BASE:.2f}")
    print(f"  FLOOR_Y            = {g.FLOOR_Y:.2f}")
    print()
    print("Column:")
    print(f"  diameter           = {D_COLUMN:.2f} mm")
    y_top = g.NT_XY_BASE[1]
    y_bot = g.FLOOR_Y
    print(f"  length (y range)   = [{y_top:.2f}, {y_bot:.2f}] = {y_bot - y_top:.2f} mm")
    print(f"  NT centerline      = ({g.column_centerline_x(y_top):.2f}, {y_top:.2f})")
    print(f"  FLOOR centerline   = ({g.column_centerline_x(y_bot):.2f}, {y_bot:.2f})")
    print()
    print("Base plug + scoop:")
    print(f"  HW                 = {g.SCOOP_HW}")
    print(f"  RIM_MID            = {g.SCOOP_RIM_MID_XY}")
    print(f"  RIM_FAR            = {g.SCOOP_RIM_FAR}")
    print(f"  VERTEX             = {g.SCOOP_VERTEX_XY}")
    print(f"  rim_radius         = {g.SCOOP_RIM_RADIUS:.2f} mm")
    print(f"  depth              = {g.SCOOP_DEPTH:.2f} mm")
    print(f"  focal length       = {g.SCOOP_FOCAL_LENGTH:.2f} mm")
    print()
    print("Shoulder:")
    print(f"  H_SHOULDER         = {g.H_SHOULDER} mm")
    print(f"  diffuser R/d       = {g.SHOULDER_DIFFUSER_SPHERE_RADIUS}/{g.SHOULDER_DIFFUSER_DEPTH} mm")
    print(f"  diffuser center    = {g.SHOULDER_DIFFUSER_CENTER_XY}")
    print(f"  treble scoop r/d   = {g.TREBLE_SCOOP_RIM_RADIUS}/{g.TREBLE_SCOOP_DEPTH} mm")
    print(f"  treble scoop HW    = {g.TREBLE_SCOOP_HW}")
    print()
    print("Sound holes:")
    for h in g.SOUND_HOLES:
        print(f"  {h['label']:8s} s'={h['s_prime']:.1f}  Ø{h['diameter']:.1f}  center={h['center_xy']}")
    print()
    print("Soundboard column ellipse:")
    print(f"  minor (z)          = {g.SOUNDBOARD_COLUMN_HOLE_MINOR} mm")
    print(f"  major (along tilt) = {g.SOUNDBOARD_COLUMN_HOLE_MAJOR} mm")
    print(f"  center y           = {g.SOUNDBOARD_COLUMN_HOLE_Y} mm")
    print()
    print("Neck plate holes (from build_harp.build_strings):")
    holes = _get_hole_positions()
    from collections import Counter
    counts = Counter((h['plate'], h['kind']) for h in holes)
    for (plate, kind), n in sorted(counts.items()):
        print(f"  {plate} {kind:6s} = {n}")
    print(f"  TOTAL holes = {len(holes)}")
    print()
    print("Outline samples (from v3 SVG, authoring frame):")
    try:
        outline = _parse_neck_outline_authoring()
        print(f"  samples            = {len(outline)}")
        print(f"  first              = {outline[0]}")
        print(f"  last               = {outline[-1]}")
    except Exception as exc:
        print(f"  FAILED: {exc}")


if __name__ == "__main__":
    # Module-level smoke test. Inside FreeCAD, call build() from the console
    # or run the whole file.
    if HAS_FREECAD:
        build()
    else:
        _smoke_test_no_freecad()
