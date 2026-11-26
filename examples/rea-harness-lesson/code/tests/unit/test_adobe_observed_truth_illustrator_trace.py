"""The trace probe's own rasters and specs."""

from __future__ import annotations

import numpy as np

from scripts.adobe_observed_truth.illustrator_trace import CIRCLE, IMAGES, SPECKLES, raster, trace_js, trace_specs


def test_every_probe_raster_is_drawn_and_the_circle_has_its_area() -> None:
    for name in IMAGES:
        assert raster(name).shape == (200, 200, 3)
    dark = (raster("circle")[..., 0] == 0).sum()
    assert abs(dark - np.pi * CIRCLE[2] ** 2) < 60


def test_speckles_are_the_sizes_named() -> None:
    dark = raster("speckles")[..., 0] == 0
    assert dark.sum() == sum(side * side for _, _, side in SPECKLES)


def test_the_trace_script_sets_enumerations_bare_and_values_as_json() -> None:
    script = trace_js("C:/x.png", {"tracingMode": "TracingModeType.TRACINGMODEBLACKANDWHITE", "ignoreWhite": True, "threshold": 64})
    assert "o.tracingMode=TracingModeType.TRACINGMODEBLACKANDWHITE;" in script
    assert "o.ignoreWhite=true;" in script and "o.threshold=64;" in script
    assert "doc.close(SaveOptions.DONOTSAVECHANGES)" in script


def test_every_fidelity_setting_has_a_spec_on_each_shape() -> None:
    ids = {s.item_id for s in trace_specs()}
    assert "trace:star:bw:cornerFidelity=0" in ids and "trace:speckles:bw:noiseFidelity=10" in ids and "trace:ramp:bw:threshold=192" in ids


def test_the_palette_bars_and_overlapping_blobs_are_drawn_as_named() -> None:
    from scripts.adobe_observed_truth.illustrator_trace import BARS, PALETTE

    colours = {tuple(c) for c in raster("palette").reshape(-1, 3).tolist()}
    assert colours == {tuple(c) for c in PALETTE} | {(255, 255, 255)}
    dark_rows = (raster("bars")[..., 0] == 0).any(axis=1)
    assert dark_rows.sum() == sum(width for _, width in BARS)
    assert len({tuple(c) for c in raster("blobs_overlap").reshape(-1, 3).tolist()}) == 4


def test_the_new_trace_specs_cover_colour_reduction_abutting_and_strokes() -> None:
    ids = {s.item_id for s in trace_specs()}
    assert {"trace:palette:limited:colorFidelity=0", "trace:palette:limited:tracingColors=2", "trace:blobs_overlap:color:abutting",
            "trace:ring:bw:abutting", "trace:bars:strokes:maxStrokeWeight=4"} <= ids


def test_a_preset_loads_before_the_other_options_and_the_colour_presets_trace_the_palette() -> None:
    script = trace_js("C:/x.png", {"preset": "3 Colors", "ignoreWhite": True})
    assert script.index('o.loadFromPreset("3 Colors");') < script.index("o.ignoreWhite=true;")
    ids = {s.item_id for s in trace_specs()}
    assert {"trace:palette:preset=3_colors", "trace:palette:preset=6_colors", "trace:palette:preset=16_colors"} <= ids
