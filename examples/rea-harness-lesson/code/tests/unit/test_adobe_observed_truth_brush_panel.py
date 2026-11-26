"""Finding the harness's ramp pattern in captures of Photoshop's pattern picker and texture swatch."""

from __future__ import annotations

import numpy as np

from scripts.adobe_observed_truth.brush_panel import find_ramp


def _canvas() -> np.ndarray:
    return np.full((120, 200, 3), 80, np.uint8)


def test_a_dark_to_white_ramp_is_found_at_its_centre() -> None:
    image = _canvas()
    image[60:63, 40:80] = np.linspace(10, 250, 40).astype(np.uint8)[None, :, None]
    assert find_ramp(image) == (59, 61)


def test_flat_grey_coloured_ramps_and_short_ones_are_not_ramps() -> None:
    image = _canvas()
    image[20, 10:60] = 200  # flat
    image[40, 10:60, 1] = np.linspace(10, 250, 50).astype(np.uint8)  # green only
    image[90, 10:20] = np.linspace(10, 250, 10).astype(np.uint8)[:, None]  # too short
    assert find_ramp(image) is None


def test_of_two_ramps_the_lowest_is_taken() -> None:
    image = _canvas()
    for y in (30, 100):
        image[y, 50:90] = np.linspace(10, 250, 40).astype(np.uint8)[:, None]
    assert find_ramp(image)[1] == 100
