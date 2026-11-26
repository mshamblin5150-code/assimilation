"""The healing probe's own images and specs."""

from __future__ import annotations

import numpy as np
import pytest

from scripts.adobe_observed_truth.heal_probe import CENTRE, DOT, IMAGES, PATCH, base, heal_specs, image, patch


@pytest.mark.parametrize("name", IMAGES)
def test_each_image_is_its_smooth_base_with_a_black_dot_at_the_centre(name: str) -> None:
    grey, smooth = np.asarray(image(name))[..., 0].astype(int), base(name)
    yy, xx = np.mgrid[0:grey.shape[0], 0:grey.shape[1]] + 0.5
    dot = (xx - CENTRE[0] - 0.5) ** 2 + (yy - CENTRE[1] - 0.5) ** 2 <= DOT ** 2
    assert (grey[dot] == 0).all() and np.abs(grey[~dot] - smooth[~dot]).max() <= 0.5


def test_the_bowl_bends_enough_for_a_smooth_fill_to_miss_it() -> None:
    bowl = base("heal_bowl")
    laplacian = bowl[CENTRE[1], CENTRE[0] + 1] + bowl[CENTRE[1], CENTRE[0] - 1] - 2 * bowl[CENTRE[1], CENTRE[0]]
    assert laplacian > 0.05


def test_the_patch_is_centred_on_the_dot() -> None:
    grey = np.asarray(image("heal_ramp"))[..., 0]
    p = patch(np.repeat(grey[..., None], 3, 2))
    assert len(p) == 2 * PATCH + 1 and p[PATCH][PATCH] == 0


def test_every_spec_heals_once_and_restores_the_tool() -> None:
    specs = heal_specs()
    assert len({s.item_id for s in specs}) == len(specs) >= 12
    for s in specs:
        names = [step[0] for step in s.steps]
        assert names.count("spot_heal") == 1 and "restore_tool_state" in names and names[-1] == "close_throwaway_document"
