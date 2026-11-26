"""Illustrator's art and pattern brushes along a path, rebuilt from brushes made of the harness's
own arrow (illustrator_brushes; brush-probe.jsonl), at the New Brush dialogs' defaults.

Art brush (stretch to fit, width 100%): a point of the art at x along its length and y across it
goes to the point at arc length x * L / art length along the path, offset across the path by
y minus the middle of the art's bounds (to the path's left as it runs, on these paths). On a
straight path that is exact; on an arc the anchors sit within 0.03 pt of it, and Illustrator adds
anchors along long art edges so they follow the bend. The art's area scales by L / art length.

Pattern brush (side tile only, stretch to fit): on each straight or smooth run, n = L / tile
length rounded half up (2.5 gives 3) whole tiles, at least one, each stretched along the path by
L / (n * tile length). At a corner the side tiles stop half the art's width short of it on each
side (pattern_runs); the corner tile, which a brush made at the dialog's defaults does not have,
would go there, so the corner is left empty. Exact on lines of 2, 2.5 and 2.75 tile lengths, an
open path with one right-angled corner and a closed square.

Scatter brush (size, spacing and scatter fixed at 100%, 100% and 0): an unscaled copy of the art
every art length along the path, from its start (scatter_positions: 0, 120, ... up to and
including L, so a closed path gets one on top of the first), each centred on the path by its
bounds. Exact on three lines.

Pattern options (each set in the brush's options dialog; pattern_layout): scale makes the tile
that much longer and wider, and the corner inset with it; spacing puts that share of a tile's
length before, between and after the tiles, count (L - gap) / (tile + gap) rounded half up,
everything stretched to fill; add space to fit keeps tiles whole, as many as fit (at least one),
and shares out the rest; approximate path matched stretch on these paths; flip along mirrors each
tile end to end. Exact (within 0.15 pt and 0.3% of area) on two lines and a corner.

Not settled: colourisation, approximate path where it differs from stretch, corner tiles of its
own (the options dialog previews auto-made corners, yet none came out on the corner or square); the scatter brush's random size, spacing, scatter and rotation; how a scatter copy turns
on a curve.
"""

from __future__ import annotations

import math

from . import illustrator_brushes as ib

ART_MIDDLE = (min(y for _, y in ib.ARROW) + max(y for _, y in ib.ARROW)) / 2


def _polygon_area(points: tuple[tuple[float, float], ...]) -> float:
    return abs(sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(points, points[1:] + points[:1]))) / 2


ARROW_AREA = _polygon_area(ib.ARROW)


def art_on_line(x: float, y: float, start: tuple[float, float], length: float) -> tuple[float, float]:
    """Where art point (x, y) lands on a horizontal path from `start` running `length` to the right."""
    return start[0] + x * length / ib.ART_LENGTH, start[1] + (y - ART_MIDDLE)


def art_on_arc(x: float, y: float) -> tuple[float, float]:
    """Where art point (x, y) lands on the probe's semicircle (left to right over the top)."""
    angle = math.pi - math.pi * x / ib.ART_LENGTH
    radius = ib.ARC_RADIUS + (y - ART_MIDDLE)
    return ib.ARC_CENTRE[0] + radius * math.cos(angle), ib.ARC_CENTRE[1] + radius * math.sin(angle)


def art_area(path_length: float) -> float:
    return ARROW_AREA * path_length / ib.ART_LENGTH


def pattern_tiles(path_length: float, tile_length: float = ib.ART_LENGTH) -> tuple[int, float]:
    """How many tiles a pattern brush lays along a smooth path, and how much each is stretched."""
    count = max(1, math.floor(path_length / tile_length + 0.5))
    return count, path_length / (count * tile_length)


def pattern_layout(run: float, scale: float = 100, spacing: float = 0, fit: str = "stretch") -> list[tuple[float, float, float]]:
    """Each tile a pattern brush lays on one run: (start, length along the run, stretch). The tile
    is the art at `scale` % (length and width); `spacing` % of a tile's length goes before, between
    and after the tiles; "stretch" (also what approximate gave here) rounds the count and stretches
    tiles and gaps alike to fill the run, "add_space" keeps tiles whole, as many as fit (at least
    one), and shares out what is left (a tile longer than its run overhangs both ends evenly)."""
    tile = ib.ART_LENGTH * scale / 100
    gap = tile * spacing / 100
    if fit == "add_space":
        count = max(1, math.floor(run / tile + 1e-9))
        space = (run - count * tile) / (count + 1)
        return [(space + k * (tile + space), tile, 1.0) for k in range(count)]
    count = max(1, math.floor((run - gap) / (tile + gap) + 0.5))
    stretch = run / (count * tile + (count + 1) * gap) if gap else run / (count * tile)
    first = gap * stretch
    return [(first + k * (tile + gap) * stretch, tile * stretch, stretch) for k in range(count)]


def pattern_runs(legs: tuple[float, ...], closed: bool, scale: float = 1.0) -> list[float]:
    """The run each pattern-brush side covers on a polyline of `legs`: every corner takes half the
    tile's width (the art's, times `scale`) from each leg it joins (open paths have no corner at
    their ends)."""
    inset = ib.ART_WIDTH * scale / 2
    runs = []
    for i, leg in enumerate(legs):
        corners = (1 if closed or i > 0 else 0) + (1 if closed or i < len(legs) - 1 else 0)
        runs.append(leg - inset * corners)
    return runs


def scatter_positions(path_length: float, art_length: float = ib.ART_LENGTH) -> list[float]:
    """Arc lengths where a scatter brush centres its copies: every art length from the start, up to
    and including the path's length."""
    return [art_length * k for k in range(math.floor(path_length / art_length + 1e-9) + 1)]
