"""Catalogued controls get positions: an annotator names which numbered items of a capture each
control is; the catalogue keeps the union of those items as a fraction of the capture."""

from __future__ import annotations

from scripts.adobe_observed_truth.catalogue_positions import apply_positions

ITEMS = {"D1": (10, 10, 20, 20), "D2": (30, 10, 40, 20), "T1": (0, 0, 10, 5)}
ROW = {"image": "levels.png", "controls": [{"type": "histogram_sliders"}, {"type": "static_text"}, {"type": "eyedropper"}]}


def test_each_control_gets_the_union_of_the_items_named_for_it_as_fractions_of_the_capture() -> None:
    answer = {"0": ["D1", "D2"], "1": ["T1"], "2": None}

    row = apply_positions(ROW, answer, ITEMS, size=(100, 200))

    assert [c.get("box") for c in row["controls"]] == [[0.05, 0.1, 0.2, 0.2], [0.0, 0.0, 0.05, 0.05], None]


def test_an_answer_naming_an_item_the_capture_does_not_have_leaves_that_control_without_a_box() -> None:
    row = apply_positions(ROW, {"0": ["D9"], "1": ["T1"]}, ITEMS, size=(100, 200))

    assert [c.get("box") for c in row["controls"]] == [None, [0.0, 0.0, 0.05, 0.05], None]
