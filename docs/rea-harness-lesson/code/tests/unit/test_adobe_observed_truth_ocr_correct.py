"""OCR corrected against Photoshop's own interface strings."""

from __future__ import annotations

from scripts.adobe_observed_truth.ocr_correct import Corrector

STRINGS = ["OK", "Cancel", "Tile", "Horizontal Scale:", "Repeat Edge Pixels", "Preview", "Radius", "Stretch To Fit"]


def test_a_word_photoshop_never_shows_becomes_the_one_it_does_by_swapping_confusable_characters() -> None:
    fix = Corrector([*STRINGS, "Solid Front Faces", "Triangle"])

    assert [fix.line(text) for text in ("0K", "oK", "Iile", "Horizontal Scaie:", "Repeat Edge Pixe1s", "Solid Eront Faces", "Iriangle")] == [
        "OK",
        "OK",
        "Tile",
        "Horizontal Scale:",
        "Repeat Edge Pixels",
        "Solid Front Faces",
        "Triangle",
    ]


def test_numbers_and_text_already_right_are_left_alone() -> None:
    fix = Corrector(STRINGS)

    assert [fix.line(text) for text in ("10", "12.5", "0", "Cancel", "observed-truth-probe copy")] == [
        "10",
        "12.5",
        "0",
        "Cancel",
        "observed-truth-probe copy",
    ]


def test_punctuation_read_around_a_known_word_is_kept() -> None:
    fix = Corrector(STRINGS)

    assert [fix.line(text) for text in ("Radius:", "Radlus:", "(Preview)", "Tile...")] == ["Radius:", "Radius:", "(Preview)", "Tile..."]


def test_letters_are_never_added_dropped_or_swapped_for_unconfusable_ones() -> None:
    fix = Corrector(["Calculator", "Numbers", "Tiny", "Letter", "Use Selection in Source to Calculator Colors"])

    assert [fix.line(text) for text in ("Calculate", "Number", "Tint", "Gutter", "Use Selection in Source to Calculate Colors")] == [
        "Calculate",
        "Number",
        "Tint",
        "Gutter",
        "Use Selection in Source to Calculate Colors",
    ]


def test_a_text_cursor_read_at_the_edge_of_a_value_is_dropped() -> None:
    fix = Corrector(STRINGS)

    assert [fix.line(text) for text in ("1|", "30|", "|Tile", "Radius: 10|", "|")] == ["1", "30", "Tile", "Radius: 10", "|"]


def test_a_capital_read_is_never_made_lower_case() -> None:
    fix = Corrector(["stylization:", "Settings"])

    assert [fix.line("Stylization:"), fix.line("settings")] == ["Stylization:", "Settings"]


def test_a_word_two_labels_fit_equally_well_is_not_guessed() -> None:
    fix = Corrector(["Coil", "Coll"])

    assert fix.line("Co1l") == "Co1l"


def test_between_equal_fits_the_one_keeping_letters_as_letters_wins() -> None:
    fix = Corrector(["OK", "0K"])

    assert [fix.line("oK"), fix.line("0k")] == ["OK", "0k"]


def test_mnemonic_markers_in_the_strings_do_not_reach_the_labels() -> None:
    fix = Corrector(["&Radius:", "R^adius:"])

    assert fix.line("Radlus:") == "Radius:"
