"""Illustrator's Pathfinder on curves, from two overlapping circles combined by every Pathfinder
command value (illustrator_pathfinder; pathfinder-probe.jsonl).

What a rebuild must do: keep each input curve's own Bezier segments and split them at their
exact intersections. Every output curve lies on the input Bezier circles (within 0.003 pt, the
coordinates being kept to about 1/4096 pt), new
anchors sit on the exact crossing points (within 0.001 pt), and areas equal the exact boolean of
the circles within 0.05% (the four-anchor Bezier circle's own bulge, 0.0136 pt at radius 50).
Any robust Bezier boolean that splits curves at exact intersections matches.

Command values (the Pathfinder effect's Command) and what they left on the two circles (pieces,
anchors per piece): 0 union (1, 8); 1 intersection (1, 4); 2 nothing; 3, 4 and 12 both discs
kept (2, 4 + 4); 5 divide (3: the lens and both crescents); 6 four pieces (3, 3, 5, 5); 7, 10
and 11 the front disc and the back crescent; 8 union; 9 one disc. Names follow the menu; only
the geometry is claimed.
"""

from __future__ import annotations

import numpy as np

KAPPA = 0.5522847498  # four-anchor circle handle length per radius
COMMAND_SHAPES = {0: (1, [8]), 1: (1, [4]), 2: (0, []), 3: (2, [4, 4]), 4: (2, [4, 4]), 5: (3, [4, 6, 6]),
                  6: (4, [3, 3, 5, 5]), 7: (2, [6, 6]), 8: (1, [8]), 9: (1, [4]), 10: (2, [6, 6]),
                  11: (2, [6, 6]), 12: (2, [4, 4])}


def bezier_circle(centre: tuple[float, float], radius: float) -> list[np.ndarray]:
    """A circle as Illustrator draws it: four cubic segments, each [p0, p1, p2, p3]."""
    cx, cy = centre
    k = KAPPA * radius
    anchors = [(cx, cy + radius), (cx + radius, cy), (cx, cy - radius), (cx - radius, cy)]
    tangents = [(k, 0), (0, -k), (-k, 0), (0, k)]
    segments = []
    for i in range(4):
        a, b = np.array(anchors[i]), np.array(anchors[(i + 1) % 4])
        ta, tb = np.array(tangents[i]), np.array(tangents[(i + 1) % 4])
        segments.append(np.array([a, a + ta, b - tb, b]))
    return segments


def _points(segment: np.ndarray, n: int) -> np.ndarray:
    t = np.linspace(0, 1, n)[:, None]
    p0, p1, p2, p3 = segment
    return (1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * p1 + 3 * (1 - t) * t ** 2 * p2 + t ** 3 * p3


def sample(path: dict, n: int = 48) -> np.ndarray:
    """Points along a measured path (document coordinates)."""
    points = np.asarray(path["points"], float)
    count = len(points)
    segments = []
    for i in range(count if path["closed"] else count - 1):
        a, b = points[i], points[(i + 1) % count]
        segments.append(_points(np.array([a[0:2], a[4:6], b[2:4], b[0:2]]), n))
    return np.vstack(segments) if segments else np.zeros((0, 2))


def distance_to_curves(points: np.ndarray, circles: list[list[np.ndarray]], density: int = 400) -> np.ndarray:
    """Each point's distance to the nearest of the given Bezier curves: the nearest of a coarse
    sampling, refined by Newton steps on the curve parameter."""
    segments = [segment for circle in circles for segment in circle]
    ts = np.linspace(0, 1, density)
    best = np.full(len(points), np.inf)
    for segment in segments:
        p0, p1, p2, p3 = segment
        curve = lambda t: ((1 - t) ** 3)[:, None] * p0 + (3 * (1 - t) ** 2 * t)[:, None] * p1 + (3 * (1 - t) * t ** 2)[:, None] * p2 + (t ** 3)[:, None] * p3
        d1 = lambda t: (3 * (1 - t) ** 2)[:, None] * (p1 - p0) + (6 * (1 - t) * t)[:, None] * (p2 - p1) + (3 * t ** 2)[:, None] * (p3 - p2)
        d2 = lambda t: (6 * (1 - t))[:, None] * (p2 - 2 * p1 + p0) + (6 * t)[:, None] * (p3 - 2 * p2 + p1)
        coarse = curve(ts)
        t = ts[np.sqrt(((points[:, None, :] - coarse[None, :, :]) ** 2).sum(-1)).argmin(axis=1)]
        for _ in range(8):
            diff = curve(t) - points
            grad = (diff * d1(t)).sum(-1)
            hess = (d1(t) ** 2).sum(-1) + (diff * d2(t)).sum(-1)
            t = np.clip(t - grad / np.where(np.abs(hess) > 1e-12, hess, 1e-12), 0, 1)
        best = np.minimum(best, np.sqrt(((curve(t) - points) ** 2).sum(-1)))
    return best
