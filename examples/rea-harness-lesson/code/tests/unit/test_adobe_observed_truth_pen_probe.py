"""The pen probe's strokes and what it reads from a painted layer."""

from __future__ import annotations

import numpy as np

from scripts.adobe_observed_truth.pen_probe import N, X0, X1, column_centres, pen_specs, ramp, stroke_points


def test_a_stroke_runs_across_the_canvas_one_pen_frame_every_two_pixels() -> None:
    points = stroke_points()
    assert len(points) == N and points[0][0] == X0 and points[-1][0] == X1
    assert {p[1] for p in points} == {points[0][1]}
    assert ramp(0, 1)[0] == 0 and ramp(0, 1)[-1] == 1


def test_every_spec_sends_pen_input_and_ids_are_unique() -> None:
    specs = pen_specs()
    assert all(s.needs_input for s in specs) and len({s.item_id for s in specs}) == len(specs)


def test_column_centres_give_each_columns_middle_painted_row() -> None:
    alpha = np.zeros((10, 3), dtype=np.uint8)
    alpha[2:5, 0] = 255  # rows 2-4
    alpha[6, 1] = 100  # too faint to count
    assert column_centres(alpha) == [3.0, None, None]
