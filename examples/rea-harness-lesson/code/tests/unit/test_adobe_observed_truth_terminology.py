"""Photoshop's scripting dictionary, read out of the running app.

Built-in names have a four-letter code as their numeric id (charIDToTypeID("GsnB") ->
"gaussianBlur"); names added at runtime have small sequential ids and no code. Both are read
with typeIDToStringID, which returns "" for an id nothing is registered under.
"""

from __future__ import annotations

from scripts.adobe_observed_truth.terminology import dictionary, prefixes


def test_built_in_and_runtime_names_merge_into_one_sorted_dictionary() -> None:
    built_in = {"GsnB": "gaussianBlur", "HStr": "hueSaturation"}
    runtime = {4659: "activeFilters"}

    assert dictionary(built_in, runtime) == [
        {"name": "activeFilters", "code": None, "id": 4659},
        {"name": "gaussianBlur", "code": "GsnB", "id": 0x47736E42},
        {"name": "hueSaturation", "code": "HStr", "id": 0x48537472},
    ]


def test_a_name_known_both_ways_is_listed_once_under_its_code() -> None:
    assert dictionary({"GsnB": "gaussianBlur"}, {12: "gaussianBlur"}) == [
        {"name": "gaussianBlur", "code": "GsnB", "id": 0x47736E42}
    ]


def test_the_code_space_is_split_into_two_letter_prefixes_to_keep_each_lookup_call_short() -> None:
    chunks = prefixes("ab")

    assert chunks == ["aa", "ab", "ba", "bb"]
