"""Finding a dialog's dropdowns by sight (the dialog survey: look, don't drive).

Illustrator draws its dropdowns itself: a dark box holding the current value, with a small light
down-chevron at its right edge (about 9 x 5 pixels, Offset Path's Joins, 2026-11-25). The chevron
is matched against a V drawn here, on the dialog's light pixels; a match inside a word the OCR read
is a letter v (Preview), not a dropdown.
"""

from __future__ import annotations

from typing import Any

import numpy as np

LIGHT = 140  # chevrons are light on the dark dialog; their soft edges fall to about 130
MATCH = 0.8


WIDTHS = (9, 10)  # most chevrons are 9 wide; some lists (Grid Colors) draw them 10 wide
SPINNER_GAP = (6, 16)  # a spinner's up arrow sits this many pixels above its down arrow
LOOKS = 4  # looks for a dropdown's list after the click, settle_s apart


def chevron(width: int = 9) -> np.ndarray:
    """A 5-high light V with arms three pixels thick, as Illustrator's dropdowns show (drawn, not
    copied): row r lights columns r-1..r+1 and width-2-r..width-r."""
    mark = np.zeros((5, width), dtype=np.uint8)
    for row in range(5):
        for col in (*range(row - 1, row + 2), *range(width - 2 - row, width + 1 - row)):
            if 0 <= col < width:
                mark[row, col] = 255
    return mark


def _in_word(x: float, y: float, words: list[dict[str, Any]]) -> bool:
    return any(len(str(w.get("text", ""))) >= 2 and w["x"] - 2 <= x <= w["x"] + w["w"] + 2
               and w["y"] - 2 <= y <= w["y"] + w["h"] + 2 for w in words)


def _matches(light: np.ndarray, *, up: bool) -> list[tuple[float, float, float]]:
    """(score, centre x, centre y) of every chevron-shaped spot, down or (`up`) up."""
    import cv2

    out = []
    for width in WIDTHS:
        mark = chevron(width)[::-1] if up else chevron(width)
        if light.shape[0] < mark.shape[0] or light.shape[1] < mark.shape[1]:
            continue
        scores = cv2.matchTemplate(light, mark, cv2.TM_CCOEFF_NORMED)
        out += [(float(scores[y, x]), x + width / 2, y + 2.5) for y, x in zip(*np.nonzero(scores >= MATCH))]
    return out


def find_dropdowns(gray: np.ndarray, words: list[dict[str, Any]]) -> list[tuple[float, float]]:
    """Centres of the dropdown chevrons in a greyscale dialog image (`words`: its OCR words with
    boxes in the same pixels), top to bottom. A down arrow just under an up arrow is a spinner's,
    not a dropdown's."""
    light = np.where(gray >= LIGHT, 255, 0).astype(np.uint8)
    if not light.any():
        return []
    ups = _matches(light, up=True)
    seen: list[tuple[float, float]] = []
    found: list[tuple[float, float]] = []
    for _, cx, cy in sorted(_matches(light, up=False), reverse=True):
        if any(abs(cx - sx) < 8 and abs(cy - sy) < 8 for sx, sy in seen):
            continue  # the same chevron, a pixel over or matched at the other width
        seen.append((cx, cy))
        spinner = any(abs(cx - ux) <= 3 and SPINNER_GAP[0] <= cy - uy <= SPINNER_GAP[1] for _, ux, uy in ups)
        if not spinner and not _in_word(cx, cy, words):
            found.append((cx, cy))
    return sorted(found, key=lambda p: (p[1], p[0]))


def survey_dialog(surface: Any, *, settle_s: float = 0.5) -> dict[str, Any]:
    """Look at one open dialog (a dialog_surface.DialogSurface): its text read, and each dropdown
    opened by a click on its chevron, its list read, then closed. No key is sent and no choice is
    clicked, so nothing in the dialog changes. Returns the image, the OCR words, and per dropdown
    where it is, whether a list opened, and the list's lines."""
    import time

    from PIL import Image

    from .input_plan import click

    image = surface.shot()
    words = surface.words()
    gray = np.asarray(Image.fromarray(image[..., :3]).convert("L"))
    dropdowns = []
    for x, y in find_dropdowns(gray, words):
        at = [round(x), round(y)]
        surface.send(click((at[0], at[1])))
        opened = False
        for _ in range(LOOKS):  # a long list (Color Settings' CMYK profiles) shows late
            time.sleep(settle_s)
            if opened := surface.popups() > 0:
                break
        choices = surface.popup_lines() if opened else []
        surface.close_popups()
        dropdowns.append({"at": at, "opened": opened, "choices": choices})
    return {"image": image, "words": words, "dropdowns": dropdowns}
