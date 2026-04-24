"""
Sketch of the shoulder geometry with the two-part hidden tongue-and-groove
joint. Three panels:

  (A) Side view (x-y, authoring frame) -- tangent + arc wedge, treble
      buffers, the plate's ST->BT edge, the seam line at Y_ST_HORIZ where
      chamber meets shoulder externally.
  (B) Plan view at y = Y_ST_HORIZ (x-z slice looking down) -- lens-shaped
      chamber opening, annular rim, seam ring, plate footprints in z.
  (C) Joint detail (y-z cross-section, zoomed) -- shows the chamber's
      tongue rising from the rim, the shoulder's matching groove,
      external chamfer, threaded insert, fastener path.

All dimensions pulled from build_harp.py + soundbox.geometry (R_SHOULDER_FILLET,
SHOULDER_JOINT_TONGUE_HEIGHT, SHOULDER_JOINT_TONGUE_THICK, etc.).
"""

import math
import build_harp as bh
import soundbox.geometry as g


WALL_T = 5.0       # chamber wall thickness (mm) -- sketch approximation
PLATE_T = 2.0      # plate thickness in z (mm)
GAP = 12.7         # plate-to-plate gap in z (mm)


def unit(v):
    L = math.hypot(*v)
    return (v[0] / L, v[1] / L)


def intersect(p1, d1, p2, d2):
    det = d1[0] * (-d2[1]) - d1[1] * (-d2[0])
    rhs = (p2[0] - p1[0], p2[1] - p1[1])
    s = (rhs[0] * (-d2[1]) - rhs[1] * (-d2[0])) / det
    t = (d1[0] * rhs[1] - d1[1] * rhs[0]) / det
    return (p1[0] + s * d1[0], p1[1] + s * d1[1]), s, t


def chamber_outer_z(x_target, y_target):
    """Return z on the chamber outer surface at (x_target, y_target), or
    None if no valid solution. Uses bisection over s' (monotonic in x
    at fixed y)."""
    lo, hi = g.S_BASS_CLEAR, g.S_TREBLE_FINAL
    for _ in range(80):
        mid = (lo + hi) / 2
        fx = g.CO[0] + mid * g.u[0]
        fy = g.CO[1] + mid * g.u[1]
        n_local = (y_target - fy) / g.n[1]
        b = g.b_of(mid)
        if b < 1e-6 or n_local < 0:
            lo = mid
            continue
        if n_local > 4 * b:
            hi = mid
            continue
        x_at = fx + n_local * g.n[0]
        if x_at < x_target:
            lo = mid
        else:
            hi = mid
    sp = (lo + hi) / 2
    fx = g.CO[0] + sp * g.u[0]
    fy = g.CO[1] + sp * g.u[1]
    n_local = (y_target - fy) / g.n[1]
    b = g.b_of(sp)
    if b < 1e-6 or n_local < 0 or n_local > 4 * b:
        return None
    c = math.sqrt(n_local / b) - 1
    c = max(-1.0, min(1.0, c))
    r = (2 + c) * b
    theta = math.acos(c)
    return r * math.sin(theta)


def main(R_fillet=None):
    strings = bh.build_strings()
    F7 = next(s for s in strings if s['note'] == 'F7')
    G7 = next(s for s in strings if s['note'] == 'G7')
    R_buf = bh.R_BUFFER
    if R_fillet is None:
        R_fillet = getattr(g, 'R_SHOULDER_FILLET', 5.0)

    F7sb, G7sb = F7['sharp_buffer'], G7['sharp_buffer']
    F7fb, G7fb = F7['flat_buffer'], G7['flat_buffer']
    ST, u = g.ST, g.u
    Y_RIM = g.Y_ST_HORIZ
    BT = (906.632, 481.877)

    TONGUE_H = getattr(g, 'SHOULDER_JOINT_TONGUE_HEIGHT', 8.0)
    TONGUE_T = getattr(g, 'SHOULDER_JOINT_TONGUE_THICK', 2.0)
    CLEAR = getattr(g, 'SHOULDER_JOINT_BOND_CLEARANCE', 0.15)
    CHAMFER = getattr(g, 'SHOULDER_JOINT_CHAMFER', 1.0)

    # Actual limaçon horizontal slice at y = Y_ST_HORIZ, computed from the
    # chamber equations (not an ellipse). Sweep generator s' from ST to the
    # bulge-tip clearance station; for each, find the n_local value that
    # places the point at y=Y_RIM, then compute (x, z) on the cross-section.
    lens_half = []   # list of (x, z) with z >= 0 going from left-point to right-point
    N_LENS = 120
    for i in range(N_LENS + 1):
        sp = g.L_CO_ST + (g.S_TREBLE_CLEAR - g.L_CO_ST) * i / N_LENS
        fx = g.CO[0] + sp * g.u[0]
        fy = g.CO[1] + sp * g.u[1]
        n_local = (Y_RIM - fy) / g.n[1]
        b = g.b_of(sp)
        if b < 1e-6:
            continue
        ratio = n_local / b
        if ratio < 0 or ratio > 4:
            continue
        c = math.sqrt(ratio) - 1
        c = max(-1.0, min(1.0, c))
        r = (2 + c) * b
        th = math.acos(c)
        zpos = r * math.sin(th)
        x = fx + n_local * g.n[0]
        lens_half.append((x, zpos))
    # Full lens outline: left point, upper half (z>=0) going east, right
    # point, lower half (z<=0) going west back to left point.
    lens_outline = list(lens_half) + [(p[0], -p[1]) for p in reversed(lens_half)]
    xs_l = [p[0] for p in lens_outline]
    zs_l = [p[1] for p in lens_outline]
    LENS_X_MIN, LENS_X_MAX = min(xs_l), max(xs_l)
    LENS_Z_HALF = max(zs_l)
    lens_cx = (LENS_X_MIN + LENS_X_MAX) / 2
    lens_rx = (LENS_X_MAX - LENS_X_MIN) / 2
    lens_rz = LENS_Z_HALF

    # Compute an outward-offset outline (seam ring = lens + wall thickness).
    # For each lens point, use the local outward normal (from finite
    # differences along the half-curve) offset by WALL_T.
    def _offset_half(pts, offset):
        out = []
        for i, p in enumerate(pts):
            if i == 0:
                # At the west (left) point: normal points -x.
                nx, nz = -1.0, 0.0
            elif i == len(pts) - 1:
                # At the east (right) point: normal points +x.
                nx, nz = 1.0, 0.0
            else:
                p_prev = pts[i - 1]
                p_next = pts[i + 1]
                dx = p_next[0] - p_prev[0]
                dz = p_next[1] - p_prev[1]
                L = math.hypot(dx, dz)
                if L < 1e-9:
                    nx, nz = 0.0, 1.0
                else:
                    # Tangent (dx,dz) -> outward normal (dz,-dx) normalized,
                    # taking the sign that gives +z (above) for upper half.
                    nx, nz = dz / L, -dx / L
                    if nz < 0:
                        nx, nz = -nx, -nz
            out.append((p[0] + offset * nx, p[1] + offset * nz))
        return out
    seam_upper = _offset_half(lens_half, WALL_T)
    seam_outline = list(seam_upper) + [(p[0], -p[1]) for p in reversed(seam_upper)]

    # South tangent of F7sb+G7sb (south side, offset by R_buf).
    d_s = unit((G7sb[0] - F7sb[0], G7sb[1] - F7sb[1]))
    n1 = (-d_s[1], d_s[0])
    n_s = n1 if n1[1] > 0 else (-n1[0], -n1[1])
    T_south_F7 = (F7sb[0] + R_buf * n_s[0], F7sb[1] + R_buf * n_s[1])
    T_south_G7 = (G7sb[0] + R_buf * n_s[0], G7sb[1] + R_buf * n_s[1])

    P, s_P, t_P = intersect(T_south_F7, d_s, ST, u)
    cos_th = d_s[0] * u[0] + d_s[1] * u[1]
    theta = math.acos(max(-1.0, min(1.0, cos_th)))
    theta_deg = math.degrees(theta)
    tp_dist = R_fillet / math.tan(theta / 2)
    arc_on_south = (P[0] - tp_dist * d_s[0], P[1] - tp_dist * d_s[1])
    arc_on_sb = (P[0] - tp_dist * u[0], P[1] - tp_dist * u[1])
    bis = unit((-d_s[0] - u[0], -d_s[1] - u[1]))
    center_dist = R_fillet / math.sin(theta / 2)
    arc_center = (P[0] + center_dist * bis[0], P[1] + center_dist * bis[1])

    print(f"R_BUFFER              = {R_buf} mm")
    print(f"R_fillet              = {R_fillet} mm")
    print(f"Interior angle at P   = {theta_deg:.2f} deg")
    print(f"Intersection P        = ({P[0]:.2f}, {P[1]:.2f})")
    print(f"Arc tangent on south  = ({arc_on_south[0]:.2f}, {arc_on_south[1]:.2f})")
    print(f"Arc tangent on sb     = ({arc_on_sb[0]:.2f}, {arc_on_sb[1]:.2f})")
    print()
    print(f"Hidden joint at Y_ST_HORIZ = {Y_RIM}")
    print(f"  Tongue: height={TONGUE_H} mm, thick={TONGUE_T} mm")
    print(f"  Groove clearance   = {CLEAR} mm (for adhesive)")
    print(f"  External chamfer   = {CHAMFER} mm")
    print(f"Lens x-range          = [{LENS_X_MIN}, {LENS_X_MAX}]")
    print(f"Chamber rim outer x   = [{LENS_X_MIN-WALL_T:.1f}, {LENS_X_MAX+WALL_T:.1f}]")
    print(f"Plate ST->BT x-range  = [{ST[0]:.2f}, {BT[0]:.2f}]")
    print(f"  covered by chamber rim for x in [{LENS_X_MIN-WALL_T:.1f}, {LENS_X_MAX+WALL_T:.1f}]")
    print(f"  covered by shoulder underside for x > {LENS_X_MAX+WALL_T:.1f}")

    # ==================================================================
    # Panel layout: three stacked panels.
    #   A (side view)   on top
    #   B (plan view)   middle
    #   C (joint detail) bottom
    # ==================================================================
    xs_A = [F7sb[0] - 40, BT[0] + 20, P[0] + 20]
    ys_A = [ST[1] + 40, P[1] - 30, F7sb[1] + R_buf + 10]
    Ax_min, Ax_max = min(xs_A), max(xs_A)
    Ay_min, Ay_max = min(ys_A), max(ys_A)
    A_h = Ay_max - Ay_min

    Bz_half = max(LENS_Z_HALF + WALL_T + 8, GAP / 2 + PLATE_T + 5)
    B_h = 2 * Bz_half

    # Panel C: zoomed 20x view of the joint cross-section.
    # Window in real mm: width = tongue+adhesive+chamber+lip ~ 30 mm,
    #                    height = chamber_wall_above + tongue + shoulder_wall ~ 20 mm.
    C_zoom = 2.0
    C_real_w = 40.0
    C_real_h = 24.0
    C_h = C_real_h * C_zoom

    sep = 15
    svg_x_min = Ax_min
    svg_w = Ax_max - Ax_min
    svg_h = A_h + sep + B_h + sep + C_h

    # y-origin for each panel in the SVG.
    A_y0 = 0                    # panel A starts at top
    B_y0 = A_h + sep            # panel B starts after A + sep
    B_z0 = B_y0 + Bz_half       # z=0 line of panel B (center)
    C_y0 = B_y0 + B_h + sep     # panel C starts after B + sep

    def line(x1, y1, x2, y2, color, sw=1.0, dash=None, opacity=1.0):
        d = f' stroke-dasharray="{dash}"' if dash else ''
        o = f' opacity="{opacity}"' if opacity < 1.0 else ''
        return (f'<line x1="{x1:.2f}" y1="{y1:.2f}" '
                f'x2="{x2:.2f}" y2="{y2:.2f}" '
                f'stroke="{color}" stroke-width="{sw}" fill="none"{d}{o}/>')

    def circle(cx, cy, r, stroke, fill="none", sw=0.8):
        return (f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{r}" '
                f'stroke="{stroke}" fill="{fill}" stroke-width="{sw}"/>')

    def ellipse(cx, cy, rx, ry, stroke, fill="none", sw=0.8, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ''
        return (f'<ellipse cx="{cx:.2f}" cy="{cy:.2f}" rx="{rx:.2f}" ry="{ry:.2f}" '
                f'stroke="{stroke}" fill="{fill}" stroke-width="{sw}"{d}/>')

    def text(x, y, s, color="black", size=6):
        return (f'<text x="{x:.2f}" y="{y:.2f}" '
                f'font-size="{size}" fill="{color}" '
                f'font-family="monospace">{s}</text>')

    def rect(x, y, w, h, stroke, fill="none", sw=0.6, opacity=1.0):
        o = f' opacity="{opacity}"' if opacity < 1.0 else ''
        return (f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" '
                f'stroke="{stroke}" fill="{fill}" stroke-width="{sw}"{o}/>')

    # Panel A transform:
    def Ax(x): return x
    def Ay(y): return A_y0 + (y - Ay_min)

    # Panel B transform (x-z, z up is -y in SVG):
    def By(z): return B_z0 - z

    # Panel C transform (y-z, zoomed; local frame centered on joint):
    #   y_joint (real) = Y_RIM   -> SVG y = C_y0 + C_h/2
    #   z_joint (real) = 0       -> SVG x = svg_x_min + svg_w/2
    C_cx = svg_x_min + svg_w / 2
    C_cy = C_y0 + C_h / 2
    def Cx(z_real): return C_cx + z_real * C_zoom
    def Cy(y_real): return C_cy + (y_real - Y_RIM) * C_zoom  # y increases downward

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" '
             f'viewBox="{svg_x_min:.2f} 0 {svg_w:.2f} {svg_h:.2f}" '
             f'width="{svg_w*3:.0f}" height="{svg_h*3:.0f}">']

    # ================== Panel A: side view ==================
    parts.append(text(svg_x_min + 2, A_y0 + 6,
                      'A. Side view (authoring x-y) — seam at y = Y_ST_HORIZ',
                      color='#333', size=5))

    # Chamber opening x-extent (seam line)
    parts.append(line(LENS_X_MIN - WALL_T, Ay(Y_RIM),
                      LENS_X_MAX + WALL_T, Ay(Y_RIM),
                      '#cc00cc', sw=2))
    parts.append(text(LENS_X_MIN - WALL_T - 2, Ay(Y_RIM) + 10,
                      f'seam (chamber↔shoulder) at y={Y_RIM:.2f}',
                      '#cc00cc', size=4))

    # Plate ST→BT edge
    parts.append(line(ST[0], Ay(ST[1]), BT[0], Ay(BT[1]),
                      '#227722', sw=3))
    parts.append(text(ST[0] + 2, Ay(ST[1]) - 2,
                      f'plate ST→BT ({BT[0]-ST[0]:.1f} mm)',
                      '#227722', size=5))

    # Buffer circles
    for name, c, col in [('F7sb', F7sb, '#d02020'), ('G7sb', G7sb, '#d02020'),
                         ('F7fb', F7fb, '#2020d0'), ('G7fb', G7fb, '#2020d0')]:
        parts.append(circle(Ax(c[0]), Ay(c[1]), R_buf, col))
        parts.append(text(Ax(c[0]) + R_buf + 1, Ay(c[1]) + 2, name, col, size=5))

    # ST, BT markers
    parts.append(circle(Ax(ST[0]), Ay(ST[1]), 1.5, '#000', fill='#000'))
    parts.append(text(Ax(ST[0]) + 3, Ay(ST[1]) + 7, 'ST', '#000', size=6))
    parts.append(circle(Ax(BT[0]), Ay(BT[1]), 1.5, '#000', fill='#000'))
    parts.append(text(Ax(BT[0]) + 3, Ay(BT[1]) + 7, 'BT', '#000', size=6))

    # South tangent, soundboard tangent (dashed)
    ext = 30
    st_start = (T_south_F7[0] - ext * d_s[0], T_south_F7[1] - ext * d_s[1])
    st_end = (P[0] + ext * d_s[0], P[1] + ext * d_s[1])
    parts.append(line(Ax(st_start[0]), Ay(st_start[1]),
                      Ax(st_end[0]), Ay(st_end[1]),
                      '#008800', 0.8, dash='3,2'))
    sb_start = (ST[0] - 10 * u[0], ST[1] - 10 * u[1])
    sb_end = (P[0] + ext * u[0], P[1] + ext * u[1])
    parts.append(line(Ax(sb_start[0]), Ay(sb_start[1]),
                      Ax(sb_end[0]), Ay(sb_end[1]),
                      '#aa6600', 0.8, dash='3,2'))

    # Intersection P and fillet arc
    parts.append(circle(Ax(P[0]), Ay(P[1]), 1.5, '#ff00ff', fill='#ff00ff'))
    parts.append(text(Ax(P[0]) + 3, Ay(P[1]),
                      f'P (angle={theta_deg:.1f}°)', '#ff00ff', size=5))
    parts.append(circle(Ax(arc_center[0]), Ay(arc_center[1]),
                        R_fillet, '#bbbbbb', sw=0.3))
    v1 = (arc_on_south[0] - arc_center[0], arc_on_south[1] - arc_center[1])
    v2 = (arc_on_sb[0] - arc_center[0], arc_on_sb[1] - arc_center[1])
    cross = v1[0] * v2[1] - v1[1] * v2[0]
    sweep = 1 if cross > 0 else 0
    parts.append(f'<path d="M {Ax(arc_on_south[0]):.2f} {Ay(arc_on_south[1]):.2f} '
                 f'A {R_fillet} {R_fillet} 0 0 {sweep} '
                 f'{Ax(arc_on_sb[0]):.2f} {Ay(arc_on_sb[1]):.2f}" '
                 f'stroke="#ff00ff" stroke-width="2" fill="none"/>')

    for c in [F7sb, G7sb, F7fb, G7fb]:
        parts.append(circle(Ax(c[0]), Ay(c[1]), 0.6, '#000', fill='#000', sw=0))

    # Separator
    parts.append(line(svg_x_min, B_y0 - sep / 2,
                      svg_x_min + svg_w, B_y0 - sep / 2,
                      '#ccc', sw=0.5, dash='2,3'))

    # ================== Panel B: plan view at Y_ST_HORIZ ==================
    parts.append(text(svg_x_min + 2, B_y0 + 6,
                      f'B. Plan view at y=Y_ST_HORIZ={Y_RIM} (x-z) — seam ring, plates',
                      color='#333', size=5))

    # z=0 axis
    parts.append(line(svg_x_min, By(0), svg_x_min + svg_w, By(0),
                      '#ddd', sw=0.4, dash='1,3'))

    # Chamber lens (opening, inner boundary of rim/seam) -- actual limaçon
    # horizontal slice at y=Y_ST_HORIZ, NOT an ellipse.
    lens_path = 'M ' + ' L '.join(
        f'{p[0]:.2f} {By(p[1]):.2f}' for p in lens_outline) + ' Z'
    parts.append(f'<path d="{lens_path}" stroke="#00aaaa" '
                 f'fill="#e0ffff" stroke-width="1.5"/>')

    # Chamber rim outer boundary (= seam ring; shoulder underside matches this)
    seam_path = 'M ' + ' L '.join(
        f'{p[0]:.2f} {By(p[1]):.2f}' for p in seam_outline) + ' Z'
    parts.append(f'<path d="{seam_path}" stroke="#cc00cc" '
                 f'fill="none" stroke-width="1.2"/>')
    parts.append(text(LENS_X_MAX + WALL_T + 2, By(0) - 10,
                      f'seam ring (outer rim), chamfer {CHAMFER} mm',
                      '#cc00cc', size=4))

    # Tongue centerline (midway between lens and seam ring)
    tongue_upper = _offset_half(lens_half, WALL_T / 2)
    tongue_outline = list(tongue_upper) + [(p[0], -p[1]) for p in reversed(tongue_upper)]
    tongue_path = 'M ' + ' L '.join(
        f'{p[0]:.2f} {By(p[1]):.2f}' for p in tongue_outline) + ' Z'
    parts.append(f'<path d="{tongue_path}" stroke="#aa6600" '
                 f'fill="none" stroke-width="0.8" stroke-dasharray="2,1.5"/>')
    parts.append(text(LENS_X_MIN - 5, By(LENS_Z_HALF + WALL_T + 8),
                      f'tongue centerline (h={TONGUE_H}, t={TONGUE_T})',
                      '#aa6600', size=3.5))

    # Plate footprints at ±z
    plate_x = ST[0]
    plate_w = BT[0] - ST[0]
    for z_low in [GAP/2, -GAP/2 - PLATE_T]:
        parts.append(rect(plate_x, By(z_low + PLATE_T),
                          plate_w, PLATE_T,
                          stroke='#227722', fill='#ccffcc', sw=1.0,
                          opacity=0.8))
    parts.append(text(ST[0] + 2, By(GAP/2 + PLATE_T) + 5,
                      f'+z plate (z∈[{GAP/2:.1f}, {GAP/2+PLATE_T:.1f}])',
                      '#227722', size=4))
    parts.append(text(ST[0] + 2, By(-GAP/2) - 1,
                      f'-z plate (z∈[{-GAP/2-PLATE_T:.1f}, {-GAP/2:.1f}])',
                      '#227722', size=4))

    # Fastener positions (4 around the rim): mark with small crosses
    fastener_pts = [
        (lens_cx, lens_rz + WALL_T/2),      # N
        (lens_cx, -(lens_rz + WALL_T/2)),   # S
        (lens_cx - lens_rx - WALL_T/2, 0),  # W
        (lens_cx + lens_rx + WALL_T/2, 0),  # E
    ]
    for (fx, fz) in fastener_pts:
        parts.append(circle(fx, By(fz), 1.2, '#0066cc', fill='#ffffff', sw=0.6))
        parts.append(line(fx - 2, By(fz), fx + 2, By(fz), '#0066cc', 0.4))
        parts.append(line(fx, By(fz) - 2, fx, By(fz) + 2, '#0066cc', 0.4))
    parts.append(text(fastener_pts[3][0] + 3, By(fastener_pts[3][1]) + 2,
                      'fasteners (4×)', '#0066cc', size=3.5))

    # ST, BT in plan view
    parts.append(circle(ST[0], By(0), 1.2, '#000', fill='#000'))
    parts.append(circle(BT[0], By(0), 1.2, '#000', fill='#000'))
    parts.append(text(ST[0] + 2, By(0) - 2, 'ST', '#000', size=5))
    parts.append(text(BT[0] + 2, By(0) - 2, 'BT', '#000', size=5))

    # Separator
    parts.append(line(svg_x_min, C_y0 - sep / 2,
                      svg_x_min + svg_w, C_y0 - sep / 2,
                      '#ccc', sw=0.5, dash='2,3'))

    # ================== Panel C: joint cross-section detail ==================
    X_REF = 870.0
    parts.append(text(svg_x_min + 2, C_y0 + 6,
                      f'C. Joint detail at x = {X_REF:.0f} (y-z cross-section, '
                      f'{C_zoom:.0f}× zoom) — pear-shape walls',
                      color='#333', size=5))

    # Local reference: z=0 at center; y_RIM at vertical center of panel.
    # Chamber: wall on both ±z, ends at rim (y=Y_RIM on top of rim).
    # The chamber's outer surface is a limaçon, so the wall flares outward
    # below the rim (pear-shape). Sample the limaçon outer surface at
    # x = X_REF along y to get the curved outer boundary; the inner boundary
    # is offset inward by WALL_T.

    # Chamber wall (below the seam, 15 mm of it visible) -- curved.
    ch_ys = []
    ch_outer_z = []
    y_step = 0.5
    n_steps_ch = int(15.0 / y_step) + 1
    for i in range(n_steps_ch):
        y_val = Y_RIM + i * y_step
        z_val = chamber_outer_z(X_REF, y_val)
        if z_val is not None:
            ch_ys.append(y_val)
            ch_outer_z.append(z_val)

    def _wall_path(ys, outer_zs, sign):
        """Build a closed SVG path for one chamber wall (sign=+1 for +z side,
        -1 for -z side). Outer curve top->bottom, then across by WALL_T,
        then inner curve bottom->top, then close."""
        outer_pts = [(sign * z, y) for y, z in zip(ys, outer_zs)]
        inner_pts = [(sign * (z - WALL_T), y) for y, z in zip(ys, outer_zs)]
        cmds = [f'M {Cx(outer_pts[0][0]):.2f} {Cy(outer_pts[0][1]):.2f}']
        for (z, y) in outer_pts[1:]:
            cmds.append(f'L {Cx(z):.2f} {Cy(y):.2f}')
        for (z, y) in reversed(inner_pts):
            cmds.append(f'L {Cx(z):.2f} {Cy(y):.2f}')
        cmds.append('Z')
        return ' '.join(cmds)

    if ch_ys:
        for sign in (+1, -1):
            parts.append(f'<path d="{_wall_path(ch_ys, ch_outer_z, sign)}" '
                         f'stroke="#008888" fill="#e0ffff" '
                         f'stroke-width="0.8" fill-opacity="0.6"/>')
        parts.append(text(Cx(-(ch_outer_z[-1])) - 22, Cy(Y_RIM + 12),
                          'chamber wall', '#008888', size=4))

    # Shoulder wall (above the seam, 10 mm visible) -- approximated as the
    # MIRROR of the chamber wall about y = Y_RIM. This is only roughly
    # correct: the actual shoulder generator curves after ~10 mm. For a
    # sketch, it conveys the pear-shape continuation across the seam.
    sh_ys = []
    sh_outer_z = []
    for i in range(int(10.0 / y_step) + 1):
        dy = i * y_step
        # Mirror: shoulder y = Y_RIM - dy uses chamber's z at Y_RIM + dy.
        z_val = chamber_outer_z(X_REF, Y_RIM + dy)
        if z_val is not None:
            sh_ys.append(Y_RIM - dy)
            sh_outer_z.append(z_val)

    if sh_ys:
        for sign in (+1, -1):
            parts.append(f'<path d="{_wall_path(sh_ys, sh_outer_z, sign)}" '
                         f'stroke="#884400" fill="#ffddbb" '
                         f'stroke-width="0.8" fill-opacity="0.6"/>')
        parts.append(text(Cx(-(sh_outer_z[-1])) - 24, Cy(Y_RIM - 8),
                          'shoulder wall', '#884400', size=4))

    # The tongue/groove/chamfer/fastener detail is a schematic centered on
    # z=0 in the panel frame (it shows the joint's MECHANISM, not its actual
    # location on the wall). Keep these unchanged at small z values.
    ch_wall_x1 = -TONGUE_T / 2 - 2  # inner face of chamber wall in z (schematic)
    ch_wall_x2 = TONGUE_T / 2 + 2   # outer face of chamber wall in z (schematic)

    # Tongue (rises from rim centerline, above Y_RIM):
    tongue_x1 = -TONGUE_T / 2
    tongue_x2 = TONGUE_T / 2
    parts.append(rect(Cx(tongue_x1), Cy(Y_RIM - TONGUE_H),
                      TONGUE_T * C_zoom, TONGUE_H * C_zoom,
                      stroke='#aa6600', fill='#ffeedd', sw=1.0))
    parts.append(text(Cx(tongue_x2) + 2, Cy(Y_RIM - TONGUE_H / 2),
                      f'tongue ({TONGUE_T}×{TONGUE_H})', '#aa6600', size=4))

    # Shoulder wall (above the rim) + groove
    # Shoulder wall z-extent roughly matches the chamber wall.
    sh_wall_x1 = ch_wall_x1
    sh_wall_x2 = ch_wall_x2
    # Groove: centered at z=0, slightly wider than tongue (by 2*CLEAR)
    gr_x1 = tongue_x1 - CLEAR
    gr_x2 = tongue_x2 + CLEAR
    gr_y_top = Y_RIM - TONGUE_H - 1.0   # 1mm above tongue top for adhesive
    # Draw shoulder as a path with groove cut out:
    shoulder_path = (
        f'M {Cx(sh_wall_x1)} {Cy(Y_RIM)} '            # start at LL
        f'L {Cx(sh_wall_x1)} {Cy(Y_RIM - 12)} '       # up left outer
        f'L {Cx(sh_wall_x2)} {Cy(Y_RIM - 12)} '       # top right
        f'L {Cx(sh_wall_x2)} {Cy(Y_RIM)} '            # down right outer
        f'L {Cx(gr_x2)} {Cy(Y_RIM)} '                 # left along bottom to groove right
        f'L {Cx(gr_x2)} {Cy(gr_y_top)} '              # up right side of groove
        f'L {Cx(gr_x1)} {Cy(gr_y_top)} '              # across top of groove
        f'L {Cx(gr_x1)} {Cy(Y_RIM)} '                 # down left side of groove
        f'Z'
    )
    parts.append(f'<path d="{shoulder_path}" '
                 f'stroke="#884400" fill="#ffddbb" stroke-width="1.0" fill-opacity="0.6"/>')
    parts.append(text(Cx(sh_wall_x2) + 2, Cy(Y_RIM - 6),
                      'shoulder wall', '#884400', size=4))
    parts.append(text(Cx(gr_x1) - 20, Cy(gr_y_top - 1),
                      f'groove (clear={CLEAR})', '#884400', size=3.5))

    # External chamfer marks on both sides at the seam
    for sign in [-1, 1]:
        cx_outer = sign * (ch_wall_x2 + 0.1)
        parts.append(line(Cx(cx_outer), Cy(Y_RIM - CHAMFER),
                          Cx(cx_outer + sign * CHAMFER), Cy(Y_RIM),
                          '#cc00cc', sw=1.0))
    parts.append(text(Cx(ch_wall_x2 + 1), Cy(Y_RIM) + 8,
                      f'external chamfer ({CHAMFER} mm each side)',
                      '#cc00cc', size=3.5))

    # Horizontal dashed line marking Y_ST_HORIZ (the seam y)
    parts.append(line(Cx(-12), Cy(Y_RIM), Cx(12), Cy(Y_RIM),
                      '#cc00cc', sw=0.4, dash='2,1.5'))
    parts.append(text(Cx(-12) - 30, Cy(Y_RIM) + 2,
                      f'y=Y_ST_HORIZ={Y_RIM}', '#cc00cc', size=3.5))

    # Fastener path (dashed line showing the cap screw through rim into shoulder insert)
    # Enters from below the rim, passes up through chamber wall, into an insert in shoulder.
    insert_z = -ch_wall_x1 - 0.5  # mid wall negative side for illustration
    fast_x = Cx(-ch_wall_x2 + 0.5)
    parts.append(line(fast_x, Cy(Y_RIM + 14),  # starting from below
                      fast_x, Cy(Y_RIM - 6),   # up to insert
                      '#0066cc', sw=1.2, dash='3,2'))
    # Head of cap screw (below rim interior)
    parts.append(rect(fast_x - 1.5, Cy(Y_RIM + 14) - 1.5, 3, 2,
                      stroke='#0066cc', fill='#0066cc', sw=0.5))
    # Insert in shoulder (oval)
    parts.append(rect(fast_x - 1.2, Cy(Y_RIM - 6) - 2, 2.4, 4,
                      stroke='#0066cc', fill='none', sw=0.8))
    parts.append(text(fast_x + 3, Cy(Y_RIM - 6) + 1,
                      'insert', '#0066cc', size=3.5))
    parts.append(text(fast_x - 12, Cy(Y_RIM + 14) - 2,
                      'M4 screw (from inside)', '#0066cc', size=3.5))

    parts.append('</svg>')
    return '\n'.join(parts), {
        'theta_deg': theta_deg, 'tp_dist': tp_dist,
        'arc_on_south': arc_on_south, 'arc_on_sb': arc_on_sb,
    }


if __name__ == '__main__':
    import sys
    R = float(sys.argv[1]) if len(sys.argv) > 1 else None
    svg, info = main(R_fillet=R)
    out = 'shoulder_sketch.svg'
    with open(out, 'w') as f:
        f.write(svg)
    print(f"\nwrote {out}")
