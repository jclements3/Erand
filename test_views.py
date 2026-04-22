"""Property-based tests for soundbox.geometry + build_views.

Covers:
  - Soundbox limaçon invariants (D bounds, b/D ratio, flat-face/bulge-tip
    consistency, z-antisymmetry of the cross-section).
  - Neck physical constants (thickness, gap, z-extents).
  - Neck bounding box (extracted from erand47jc_opt.svg) matches reference
    points (NB, NT, BT) approximately.
  - SVG anchor extractor round-trips through simple generated paths.

Run: python3 -m pytest test_views.py -v
"""
import math
import pytest
from hypothesis import given, strategies as st, settings

import soundbox.geometry as G
import build_views as BV

TOL = 1e-6


# ----- Soundbox limaçon invariants -----

@given(st.floats(min_value=G.S_BASS_FINAL, max_value=G.S_TREBLE_FINAL,
                 allow_nan=False, allow_infinity=False))
def test_D_bounded(sp):
    D = G.D_of(sp)
    assert 0.0 <= D <= G.D_PEAK + TOL


@given(st.floats(min_value=G.S_BASS_CLEAR, max_value=G.S_TREBLE_CLEAR))
def test_D_positive_in_interior(sp):
    # Between the bass-clearance and treble-clearance planes the chamber
    # always has positive perpendicular width.
    assert G.D_of(sp) > 0


@given(st.floats(min_value=G.S_BASS_CLEAR, max_value=G.S_TREBLE_CLEAR))
def test_b_equals_D_over_4_404(sp):
    assert abs(G.b_of(sp) * 4.404 - G.D_of(sp)) < 1e-9


def test_D_hits_peak_at_S_PEAK():
    assert abs(G.D_of(G.S_PEAK) - G.D_PEAK) < TOL


def test_D_zero_at_finals():
    assert abs(G.D_of(G.S_BASS_FINAL)) < TOL
    assert abs(G.D_of(G.S_TREBLE_FINAL)) < TOL


@given(st.floats(min_value=G.S_BASS_CLEAR, max_value=G.S_TREBLE_CLEAR))
def test_flat_face_matches_centerline(sp):
    # limacon_3d(sp, π) is the flat face point.
    x, y, z = G.limacon_3d(sp, math.pi)
    cx, cy = G.centerline_point(sp)
    assert abs(x - cx) < 1e-6
    assert abs(y - cy) < 1e-6
    assert abs(z) < 1e-6


@given(st.floats(min_value=G.S_BASS_CLEAR, max_value=G.S_TREBLE_CLEAR))
def test_bulge_tip_matches_theta0(sp):
    # limacon_3d(sp, 0) is the bulge tip point.
    x, y, z = G.limacon_3d(sp, 0.0)
    bx, by, bz = G.bulge_tip_point(sp)
    assert abs(x - bx) < 1e-6
    assert abs(y - by) < 1e-6
    assert abs(z - bz) < 1e-6


@given(
    sp=st.floats(min_value=G.S_BASS_CLEAR, max_value=G.S_TREBLE_CLEAR),
    theta=st.floats(min_value=0.0, max_value=2 * math.pi),
)
def test_cross_section_is_z_symmetric(sp, theta):
    # The chamber is symmetric about z=0, so (sp, θ) and (sp, -θ) give
    # points with identical x, y and opposite z.
    x1, y1, z1 = G.limacon_3d(sp, theta)
    x2, y2, z2 = G.limacon_3d(sp, -theta)
    assert abs(x1 - x2) < 1e-9
    assert abs(y1 - y2) < 1e-9
    assert abs(z1 + z2) < 1e-9


@given(st.floats(min_value=G.S_BASS_CLEAR, max_value=G.S_TREBLE_CLEAR))
def test_n_local_range(sp):
    # The cross-section spans n_local in [0, 4b]:
    # flat face (θ=π): n_local = 0
    # bulge tip (θ=0): n_local = 4b
    b = G.b_of(sp)
    flat_n = 0.0
    tip_n  = 4 * b
    for theta in (0.0, math.pi/2, math.pi, 3*math.pi/2):
        x, y, _ = G.limacon_3d(sp, theta)
        fx, fy = G.centerline_point(sp)
        n_local = ((x - fx) * G.n[0] + (y - fy) * G.n[1])
        assert flat_n - 1e-9 <= n_local <= tip_n + 1e-9


# ----- Neck physical geometry (plywood + gap) -----

def test_neck_plywood_thickness():
    assert BV.NECK_Z_OUTER - BV.NECK_Z_INNER == pytest.approx(BV.NECK_PLY_THICKNESS)


def test_neck_gap_matches_half_inch():
    assert BV.NECK_GAP == pytest.approx(12.7)
    assert BV.NECK_Z_INNER * 2 == pytest.approx(BV.NECK_GAP)


def test_neck_half_inch_in_mm():
    # Sanity: 1/2" = 12.7 mm exactly.
    assert BV.NECK_GAP == pytest.approx(0.5 * 25.4)


# ----- Neck bbox (from erand47jc_opt.svg) -----

def test_neck_bbox_bass_anchored_at_column():
    # The neck outline starts and ends at the column (x = 12.7 mm).
    assert abs(BV.NECK_XMIN - G.NB[0]) < 0.5


def test_neck_bbox_reaches_past_the_soundbox():
    # Treble-most neck point should be near BT (~ 903-906 mm) — well past the
    # soundbox top ST (838.8 mm).
    assert BV.NECK_XMAX > G.ST[0]


def test_neck_bbox_y_range_matches_column_endpoints():
    # Neck top should be at or above NT; bottom should be below NB but well
    # above the floor.
    assert BV.NECK_YMIN <= G.NT[1] + 1.0
    assert BV.NECK_YMAX > G.NB[1]
    assert BV.NECK_YMAX < G.FLOOR_Y


# ----- Anchor extractor -----

@given(st.lists(
    st.tuples(
        st.floats(min_value=-1000, max_value=1000, allow_nan=False,
                  allow_infinity=False),
        st.floats(min_value=-1000, max_value=1000, allow_nan=False,
                  allow_infinity=False),
    ),
    min_size=2, max_size=12))
def test_anchor_extraction_roundtrip_lines(points):
    # Build a simple M + L* path through 'points' and check every anchor
    # is recovered with the identity translation.
    d = f"M {points[0][0]:.6f},{points[0][1]:.6f}"
    for p in points[1:]:
        d += f" L {p[0]:.6f},{p[1]:.6f}"
    extracted = BV._anchor_points(d, 0, 0)
    assert len(extracted) == len(points)
    for (ex, ey), (px, py) in zip(extracted, points):
        assert abs(ex - px) < 1e-3
        assert abs(ey - py) < 1e-3


@given(
    st.lists(
        st.tuples(
            st.floats(min_value=-1000, max_value=1000, allow_nan=False,
                      allow_infinity=False),
            st.floats(min_value=-1000, max_value=1000, allow_nan=False,
                      allow_infinity=False),
        ),
        min_size=1, max_size=6
    ),
    st.floats(min_value=-100, max_value=100),
    st.floats(min_value=-100, max_value=100),
)
def test_anchor_translation_applied(points, dx, dy):
    d = f"M 0,0"
    for p in points:
        d += f" L {p[0]:.6f},{p[1]:.6f}"
    extracted = BV._anchor_points(d, dx, dy)
    # First anchor (the M point) is (0+dx, 0+dy).
    assert abs(extracted[0][0] - dx) < 1e-3
    assert abs(extracted[0][1] - dy) < 1e-3
    for (ex, ey), (px, py) in zip(extracted[1:], points):
        assert abs(ex - (px + dx)) < 1e-3
        assert abs(ey - (py + dy)) < 1e-3


@given(st.lists(
    st.tuples(
        st.floats(min_value=-500, max_value=500, allow_nan=False,
                  allow_infinity=False),
        st.floats(min_value=-500, max_value=500, allow_nan=False,
                  allow_infinity=False),
    ),
    min_size=4, max_size=4))
def test_anchor_extraction_cubic_returns_endpoint_only(points):
    # A single cubic C has three (x,y) pairs; the anchor is only the third
    # (the endpoint). Prepend an M so the path is valid.
    d = (f"M {points[0][0]},{points[0][1]} "
         f"C {points[1][0]},{points[1][1]} "
         f"{points[2][0]},{points[2][1]} "
         f"{points[3][0]},{points[3][1]}")
    extracted = BV._anchor_points(d, 0, 0)
    # One M anchor + one C endpoint = 2 total.
    assert len(extracted) == 2
    assert abs(extracted[0][0] - points[0][0]) < 1e-3
    assert abs(extracted[1][0] - points[3][0]) < 1e-3
    assert abs(extracted[1][1] - points[3][1]) < 1e-3


# ----- Generated view content sanity -----

def test_side_view_contains_neck_if_neck_loaded():
    xml = "\n".join(BV.side_view_content())
    if BV.NECK_D is not None:
        assert 'stroke="#8b4513"' in xml, "neck outline missing in side view"
        assert BV.NECK_D[:40] in xml, "neck d attribute not wired through"


def test_top_view_has_two_neck_strips():
    xml = "\n".join(BV.top_view_content())
    # Two rectangles with fill = FILL_NECK — one per plywood side.
    assert xml.count(f'fill="{BV.FILL_NECK}"') == 2


def test_front_view_has_two_neck_strips():
    xml = "\n".join(BV.front_view_content())
    assert xml.count(f'fill="{BV.FILL_NECK}"') == 2


def test_top_view_neck_strip_thickness():
    # Extract all y="..." height="..." from rects whose fill matches FILL_NECK.
    xml = "\n".join(BV.top_view_content())
    import re
    for m in re.finditer(
            rf'<rect[^/]*fill="{re.escape(BV.FILL_NECK)}"[^/]*/>', xml):
        tag = m.group(0)
        h_m = re.search(r'height="([-0-9.]+)"', tag)
        assert h_m is not None
        assert abs(float(h_m.group(1)) - BV.NECK_PLY_THICKNESS) < 1e-6
