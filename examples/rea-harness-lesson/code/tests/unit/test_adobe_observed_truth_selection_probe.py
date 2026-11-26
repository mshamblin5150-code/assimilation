"""The selection probe: Magic Wand, Paint Bucket and Feather measured on an image built for them, so
the tolerance rule, the colour distance, contiguity and the feather's softening can be rebuilt."""

from __future__ import annotations

import numpy as np

from scripts.adobe_observed_truth.selection_probe import (
    BANDS,
    GRID,
    PATCHES,
    measure_selection,
    published_rows,
    selection_image,
    selection_specs,
)


def test_the_dataset_gets_each_probes_latest_measures_and_nothing_else() -> None:
    measured = {"rows": {"grey": [0]}, "grid": [[0]], "patches": {"apart": [0, 0]}}
    results = [
        {"item_id": "wand:grey:tolerance=0:anti_alias=false", "status": "ok",
         "observations": {"selection": measured, "dialogs": []}},
        {"item_id": "bucket:grey:tolerance=10:anti_alias=true", "status": "ok", "observations": {"bucket": measured}},
        {"item_id": "feather:radius=1", "status": "failed", "observations": {}},
        {"item_id": "menu:1801", "status": "ok", "observations": {}},
    ]

    assert published_rows(results) == [{"item_id": "wand:grey:tolerance=0:anti_alias=false", **measured},
                                       {"item_id": "bucket:grey:tolerance=10:anti_alias=true", **measured}]


def test_the_image_holds_a_grey_ramp_a_red_ramp_a_colour_grid_and_patches_to_tell_contiguity() -> None:
    image = selection_image()

    assert image.shape == (300, 400, 3)
    grey_row, red_row = BANDS["grey"], BANDS["red"]
    assert image[grey_row, 129].tolist() == [129, 129, 129]  # column x is grey x up to 255
    assert image[red_row, 77].tolist() == [77, 128, 128]  # red ramps, green and blue stay 128
    i, j = 3, 5  # grid cell (column i, row j): red 16 i, green 16 j
    x, y = GRID["left"] + i * GRID["cell"] + 1, GRID["top"] + j * GRID["cell"] + 1
    assert image[y, x].tolist() == [16 * i, 16 * j, 128]
    a, b = PATCHES["apart"]
    assert image[a[1], a[0]].tolist() == image[b[1], b[0]].tolist()  # alike, with a wall between


def test_each_question_has_its_probe() -> None:
    ids = {s.item_id for s in selection_specs()}

    assert {f"wand:grey:tolerance={t}:anti_alias=false" for t in (0, 1, 5, 10, 32, 64, 128)} <= ids
    assert "wand:grey:tolerance=32:anti_alias=true" in ids
    # A colour difference in one channel was held to one less than the tolerance at 1 and 5 but not
    # at 10 or 32: every small tolerance on the red ramp pins the rule.
    assert {f"wand:red:tolerance={t}:anti_alias=false" for t in (*range(1, 13), 16)} <= ids
    assert {"wand:red:tolerance=32:anti_alias=false", "wand:grid:tolerance=40:anti_alias=false",
            "wand:apart:contiguous=false", "wand:apart:contiguous=true", "wand:corner:contiguous=true"} <= ids
    assert {f"bucket:grey:tolerance={t}:anti_alias=true" for t in (10, 32)} <= ids
    assert {f"feather:radius={r}" for r in (1, 2, 5, 10, 25)} <= ids
    wand = next(s for s in selection_specs() if s.item_id == "wand:grey:tolerance=32:anti_alias=false")
    assert wand.steps[0] == ("open_test_image", "selection")
    assert wand.steps[1] == ("wand_click", 128, BANDS["grey"], 32, False, True)


def test_a_mask_is_measured_along_the_bands_across_the_grid_and_at_each_patch() -> None:
    mask = np.zeros((300, 400), dtype=np.uint8)
    mask[BANDS["grey"], 96:161] = 255
    mask[GRID["top"]:GRID["top"] + GRID["cell"], GRID["left"]:GRID["left"] + GRID["cell"]] = 255  # cell (0, 0)
    a, _ = PATCHES["apart"]
    mask[a[1], a[0]] = 255

    found = measure_selection(mask)

    assert found["rows"]["grey"][100] == 255 and found["rows"]["grey"][200] == 0
    assert found["grid"][0][0] == 255 and found["grid"][0][1] == 0
    assert found["patches"]["apart"] == [255, 0]
