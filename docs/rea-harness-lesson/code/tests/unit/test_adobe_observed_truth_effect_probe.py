"""The layer effect probe's scripts, specs and line reading."""

from __future__ import annotations

import numpy as np

from scripts.adobe_observed_truth.effect_probe import CASES, effect_js, effect_specs, measure


def test_each_effect_is_put_on_the_layer_style_in_red_at_full_opacity() -> None:
    for kind, _name, params in CASES:
        script = effect_js(kind, params)
        assert "charIDToTypeID('Lefx')" in script and "putDouble(charIDToTypeID('Rd  '),255)" in script, kind
    assert len(effect_specs()) == len(CASES)


def test_the_three_lines_are_read_through_the_centre() -> None:
    pixels = np.zeros((200, 200, 4), dtype=np.uint8)
    pixels[100, :, 1] = 7
    lines = measure(pixels)
    assert set(lines["row"]["green"]) == {7} and len(lines["diagonal"]["red"]) == 200
