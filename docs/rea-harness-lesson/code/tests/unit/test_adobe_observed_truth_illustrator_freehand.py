"""The freehand probe's own paths and scripts."""

from __future__ import annotations

import numpy as np
import pytest

from scripts.adobe_observed_truth.illustrator_freehand import circle, document_js, fidelity_slider, freehand_specs, noisy_sine, sine


def test_the_probe_paths_have_their_sizes() -> None:
    assert len(sine()) == 60 and len(circle()) == 73 and len(noisy_sine()) == 200


def test_documents_are_harness_titled_and_every_spec_closes_its_document() -> None:
    assert "pr.title=PREFIX+'freehand'" in document_js("width")
    assert all(s.steps[-1] == ("close_throwaway_document",) for s in freehand_specs())


def _dialog_image(knob_stop: int, stops=(39, 128, 218, 307, 397), y: int = 107) -> np.ndarray:
    """A stand-in for the Pencil options dialog: dark grey, a light track with tick marks above
    it at each stop, the blue knob covering one stop's tick, and a blue checkbox lower down."""
    image = np.full((300, 436, 3), 83, dtype=np.uint8)
    image[y, 34:402] = 170
    for x in stops:
        image[y - 7:y - 3, x] = 170
    yy, xx = np.mgrid[0:300, 0:436]
    image[(yy - y) ** 2 + (xx - stops[knob_stop]) ** 2 <= 49] = (64, 150, 255)
    image[200:212, 34:46] = (64, 150, 255)
    return image


@pytest.mark.parametrize("stop", range(5))
def test_the_fidelity_slider_is_read_from_the_dialog_image(stop: int) -> None:
    at, xs, y = fidelity_slider(_dialog_image(stop))
    assert at == stop and y == 107
    assert np.allclose(xs, (39, 128, 218, 307, 397), atol=1.5)
