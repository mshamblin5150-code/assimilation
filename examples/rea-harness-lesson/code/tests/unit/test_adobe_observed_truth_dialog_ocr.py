"""Dialog OCR: the reader process's words, back in the dialog's pixels, corrected to Photoshop's labels."""

from __future__ import annotations

import json
import sys

import numpy as np

from scripts.adobe_observed_truth.dialog_surface import OCR_SCALE, Ocr
from scripts.adobe_observed_truth.ocr_correct import Corrector

# A stand-in reader: answers every image path with the same two words, in prepared (scaled) pixels.
ANSWER = {
    "words": [
        {"text": "Radlus:", "x": 30, "y": 60, "w": 90, "h": 30, "line": 0, "score": 0.9},
        {"text": "10", "x": 150, "y": 60, "w": 30, "h": 30, "line": 0, "score": 0.9},
    ],
    "error": None,
}
READER = [sys.executable, "-c", f"import sys\nfor _ in sys.stdin: print({json.dumps(json.dumps(ANSWER))}, flush=True)"]


def test_words_come_back_corrected_and_in_the_dialogs_own_pixels() -> None:
    ocr = Ocr(READER, corrector=Corrector(["Radius:"]))
    try:
        words = ocr.words(np.full((40, 80, 3), 40, dtype=np.uint8))
    finally:
        ocr.close()

    assert [(w["text"], w["x"], w["y"], w["w"]) for w in words] == [
        ("Radius:", 30 // OCR_SCALE, 60 // OCR_SCALE, 90 // OCR_SCALE),
        ("10", 150 // OCR_SCALE, 60 // OCR_SCALE, 30 // OCR_SCALE),
    ]


def test_a_region_is_read_with_a_margin_of_the_dialog_round_it_kept_inside_the_dialog() -> None:
    """Text cropped tight to its box reads worse ("Press s me" live on 2026-11-10)."""
    from scripts.adobe_observed_truth.dialog_surface import DialogSurface

    class Recording:
        def __init__(self) -> None:
            self.shapes: list[tuple[int, ...]] = []

        def words(self, image: np.ndarray) -> list[dict]:
            self.shapes.append(image.shape[:2])
            return [{"text": "Press"}, {"text": "me"}]

    class Still(DialogSurface):
        def shot(self) -> np.ndarray:
            return np.zeros((100, 200, 3), dtype=np.uint8)

    reader = Recording()
    surface = Still(hwnd=0, pid=0, ocr=reader)

    texts = [surface.read_text((50, 40, 90, 60)), surface.read_text((0, 0, 30, 20))]

    assert (texts, reader.shapes) == (["Press me", "Press me"], [(32, 52), (26, 36)])


def test_a_dialog_whose_window_is_gone_says_so_instead_of_failing_in_windows_calls() -> None:
    import pytest

    from scripts.adobe_observed_truth.controls import DialogClosed
    from scripts.adobe_observed_truth.dialog_surface import DialogSurface
    from scripts.adobe_observed_truth.input_plan import chord

    gone = DialogSurface(hwnd=0, pid=0)  # no window has handle 0

    with pytest.raises(DialogClosed):
        gone.send(chord("tab"))
    with pytest.raises(DialogClosed):
        gone.shot()


def test_a_tooltip_or_a_shadow_is_not_something_the_dialog_opened() -> None:
    """Hovering in Hue/Saturation raised a tooltip; counted as an open list, it drew an Escape
    that cancelled the dialog (2026-11-10). Its list is a DroverLord window with a shadow."""
    from scripts.adobe_observed_truth.dialog_surface import is_popup

    classes = ["tooltips_class32", "SysShadow", "DroverLord - Window Class", "#32768"]

    assert [is_popup(c) for c in classes] == [False, False, True, True]


def test_photoshops_drag_feedback_overlay_is_not_something_the_dialog_opened() -> None:
    """Image Size stopped at a different control on each run with a window "left open"
    (2026-11-11); its class was PSDragFeedback, Photoshop's transient drag overlay: no list to
    close, and while it counted, input could not refocus the dialog."""
    from scripts.adobe_observed_truth.dialog_surface import is_popup

    assert is_popup("PSDragFeedback") is False
