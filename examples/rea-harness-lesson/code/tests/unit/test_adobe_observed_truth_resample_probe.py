"""The resample probe's own impulse image and specs."""

from __future__ import annotations

from scripts.adobe_observed_truth.resample_probe import IMPULSES, METHODS, SIZES, image, resample_specs, resize_js


def test_the_image_has_one_white_pixel_per_impulse() -> None:
    grey = image()[..., 0]
    assert (grey == 255).sum() == len(IMPULSES) and all(grey[y, x] == 255 for x, y in IMPULSES)


def test_every_method_and_size_has_a_spec_and_the_script_names_the_method() -> None:
    assert len(resample_specs()) == len(METHODS) * len(SIZES)
    assert "ResampleMethod.BICUBICSHARPER" in resize_js(32, "BICUBICSHARPER")
