"""Keeping the harness's dialog captures small: one file per distinct image."""

from __future__ import annotations

from scripts.adobe_observed_truth.capture_store import plan_dedupe


def test_identical_captures_keep_one_file_and_every_name_still_resolves() -> None:
    files = [("run2-dialog-0.png", "aa", 20.0), ("run1-dialog-0.png", "aa", 10.0), ("other.png", "bb", 5.0)]

    plan = plan_dedupe(files, pinned=set())

    assert plan == [
        {"name": "run2-dialog-0.png", "sha256": "aa", "kept_as": "run1-dialog-0.png"},
        {"name": "run1-dialog-0.png", "sha256": "aa", "kept_as": "run1-dialog-0.png"},
        {"name": "other.png", "sha256": "bb", "kept_as": "other.png"},
    ]


def test_an_image_the_catalogue_names_is_the_copy_kept() -> None:
    files = [("old.png", "aa", 1.0), ("catalogued.png", "aa", 9.0)]

    plan = plan_dedupe(files, pinned={"catalogued.png"})

    assert [p["kept_as"] for p in plan] == ["catalogued.png", "catalogued.png"]
