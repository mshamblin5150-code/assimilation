"""Deeper probes: vary one setting of a plug-in filter at a time, from its recorded defaults."""

from __future__ import annotations

import json

from scripts.adobe_observed_truth.sweeps import (
    descriptor_puts,
    specs_from_results,
    sweep_specs,
    sweep_values,
    with_options,
)

RADIAL = [
    {"key": "amount", "type": "integer", "default": 10},
    {"key": "blurMethod", "type": "choice", "choices": "blurMethod", "default": "spin"},
    {"key": "center.horizontal", "type": "double", "default": 0.5},
]


def test_a_choice_takes_its_options_from_the_plug_in_by_4_char_code_and_skips_its_default() -> None:
    codes = {"blurMethod": {"BlrM"}, "spin": {"Spn "}}
    pipl = {"BlrM": ["Spn ", "Zm  "]}

    method = with_options([RADIAL[1]], codes, pipl)[0]

    assert sweep_values(method) == ["Zm  "]


def test_each_setting_is_swept_alone_and_the_defaults_are_replayed_three_times() -> None:
    settings = [{"key": "radius", "type": "unit", "unit": "pixelsUnit", "default": 1.0}]

    ids = [spec.item_id for spec in sweep_specs("gaussianBlur", settings)]

    assert ids == [
        "sweep:gaussianBlur:default#1",
        "sweep:gaussianBlur:default#2",
        "sweep:gaussianBlur:default#3",
        "sweep:gaussianBlur:radius=0.25",
        "sweep:gaussianBlur:radius=0.5",
        "sweep:gaussianBlur:radius=2.0",
        "sweep:gaussianBlur:radius=4.0",
        # Far out of any range: the value Photoshop reads back is the bound it clamps to.
        "sweep:gaussianBlur:radius=-1000000.0",
        "sweep:gaussianBlur:radius=1000000.0",
    ]


def test_a_command_with_nested_settings_is_not_swept_yet_rather_than_replayed_half_set() -> None:
    assert sweep_specs("radialBlur", RADIAL) == []


def test_the_filter_identity_and_preset_choices_are_never_swept() -> None:
    settings = [
        {"key": "GEfk", "type": "choice", "choices": "GEfk", "default": "cutout", "options": ["Ct  ", "Wtrc"]},
        {"key": "presetKind", "type": "choice", "choices": "presetKindType", "default": "presetKindDefault"},
        {"key": "numberOfLayers", "type": "integer", "default": 4},
    ]

    ids = [spec.item_id for spec in sweep_specs("cutout", settings)]

    assert [i for i in ids if "default" not in i] == [
        "sweep:cutout:numberOfLayers=1",
        "sweep:cutout:numberOfLayers=2",
        "sweep:cutout:numberOfLayers=8",
        "sweep:cutout:numberOfLayers=16",
        "sweep:cutout:numberOfLayers=-1000000",
        "sweep:cutout:numberOfLayers=1000000",
    ]


def test_sweeps_use_each_commands_latest_recorded_defaults() -> None:
    def row(settings: list[dict[str, object]]) -> str:
        observed = {"event_settings": {"event": "gaussianBlur", "settings": settings, "error": None}}
        return json.dumps({"item_id": "menu:1@settings", "status": "ok", "observations": observed})

    old = row([{"key": "radius", "type": "integer", "default": 1}])
    refreshed = row([{"key": "radius", "type": "unit", "unit": "pixelsUnit", "default": 1.0}])

    specs = specs_from_results([old, refreshed, "{cut short"], codes_of={}, pipl_choices={})

    ids = [s.item_id for s in specs]
    assert "sweep:gaussianBlur:radius=4.0" in ids and "sweep:gaussianBlur:radius=4" not in ids


def test_the_replay_sets_every_setting_by_its_recorded_type_with_one_changed() -> None:
    settings = [
        {"key": "amount", "type": "unit", "unit": "percentUnit", "default": 50.0},
        {"key": "radius", "type": "double", "default": 1.0},
        {"key": "threshold", "type": "integer", "default": 0},
        {"key": "blurMethod", "type": "choice", "choices": "blurMethod", "default": "spin"},
        {"key": "monochromatic", "type": "boolean", "default": False},
    ]

    puts = descriptor_puts(settings, {"blurMethod": "Zm  ", "threshold": 10})

    assert puts == [
        ("putUnitDouble", "amount", "percentUnit", 50.0),
        ("putDouble", "radius", 1.0),
        ("putInteger", "threshold", 10),
        ("putEnumerated", "blurMethod", "blurMethod", {"code": "Zm  "}),
        ("putBoolean", "monochromatic", False),
    ]


def test_a_number_is_tried_at_a_quarter_half_double_and_four_times_its_default() -> None:
    assert sweep_values({"key": "amount", "type": "integer", "default": 10}) == [2, 5, 20, 40]


def test_decimal_settings_keep_their_fractions() -> None:
    assert sweep_values({"key": "radius", "type": "double", "default": 3.0}) == [0.75, 1.5, 6.0, 12.0]


def test_a_number_whose_default_is_zero_is_tried_at_one_ten_and_a_hundred() -> None:
    assert sweep_values({"key": "threshold", "type": "integer", "default": 0}) == [1, 10, 100]


def test_a_choice_is_tried_at_every_other_choice() -> None:
    method = {"key": "blurMethod", "type": "choice", "default": "spin", "options": ["spin", "zoom"]}

    assert sweep_values(method) == ["zoom"]


def test_an_on_off_setting_is_flipped() -> None:
    assert sweep_values({"key": "colorize", "type": "boolean", "default": False}) == [True]


def test_a_unit_value_is_varied_like_a_decimal_number() -> None:
    radius = {"key": "radius", "type": "unit", "unit": "pixelsUnit", "default": 1.0}

    assert sweep_values(radius) == [0.25, 0.5, 2.0, 4.0]
