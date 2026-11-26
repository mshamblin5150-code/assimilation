"""Finding a dialog's dropdowns by sight: the small light down-chevron at a dropdown's right edge,
never a letter v inside a word the OCR read."""

from __future__ import annotations

import numpy as np

from scripts.adobe_observed_truth.dialog_dropdowns import chevron, find_dropdowns, survey_dialog


def _dialog_with(points: list[tuple[int, int]]) -> np.ndarray:
    image = np.full((200, 300), 83, dtype=np.uint8)  # a dark grey dialog
    mark = chevron()
    for x, y in points:
        h, w = mark.shape
        image[y:y + h, x:x + w] = np.maximum(image[y:y + h, x:x + w], mark)
    return image


def test_each_chevron_is_a_dropdown_and_a_v_inside_a_word_is_not() -> None:
    image = _dialog_with([(200, 40), (200, 100), (60, 160)])
    words = [{"text": "Preview", "x": 30, "y": 150, "w": 90, "h": 24}]  # the third mark sits in a word

    found = find_dropdowns(image, words)

    assert [(round(x), round(y)) for x, y in found] == [(204, 42), (204, 102)]


# A chevron as the dialog draws it: arms about three pixels thick with soft edges (drawn here to the
# shape measured on a real capture, 2026-11-25).
_SOFT_CHEVRON = np.array([
    [230, 165, 75, 75, 75, 75, 75, 130, 240],
    [220, 255, 190, 75, 75, 75, 145, 255, 240],
    [75, 190, 255, 220, 85, 190, 255, 220, 85],
    [75, 75, 165, 255, 245, 255, 200, 85, 75],
    [75, 75, 75, 145, 255, 190, 75, 75, 75],
], dtype=np.uint8)


def test_a_soft_thick_chevron_is_a_dropdown() -> None:
    image = np.full((200, 300), 75, dtype=np.uint8)
    image[115:120, 202:211] = _SOFT_CHEVRON

    found = find_dropdowns(image, [])

    assert [(round(x), round(y)) for x, y in found] == [(206, 118)]


# Some dropdowns (a colour list) draw the chevron a pixel wider.
_WIDE_CHEVRON = np.array([
    [235, 255, 145, 75, 75, 75, 75, 190, 255, 190],
    [110, 220, 255, 165, 75, 85, 200, 255, 200, 85],
    [75, 85, 220, 255, 190, 220, 255, 190, 75, 75],
    [75, 75, 75, 190, 255, 255, 145, 75, 75, 75],
    [75, 75, 75, 75, 165, 130, 75, 75, 75, 75],
], dtype=np.uint8)


def test_a_wider_chevron_is_a_dropdown() -> None:
    image = np.full((200, 300), 75, dtype=np.uint8)
    image[100:105, 150:160] = _WIDE_CHEVRON

    found = find_dropdowns(image, [])

    assert [(round(x), round(y)) for x, y in found] == [(155, 102)]


def test_a_spinners_down_arrow_under_its_up_arrow_is_not_a_dropdown() -> None:
    image = np.full((200, 300), 75, dtype=np.uint8)
    image[100:105, 50:59] = _SOFT_CHEVRON[::-1]  # the up arrow
    image[111:116, 50:59] = _SOFT_CHEVRON        # the down arrow, just under it
    image[150:155, 200:209] = _SOFT_CHEVRON      # a dropdown, alone

    found = find_dropdowns(image, [])

    assert [(round(x), round(y)) for x, y in found] == [(204, 152)]


def test_a_plain_dialog_has_no_dropdowns() -> None:
    assert find_dropdowns(np.full((200, 300), 83, dtype=np.uint8), []) == []


class _Dialog:
    """A dialog with dropdowns whose lists open as windows (Illustrator's), recording all input."""

    def __init__(self, image: np.ndarray, lists: dict[tuple[int, int], list[str]]) -> None:
        self.image, self.lists = image, lists
        self.sent: list[object] = []
        self.open: list[str] | None = None

    def shot(self) -> np.ndarray:
        return np.stack([self.image] * 3, axis=-1)

    def words(self) -> list[dict]:
        return [{"text": "Joins:", "x": 10, "y": 30, "w": 50, "h": 20, "line": 0}]

    def send(self, events: list[object]) -> None:
        self.sent += events
        (x, y) = next((e.x, e.y) for e in events if hasattr(e, "x"))
        self.open = next((v for (lx, ly), v in self.lists.items() if abs(lx - x) <= 2 and abs(ly - y) <= 2), None)

    def popups(self) -> int:
        return int(self.open is not None)

    def popup_lines(self) -> list[str]:
        return list(self.open or [])

    def close_popups(self) -> None:
        self.open = None


def test_a_survey_reads_the_dialog_and_each_dropdowns_choices_and_changes_nothing() -> None:
    image = np.full((200, 300), 75, dtype=np.uint8)
    image[40:45, 200:209] = _SOFT_CHEVRON
    image[100:105, 200:209] = _SOFT_CHEVRON  # a dropdown whose click opens nothing
    dialog = _Dialog(image, {(204, 42): ["Miter", "Round", "Bevel"]})

    seen = survey_dialog(dialog, settle_s=0)

    assert seen["words"] == dialog.words()
    assert seen["dropdowns"] == [{"at": [204, 42], "opened": True, "choices": ["Miter", "Round", "Bevel"]},
                                 {"at": [204, 102], "opened": False, "choices": []}]
    # Only clicks on the chevrons: no key reaches the dialog, so no value changes.
    assert {type(e).__name__ for e in dialog.sent} <= {"MouseMove", "MouseDown", "MouseUp"}
    assert dialog.open is None


class _SlowDialog(_Dialog):
    """Its list window shows only at the third look (Color Settings' long CMYK list, 2026-11-25)."""

    looks = 0

    def popups(self) -> int:
        self.looks += 1
        return int(self.open is not None and self.looks >= 3)


def test_a_survey_waits_for_a_slow_list() -> None:
    image = np.full((200, 300), 75, dtype=np.uint8)
    image[40:45, 200:209] = _SOFT_CHEVRON
    dialog = _SlowDialog(image, {(204, 42): ["Coated FOGRA39", "U.S. Web Coated (SWOP) v2"]})

    seen = survey_dialog(dialog, settle_s=0)

    assert seen["dropdowns"] == [{"at": [204, 42], "opened": True,
                                  "choices": ["Coated FOGRA39", "U.S. Web Coated (SWOP) v2"]}]
