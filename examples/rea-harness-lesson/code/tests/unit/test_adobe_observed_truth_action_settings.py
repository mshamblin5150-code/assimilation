"""A built-in command's settings, read from the action descriptor Photoshop reports when it runs.

Built-in commands (Gaussian Blur, Hue/Saturation...) have no plug-in file describing them; the
descriptor Photoshop sends to action listeners names the event and every setting with its
default (batchPlay JSON form).
"""

from __future__ import annotations

from scripts.adobe_observed_truth.action_settings import (
    event_for,
    event_script,
    settings_of,
)


def test_a_unit_value_setting_keeps_its_unit_and_default() -> None:
    gaussian = {"_obj": "gaussianBlur", "radius": {"_unit": "pixelsUnit", "_value": 1.0}}

    assert settings_of(gaussian) == [
        {"key": "radius", "type": "unit", "unit": "pixelsUnit", "default": 1.0}
    ]


def test_a_choice_setting_keeps_its_choice_list_name_and_default() -> None:
    radial = {"_obj": "radialBlur", "blurMethod": {"_enum": "blurMethod", "_value": "spin"}}

    assert settings_of(radial) == [
        {"key": "blurMethod", "type": "choice", "choices": "blurMethod", "default": "spin"}
    ]


def test_plain_values_are_typed_as_photoshop_would() -> None:
    assert settings_of({"_obj": "x", "amount": 10, "angle": 0.5, "colorize": False, "name": "a"}) == [
        {"key": "amount", "type": "integer", "default": 10},
        {"key": "angle", "type": "double", "default": 0.5},
        {"key": "colorize", "type": "boolean", "default": False},
        {"key": "name", "type": "string", "default": "a"},
    ]


def test_settings_nested_in_objects_and_lists_are_named_by_their_path() -> None:
    hue_sat = {
        "_obj": "hueSaturation",
        "adjustment": [{"_obj": "hueSatAdjustmentV2", "hue": 0, "saturation": 0}],
    }

    assert [s["key"] for s in settings_of(hue_sat)] == ["adjustment[0].hue", "adjustment[0].saturation"]


def test_which_document_and_layer_it_ran_on_are_not_settings() -> None:
    housekeeping = {
        "_obj": "gaussianBlur",
        "_target": [{"_ref": "layer", "_enum": "ordinal", "_value": "targetEnum"}],
        "_isCommand": True,
        "documentID": 219,
        "layerID": [2],
    }

    assert settings_of(housekeeping) == []


NAMES = {"gaussianBlur", "hueSaturation", "unsharpMask", "brightnessEvent", "levels"}


def test_a_menu_item_is_matched_to_the_event_of_the_same_name() -> None:
    assert event_for("Filter > Blur > Gaussian Blur", NAMES) == "gaussianBlur"


def test_punctuation_and_trailing_dots_in_the_menu_name_are_ignored() -> None:
    assert event_for("Image > Adjustments > Hue/Saturation...", NAMES) == "hueSaturation"


def test_a_menu_item_whose_event_is_named_differently_stays_unmatched_rather_than_guessed() -> None:
    # Brightness/Contrast's event is brightnessEvent: not derivable from the menu name.
    assert event_for("Image > Adjustments > Brightness/Contrast", NAMES) is None


def test_the_event_is_run_with_its_dialog_shown_so_its_defaults_are_accepted_and_returned() -> None:
    assert 'executeAction(stringIDToTypeID("gaussianBlur"), undefined, DialogModes.ALL)' in (
        event_script("gaussianBlur")
    )


def test_an_event_name_is_always_quoted_never_run_as_script() -> None:
    assert 'stringIDToTypeID("x\\");alert(1);//")' in event_script('x");alert(1);//')