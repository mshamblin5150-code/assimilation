"""The magnetic lasso probe's own images and click path."""

from __future__ import annotations

import math

import numpy as np
import pytest

from scripts.adobe_observed_truth.channel_model import srgb_to_lab
from scripts.adobe_observed_truth.lasso_probe import (CENTRE, RADIUS, REFINE_IMAGES, STEPS, edge_distance, image, lasso_specs,
                                                     mouse_path, refine_layers, refine_specs, soft_matte)


def test_the_disc_images_have_the_contrast_named() -> None:
    high, low = image("lasso_high"), image("lasso_low")
    assert high[150, 200, 0] == 60 and high[10, 10, 0] == 200
    assert low[150, 200, 0] == 180 and low[10, 10, 0] == 200


def test_the_click_path_circles_the_disc_at_the_offset() -> None:
    path = mouse_path(8)
    assert len(path) == STEPS + 1
    assert all(abs(math.hypot(x - CENTRE[0], y - CENTRE[1]) - (RADIUS + 8)) < 1e-9 for x, y in path)


def test_the_disc_itself_measures_on_its_edge() -> None:
    ys, xs = np.mgrid[0:300, 0:400] + 0.5
    disc = (((xs - CENTRE[0]) ** 2 + (ys - CENTRE[1]) ** 2) <= RADIUS ** 2).astype(np.uint8) * 255
    assert abs(edge_distance(disc)["edge_mean"]) < 1.0


def test_every_probe_needs_input() -> None:
    assert all(s.needs_input for s in lasso_specs()) and len(lasso_specs()) == 40


@pytest.mark.parametrize("name", REFINE_IMAGES)
def test_each_refine_image_lays_its_foreground_over_its_background_by_the_soft_matte(name: str) -> None:
    foreground, background = refine_layers(name)
    alpha = soft_matte()[..., None]
    assert np.abs(image(name) - (alpha * foreground + (1 - alpha) * background)).max() <= 0.5


def test_the_equiluminant_pair_differs_in_colour_but_not_lightness() -> None:
    foreground, background = refine_layers("refine_equiluminant")
    f, b = srgb_to_lab(foreground[150, 200]), srgb_to_lab(background[0, 0])
    assert abs(f[0] - b[0]) < 1.0 and np.hypot(*(f[1:] - b[1:])) > 60


def test_the_gradient_and_texture_images_are_not_two_colours() -> None:
    _f, background = refine_layers("refine_gradient")
    assert background[:, 0].max() < background[:, -1].min() - 100
    foreground, _b = refine_layers("refine_texture")
    assert len(np.unique(foreground[100:200, 150:250, 0])) == 2


def test_every_refine_image_has_specs() -> None:
    used = {s.steps[0][1] for s in refine_specs()}
    assert set(REFINE_IMAGES) <= used
