"""
bezierfit.py
============

Python port of Philip J. Schneider's "An Algorithm for Automatically Fitting
Digitized Curves" from "Graphics Gems", Academic Press, 1990.

Reference C source  : https://github.com/erich666/GraphicsGems (FitCurves.c)
Reference Py source : https://github.com/volkerp/fitCurves   (fitCurves.py)

Pure ASCII. No Unicode characters.
"""

import numpy as np
from numpy import linalg


# ---------------------------------------------------------------------------
# Bernstein basis for a cubic Bezier
# ---------------------------------------------------------------------------

def b0(u):
    tmp = 1.0 - u
    return tmp * tmp * tmp

def b1(u):
    tmp = 1.0 - u
    return 3.0 * u * tmp * tmp

def b2(u):
    tmp = 1.0 - u
    return 3.0 * u * u * tmp

def b3(u):
    return u * u * u


def q(ctrl, u):
    """Evaluate a cubic Bezier (4 control points) at parameter u."""
    return (b0(u) * ctrl[0]
            + b1(u) * ctrl[1]
            + b2(u) * ctrl[2]
            + b3(u) * ctrl[3])


def qprime(ctrl, u):
    """Evaluate first derivative of the cubic Bezier at u."""
    tmp = 1.0 - u
    return (3.0 * tmp * tmp * (ctrl[1] - ctrl[0])
            + 6.0 * tmp * u   * (ctrl[2] - ctrl[1])
            + 3.0 * u   * u   * (ctrl[3] - ctrl[2]))


def qprimeprime(ctrl, u):
    """Evaluate second derivative of the cubic Bezier at u."""
    return (6.0 * (1.0 - u) * (ctrl[2] - 2.0 * ctrl[1] + ctrl[0])
            + 6.0 * u * (ctrl[3] - 2.0 * ctrl[2] + ctrl[1]))


# ---------------------------------------------------------------------------
# Top-level entry point
# ---------------------------------------------------------------------------

def fit_curve(points, max_error):
    """Fit a polyline with one or more cubic Bezier segments."""
    points = np.asarray(points, dtype=float)
    if points.shape[0] < 2:
        return []

    left_tangent  = _normalize(points[1]  - points[0])
    right_tangent = _normalize(points[-2] - points[-1])
    return _fit_cubic(points, left_tangent, right_tangent, max_error)


# ---------------------------------------------------------------------------
# Recursive core
# ---------------------------------------------------------------------------

def _fit_cubic(points, left_tangent, right_tangent, error):
    if len(points) == 2:
        dist = linalg.norm(points[0] - points[1]) / 3.0
        bez = np.array([
            points[0],
            points[0] + left_tangent * dist,
            points[1] + right_tangent * dist,
            points[1],
        ])
        return [bez]

    u = _chord_length_parameterize(points)

    bez = _generate_bezier(points, u, left_tangent, right_tangent)
    max_err, split_point = _compute_max_error(points, bez, u)
    if max_err < error:
        return [bez]

    if max_err < error * error:
        for _ in range(20):
            u_prime = _reparameterize(bez, points, u)
            bez = _generate_bezier(points, u_prime, left_tangent, right_tangent)
            max_err, split_point = _compute_max_error(points, bez, u_prime)
            if max_err < error:
                return [bez]
            u = u_prime

    center_tangent = _compute_center_tangent(points, split_point)
    left  = _fit_cubic(points[:split_point + 1], left_tangent,  center_tangent, error)
    right = _fit_cubic(points[split_point:],   -center_tangent, right_tangent,  error)
    return left + right


# ---------------------------------------------------------------------------
# Bezier generation (least-squares solve for P1, P2)
# ---------------------------------------------------------------------------

def _generate_bezier(points, parameters, left_tangent, right_tangent):
    bez = [points[0], None, None, points[-1]]

    n = len(points)
    A = np.zeros((n, 2, 2))
    for i, u in enumerate(parameters):
        A[i][0] = left_tangent  * b1(u)
        A[i][1] = right_tangent * b2(u)

    C = np.zeros((2, 2))
    X = np.zeros(2)

    for i, (pt, u) in enumerate(zip(points, parameters)):
        C[0][0] += np.dot(A[i][0], A[i][0])
        C[0][1] += np.dot(A[i][0], A[i][1])
        C[1][0]  = C[0][1]
        C[1][1] += np.dot(A[i][1], A[i][1])

        tmp = pt - (b0(u) * points[0]
                    + b1(u) * points[0]
                    + b2(u) * points[-1]
                    + b3(u) * points[-1])

        X[0] += np.dot(A[i][0], tmp)
        X[1] += np.dot(A[i][1], tmp)

    det_C0_C1 = C[0][0] * C[1][1] - C[1][0] * C[0][1]
    det_C0_X  = C[0][0] * X[1]    - C[1][0] * X[0]
    det_X_C1  = X[0]    * C[1][1] - X[1]    * C[0][1]

    alpha_l = 0.0 if det_C0_C1 == 0.0 else det_X_C1  / det_C0_C1
    alpha_r = 0.0 if det_C0_C1 == 0.0 else det_C0_X  / det_C0_C1

    seg_length = linalg.norm(points[0] - points[-1])
    epsilon = 1.0e-6 * seg_length

    if alpha_l < epsilon or alpha_r < epsilon:
        bez[1] = bez[0] + left_tangent  * (seg_length / 3.0)
        bez[2] = bez[3] + right_tangent * (seg_length / 3.0)
    else:
        bez[1] = bez[0] + left_tangent  * alpha_l
        bez[2] = bez[3] + right_tangent * alpha_r

    return np.array(bez)


# ---------------------------------------------------------------------------
# Reparameterization (Newton-Raphson root find on each sample)
# ---------------------------------------------------------------------------

def _reparameterize(bezier, points, parameters):
    return np.array([
        _newton_raphson_root_find(bezier, pt, u)
        for pt, u in zip(points, parameters)
    ])


def _newton_raphson_root_find(bez, point, u):
    d = q(bez, u) - point
    qp  = qprime(bez, u)
    qpp = qprimeprime(bez, u)

    numerator   = np.dot(d, qp)
    denominator = np.dot(qp, qp) + np.dot(d, qpp)

    if abs(denominator) < 1.0e-10:
        return u
    return u - numerator / denominator


# ---------------------------------------------------------------------------
# Parameterization + error measurement
# ---------------------------------------------------------------------------

def _chord_length_parameterize(points):
    u = [0.0]
    for i in range(1, len(points)):
        u.append(u[i - 1] + linalg.norm(points[i] - points[i - 1]))
    total = u[-1]
    if total == 0.0:
        return np.zeros(len(points))
    return np.array([val / total for val in u])


def _compute_max_error(points, bez, parameters):
    max_dist = 0.0
    split_point = len(points) // 2
    for i, (pt, u) in enumerate(zip(points, parameters)):
        dist = linalg.norm(q(bez, u) - pt) ** 2
        if dist >= max_dist:
            max_dist = dist
            split_point = i
    return max_dist, split_point


# ---------------------------------------------------------------------------
# Tangent estimation
# ---------------------------------------------------------------------------

def _compute_center_tangent(points, center):
    v1 = points[center - 1] - points[center]
    v2 = points[center]     - points[center + 1]
    t = (v1 + v2) / 2.0
    return _normalize(t)


def _normalize(v):
    n = linalg.norm(v)
    if n == 0.0:
        return v
    return v / n


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    pts = np.array([[0.0, 0.0], [10.0, 10.0], [10.0, 0.0], [20.0, 0.0]])
    curves = fit_curve(pts, max_error=50.0)
    print("fit %d input points -> %d cubic segment(s)" % (len(pts), len(curves)))
    for i, c in enumerate(curves):
        print("segment", i)
        for j, p in enumerate(c):
            print("  P%d = (%.6f, %.6f)" % (j, p[0], p[1]))
