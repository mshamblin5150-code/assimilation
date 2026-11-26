"""Illustrator's live effects swept setting by setting: each effect applied by script from its dialog's
defaults with one setting changed at a time, then expanded and measured as geometry."""

from __future__ import annotations

from scripts.adobe_observed_truth.illustrator_effects import EFFECTS, Effect, effect_data, effect_specs, measured


def test_settings_are_written_as_the_effect_dictionary_reads_them() -> None:
    effect = Effect("Adobe Example", "Live Example", "rect", {"size": ("R", 10), "count": ("I", 4), "on": ("B", 0)}, {})

    assert effect_data(effect) == "R size 10 I count 4 B on 0 "
    assert effect_data(effect, "count", 7) == "R size 10 I count 7 B on 0 "


def test_each_effect_runs_its_defaults_twice_then_one_changed_setting_per_spec() -> None:
    effect = Effect("Adobe Example", "Live Example", "rect", {"size": ("R", 10), "count": ("I", 4)},
                    {"size": [0, 20], "count": [1]})

    specs = effect_specs([effect])

    assert [s.item_id for s in specs] == [
        "effect:Adobe Example@defaults", "effect:Adobe Example@defaults-again",
        "effect:Adobe Example@size=0", "effect:Adobe Example@size=20",
        "effect:Adobe Example@size=1000000", "effect:Adobe Example@size=-1000000",  # far values, as in Photoshop
        "effect:Adobe Example@count=1"]
    assert specs[3].steps[1] == ("apply_effect", "Adobe Example", "rect", "R size 20 I count 4 ")
    assert {s.family for s in specs} == {"live_effect"}
    assert specs[0].steps[-1] == ("close_throwaway_document",)


def test_every_effect_starts_from_settings_it_has_and_varies_only_those() -> None:
    for effect in EFFECTS:
        assert set(effect.vary) <= set(effect.base), effect.name
        assert effect.item in {"rect", "ellipse", "arch", "star", "text", "group", "overlap"}, effect.name


def test_an_effect_that_leaves_nothing_measures_as_empty_not_as_huge_bounds() -> None:
    # Pathfinder's Command 2 on two overlapping squares left nothing (2026-11-25 probe).
    assert measured(["", 1, 0, 0, 8392, -8042, -24374, 24724]) == {
        "error": "", "items": 1, "points": 0, "area": 0, "bounds": None}
    assert measured(["", 3, 8, 7200, 240, 80, 330, 0]) == {
        "error": "", "items": 3, "points": 8, "area": 7200, "bounds": [240, 80, 330, 0]}
