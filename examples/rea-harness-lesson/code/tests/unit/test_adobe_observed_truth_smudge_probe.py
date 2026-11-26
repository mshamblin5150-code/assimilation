"""The smudge probe's own image, stroke and measurement."""

from __future__ import annotations

import numpy as np

from scripts.adobe_observed_truth.smudge_probe import BAND, ROW, ROWS, START, image, measure, smudge_specs


def test_the_image_is_a_black_band_on_white() -> None:
    grey = np.asarray(image())[..., 0]
    assert (grey[:, BAND[0]:BAND[1]] == 0).all() and grey[:, :BAND[0]].min() == 255 and grey[:, BAND[1]:].min() == 255


def test_the_stroke_starts_inside_the_band_and_runs_out_into_the_white() -> None:
    assert BAND[0] < START[0] < BAND[1] and START[1] == ROW


def test_the_measure_keeps_the_stroke_row_and_the_rows_the_tip_covered() -> None:
    pixels = np.zeros((300, 400, 4), np.uint8)
    pixels[ROW, :, :3] = 7
    m = measure(pixels)
    assert m["row"] == [7] * 400 and len(m["rows"]) == ROWS[1] - ROWS[0] and m["rows_top"] == ROWS[0]


def test_every_spec_smudges_once_and_restores_the_tool() -> None:
    specs = smudge_specs()
    assert len({s.item_id for s in specs}) == len(specs) >= 8
    for s in specs:
        names = [step[0] for step in s.steps]
        assert names.count("smudge_stroke") == 1 and "restore_tool_state" in names and names[-1] == "close_throwaway_document"
