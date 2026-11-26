"""The layer probe's own images and how a composite is kept and read back."""

from __future__ import annotations

import numpy as np

from scripts.adobe_observed_truth.layer_probe import images, layer_specs, measure, table


def test_the_grey_pair_puts_every_base_level_in_a_column_and_every_top_level_in_a_row() -> None:
    made = images()
    base, top = np.asarray(made["blend_grey_base"]()), np.asarray(made["blend_grey_top"]())
    assert base[:, :, 0][7].tolist() == list(range(256)) and top[:, :, 0][:, 9].tolist() == list(range(256))


def test_a_recorded_grey_composite_reads_back_as_the_same_table() -> None:
    composite = np.dstack([np.tile(np.arange(256, dtype=np.uint8)[:, None], (1, 256))] * 3 + [np.full((256, 256), 255, np.uint8)])
    row = measure(composite, "grey")
    assert row["channels_equal"] and (table(row) == composite[..., 0]).all()


def test_every_mode_has_a_spec_and_the_mixing_modes_run_on_colour() -> None:
    ids = {s.item_id for s in layer_specs()}
    assert "blend:grey:multiply" in ids and "blend:colour:luminosity" in ids and "blend:grey:screen:opacity=50" in ids
    assert len(ids) == 49
