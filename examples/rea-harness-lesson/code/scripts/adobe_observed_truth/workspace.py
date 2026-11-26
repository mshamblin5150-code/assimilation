"""Clicking inside a full-window workspace (Vanishing Point, Liquify, Adaptive Wide Angle).

Such a workspace shows the document in its own view at its own zoom, so the main canvas
mapping does not apply. The harness knows exactly what the test image looks like, so it finds
it in a screenshot of the workspace (whatever is not the flat background), confirms the find
looks like the image, and maps image points to screen points from there.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from PIL import Image

from .input_plan import Event, click


@dataclass(frozen=True)
class Placement:
    """Where the image is drawn in the workspace screenshot, in screenshot pixels."""

    left: int
    top: int
    width: int
    height: int


def locate(
    shot: np.ndarray, search: tuple[int, int, int, int], tolerance: int = 12
) -> Placement | None:
    """The bounding box of everything in the search area (x0, y0, x1, y1) that differs from
    the workspace background (the search area's top-left pixel); None if nothing does."""
    x0, y0, x1, y1 = search
    area = shot[y0:y1, x0:x1, :3].astype(np.int16)
    differs = (np.abs(area - area[0, 0]) > tolerance).any(axis=2)
    ys, xs = np.nonzero(differs)
    if not len(xs):
        return None
    return Placement(
        x0 + int(xs.min()), y0 + int(ys.min()), int(xs.max() - xs.min()) + 1, int(ys.max() - ys.min()) + 1
    )


def trim_frame(shot: np.ndarray, placement: Placement, most: int = 3) -> Placement:
    """Drop a thin dark uniform frame the workspace draws round the image (at most `most`
    pixels a side); light uniform edges, such as a white-backed image's, are the image."""
    left, top = placement.left, placement.top
    right, bottom = left + placement.width, top + placement.height

    def frame(line: np.ndarray) -> bool:
        line = line[..., :3].astype(np.float64)
        return bool(line.std() < 6 and line.mean() < 60)

    for _ in range(most):
        if frame(shot[top, left:right]):
            top += 1
        if frame(shot[bottom - 1, left:right]):
            bottom -= 1
        if frame(shot[top:bottom, left]):
            left += 1
        if frame(shot[top:bottom, right - 1]):
            right -= 1
    return Placement(left, top, right - left, bottom - top)


def likeness(shot: np.ndarray, placement: Placement, image: Image.Image) -> float:
    """How much the found area looks like the image: the correlation of their brightness over
    the image's opaque pixels (1 the same picture, about 0 something unrelated)."""
    crop = shot[
        placement.top : placement.top + placement.height,
        placement.left : placement.left + placement.width,
        :3,
    ].astype(np.float64)
    fitted = np.asarray(image.convert("RGBA").resize((placement.width, placement.height)))
    opaque = fitted[..., 3] > 0
    a = crop.mean(axis=2)[opaque]
    b = fitted[..., :3].astype(np.float64).mean(axis=2)[opaque]
    if a.std() == 0 or b.std() == 0:
        return 0.0
    return float(np.corrcoef(a, b)[0, 1])


def plane_clicks(
    placement: Placement, *, image_size: tuple[int, int], window_origin: tuple[int, int]
) -> list[Event]:
    """Four clicks on the corners of a rectangle inset a quarter from each image edge, in
    order: a perspective plane Vanishing Point always accepts."""
    width, height = image_size
    corners = [
        (width / 4, height / 4),
        (width * 3 / 4, height / 4),
        (width * 3 / 4, height * 3 / 4),
        (width / 4, height * 3 / 4),
    ]
    return [
        event
        for corner in corners
        for event in click(
            to_screen(corner, placement, image_size=image_size, window_origin=window_origin)
        )
    ]


def to_screen(
    point: tuple[float, float],
    placement: Placement,
    *,
    image_size: tuple[int, int],
    window_origin: tuple[int, int],
) -> tuple[int, int]:
    """An image pixel's centre as a screen point, via where the workspace draws the image."""
    scale_x = placement.width / image_size[0]
    scale_y = placement.height / image_size[1]
    # Halves round up, consistently (Python's round() sends 450.5 to 450 but 451.5 to 452).
    return (
        math.floor(window_origin[0] + placement.left + (point[0] + 0.5) * scale_x + 0.5),
        math.floor(window_origin[1] + placement.top + (point[1] + 0.5) * scale_y + 0.5),
    )
