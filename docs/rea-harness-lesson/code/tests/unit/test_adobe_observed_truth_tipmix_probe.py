"""The texture and dual-tip probe's own pattern, specs and measurement."""

from __future__ import annotations

import base64

import numpy as np

from scripts.adobe_observed_truth.tipmix_probe import (BAND, OWN_PATTERN_NAME, PATTERN, measure, pattern_grey, pattern_image,
                                                         tipmix_specs)


def test_the_pattern_is_a_ramp_across_its_columns() -> None:
    grey = np.asarray(pattern_image())[..., 0]
    assert grey.shape == (PATTERN, PATTERN) and (grey == grey[0]).all()
    assert grey[0].tolist() == [pattern_grey(x) for x in range(PATTERN)]
    assert pattern_grey(0) == 0 and pattern_grey(PATTERN - 1) == 255


def test_the_measure_keeps_the_band_round_the_stroke() -> None:
    alpha = np.zeros((300, 400), np.uint8)
    alpha[150, :] = 9
    m = measure(alpha)
    band = np.frombuffer(base64.b64decode(m["alpha"]), np.uint8).reshape(m["shape"])
    assert m["top"] == BAND[0] and band.shape == (BAND[1] - BAND[0], 400) and (band[150 - BAND[0]] == 9).all()


def test_texture_specs_define_and_delete_the_own_pattern_and_dual_specs_do_not() -> None:
    specs = tipmix_specs()
    assert len({s.item_id for s in specs}) == len(specs) >= 16
    for s in specs:
        names = [step[0] for step in s.steps]
        textured = s.item_id.startswith("tipmix:texture")
        assert ("define_own_pattern" in names) == textured == ("delete_own_pattern" in names)
        assert names.count("tipmix_stroke") == 1 and "brush_restore" in names and names[-1] == "close_throwaway_document"
    assert OWN_PATTERN_NAME.startswith("observed-truth")
