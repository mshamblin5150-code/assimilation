"""The dialog survey's overview: per dialog its text in reading order and each dropdown's choices,
kept local (the text is the program's own); and counts, which can be published."""

from __future__ import annotations

from scripts.adobe_observed_truth.dialog_overview import counts, overview

_ROWS = [
    {"item_id": "menu:Example Path@survey", "image": "a.png",
     "words": [{"text": "Joins:", "x": 30, "y": 110, "w": 40, "h": 14, "line": 2},
               {"text": "Example", "x": 10, "y": 8, "w": 60, "h": 14, "line": 0},
               {"text": "Path", "x": 74, "y": 8, "w": 30, "h": 14, "line": 0},
               {"text": "Corner", "x": 80, "y": 110, "w": 50, "h": 14, "line": 2}],
     "dropdowns": [{"at": [206, 118], "opened": True, "choices": ["Corner", "Round"]},
                   {"at": [206, 160], "opened": False, "choices": []}]},
    {"item_id": "menu:Plain@survey", "image": "b.png", "words": [], "dropdowns": []},
]


def test_the_overview_reads_each_dialog_in_order_with_its_dropdowns_choices() -> None:
    text = overview(_ROWS)

    assert text.index("## Example Path") < text.index("## Plain")
    assert "Example Path\nJoins: Corner" in text  # lines top to bottom, words left to right
    assert "- (206, 118): Corner | Round" in text
    assert "- (206, 160): no list opened" in text


def test_counts_say_how_much_was_seen_and_carry_no_text() -> None:
    assert counts(_ROWS) == {"dialogs": 2, "with_dropdowns": 1, "dropdowns": 2, "lists_opened": 1, "choices": 2}
