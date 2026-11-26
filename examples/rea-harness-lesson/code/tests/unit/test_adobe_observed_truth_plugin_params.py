"""Each filter plug-in describes its own settings (JSON_PIPL); read them and find them in the code."""

from __future__ import annotations

import json

from scripts.adobe_observed_truth.plugin_params import (
    Choice,
    Setting,
    code_number,
    functions_using,
    own_functions,
    plugin_record,
    read_plugins,
)

# Shaped like a real JSON_PIPL resource (Standard MultiPlugin.8bf, Photoshop 2026), trimmed.
PIPL = json.dumps(
    {
        "PiPLs": [
            {
                "Kind": "Filter",
                "Name": "Radial Blur...",
                "Category": "Blur",
                "CodeEntryPointWin64": "EntryRadialBlur",
                "HasTerminology": {"ClassID": "Fltr", "EventID": "RdlB"},
                "Terminology": {
                    "Suites": [
                        {
                            "Events": [
                                {
                                    "EventType": "RdlB",
                                    "Parameters": [
                                        {
                                            "ParamName": "$$$/Example/RadialBlur/Actions/keyAmount=Amount",
                                            "ParamKeyword": "Amnt",
                                            "ParamType": "long",
                                        },
                                        {
                                            "ParamName": "$$$/Example/RadialBlur/Actions/keyBlurMethod=Method",
                                            "ParamKeyword": "BlrM",
                                            "ParamType": "BlrM",
                                            "ParamFlagBits": {"Enumerated": True},
                                        },
                                    ],
                                }
                            ],
                            "Enumerations": [
                                {
                                    "EnumID": "BlrM",
                                    "Enumerators": [
                                        {"EnumName": "$$$/Example/RadialBlur/Actions/enumSpin=spin", "EnumKeyword": "Spn "},
                                        {"EnumName": "$$$/Example/RadialBlur/Actions/enumZoom=zoom", "EnumKeyword": "Zm  "},
                                    ],
                                }
                            ],
                        }
                    ]
                },
            },
            {"Kind": "Filter", "Name": "Picture Package Filter", "Category": "**Hidden**"},
        ]
    }
)


def test_a_filter_is_read_with_its_menu_path_event_and_entry_point() -> None:
    radial = read_plugins(PIPL)[0]

    assert (radial.menu_path, radial.event, radial.entry_point) == (
        "Filter > Blur > Radial Blur",
        "RdlB",
        "EntryRadialBlur",
    )


def test_each_setting_is_read_with_a_readable_name_its_code_type_and_choices() -> None:
    assert read_plugins(PIPL)[0].settings == (
        Setting("Amount", "Amnt", "long", ()),
        Setting("Method", "BlrM", "BlrM", (Choice("spin", "Spn "), Choice("zoom", "Zm  "))),
    )


def test_a_hidden_plug_in_has_no_menu_path() -> None:
    assert read_plugins(PIPL)[1].menu_path is None


def test_a_four_letter_code_becomes_the_number_the_code_compares_against() -> None:
    # Seen live: Standard MultiPlugin compares a key against 0x416d6e74 ("Amnt", Radial Blur Amount).
    assert code_number("Amnt") == "0x416d6e74"


def test_codes_padded_with_spaces_keep_their_spaces() -> None:
    assert code_number("Zm  ") == "0x5a6d2020"


def test_the_functions_comparing_against_a_code_are_found_by_address() -> None:
    functions = [
        ("0x180214df0", "if (local_res8[0] == 0x416d6e74) {"),
        ("0x180221680", "switch (key) { case 0x416d6e74: case 0x426c724d: }"),
        ("0x180300000", "return 0;"),
    ]

    assert functions_using(functions, {"0x416d6e74", "0x426c724d"}) == {
        "0x416d6e74": ["0x180214df0", "0x180221680"],
        "0x426c724d": ["0x180221680"],
    }


def test_a_longer_number_that_contains_the_digits_is_not_a_use() -> None:
    assert functions_using([("0x1", "x = 0x416d6e7401;")], {"0x416d6e74"}) == {"0x416d6e74": []}


def test_a_record_ties_a_filter_to_its_menu_item_entry_function_and_the_code_reading_each_setting() -> None:
    radial = read_plugins(PIPL)[0]
    uses = {"0x416d6e74": ["0x180214df0"], "0x426c724d": [], "0x53706e20": ["0x180221680"]}

    record = plugin_record(
        radial,
        binary="Standard MultiPlugin.8bf",
        exports={"EntryRadialBlur": "0x180262090"},
        menu_items={"Filter > Blur > Radial Blur": "menu:-517"},
        uses=uses,
    )

    assert record == {
        "item_id": "menu:-517",
        "menu_path": "Filter > Blur > Radial Blur",
        "binary": "Standard MultiPlugin.8bf",
        "event": "RdlB",
        "entry_point": "EntryRadialBlur",
        "entry_function": "0x180262090",
        "own_functions": [],  # no function here reads both Amnt and BlrM
        "settings": [
            {"name": "Amount", "code": "Amnt", "type": "long", "functions": ["0x180214df0"], "choices": []},
            {
                "name": "Method",
                "code": "BlrM",
                "type": "BlrM",
                "functions": [],
                "choices": [
                    {"name": "spin", "code": "Spn ", "functions": ["0x180221680"]},
                    {"name": "zoom", "code": "Zm  ", "functions": []},
                ],
            },
        ],
    }


def test_a_filters_own_functions_are_those_reading_every_one_of_its_settings() -> None:
    # Standard MultiPlugin hosts 28 filters sharing codes like Amnt; only Radial Blur's own
    # descriptor code reads all of Amnt, BlrM, BlrQ and Cntr (seen live: 0x180221680, 0x180221a00).
    uses = {
        "0x416d6e74": ["0x180214df0", "0x180221680", "0x180221a00"],
        "0x426c724d": ["0x180221680", "0x180221a00"],
    }

    assert own_functions(read_plugins(PIPL)[0], uses) == ["0x180221680", "0x180221a00"]


def test_a_filter_with_a_single_setting_has_no_own_functions_since_shared_codes_cannot_tell() -> None:
    lone = read_plugins(PIPL)[0]
    lone = type(lone)(**{**lone.__dict__, "settings": lone.settings[:1]})

    assert own_functions(lone, {"0x416d6e74": ["0x180214df0"]}) == []