"""Room on an app's canvas for a mouse gesture: the part no other window lies over, and the view
that puts a drawing there.

A drag sent where a floating panel covers the canvas goes to the panel, not the tool (2026-11-26:
Illustrator's Width tool and Pencil "ignored" drags whose points lay under floating docks). So a
gesture is placed in the largest uncovered rectangle (free_rect), the view is set to fit it there
(view_for), and every point is checked to be over the canvas before anything is sent
(points_on_canvas).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

import numpy as np

Rect = tuple[int, int, int, int]  # left, top, right, bottom (screen pixels)


def free_rect(canvas: Rect, covers: Sequence[Rect], cell: int = 8) -> Rect:
    """The largest axis-aligned rectangle of `canvas` (on a grid of `cell` pixels) that none of
    `covers` overlaps."""
    left, top, right, bottom = canvas
    columns, rows = max(1, (right - left) // cell), max(1, (bottom - top) // cell)
    free = np.ones((rows, columns), dtype=bool)
    for cl, ct, cr, cb in covers:
        c0, c1 = max(0, (cl - left) // cell), min(columns, -(-(cr - left) // cell))
        r0, r1 = max(0, (ct - top) // cell), min(rows, -(-(cb - top) // cell))
        if c0 < c1 and r0 < r1:
            free[r0:r1, c0:c1] = False
    best, heights = (0, 0, 0, 0, 0), np.zeros(columns, dtype=int)
    for r in range(rows):  # largest rectangle in a histogram, row by row
        heights = np.where(free[r], heights + 1, 0)
        stack: list[int] = []
        for c in range(columns + 1):
            h = heights[c] if c < columns else 0
            while stack and heights[stack[-1]] >= h:
                height = heights[stack.pop()]
                start = stack[-1] + 1 if stack else 0
                area = height * (c - start)
                if area > best[0]:
                    best = (area, start, r - height + 1, c, r + 1)
            stack.append(c)
    _, c0, r0, c1, r1 = best
    return left + c0 * cell, top + r0 * cell, min(right, left + c1 * cell), min(bottom, top + r1 * cell)


def view_for(bbox_pt: tuple[float, float, float, float], free: Rect, canvas: Rect, device_pixels_per_point: float,
             margin: float = 0.1) -> tuple[tuple[int, int], int]:
    """The view (centre in milli-points, zoom in parts per million) that shows a drawing's bounding
    box (left, bottom, right, top in points, y up) inside `free`, `margin` of it kept clear on each
    side, for an app that draws the view centre at the canvas centre."""
    x0, y0, x1, y1 = bbox_pt
    fl, ft, fr, fb = free
    usable_w, usable_h = (fr - fl) * (1 - 2 * margin), (fb - ft) * (1 - 2 * margin)
    zoom = min(usable_w / max(x1 - x0, 1e-6), usable_h / max(y1 - y0, 1e-6)) / device_pixels_per_point
    per_pt = zoom * device_pixels_per_point  # screen pixels per point
    canvas_cx, canvas_cy = (canvas[0] + canvas[2]) / 2, (canvas[1] + canvas[3]) / 2
    free_cx, free_cy = (fl + fr) / 2, (ft + fb) / 2
    centre_x = (x0 + x1) / 2 - (free_cx - canvas_cx) / per_pt
    centre_y = (y0 + y1) / 2 + (free_cy - canvas_cy) / per_pt
    return (round(centre_x * 1000), round(centre_y * 1000)), round(zoom * 1_000_000)


def points_on_canvas(points: Sequence[tuple[int, int]], top_window_at: Callable[[tuple[int, int]], int], canvas_window: int) -> list[tuple[int, int]]:
    """The screen points whose top-level window is not the canvas's own (empty: all are on it)."""
    return [p for p in points if top_window_at(p) != canvas_window]
