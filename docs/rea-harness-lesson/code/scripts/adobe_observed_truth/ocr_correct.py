"""Correct OCR against Photoshop's own interface strings.

Photoshop's binaries carry every label, button and option it shows as Adobe ZStrings
("$$$/Example/Key=English text": 21,911 distinct in Photoshop 2026). The list is extracted locally to
photoshop-ui-strings.txt in the local corpus folder and never published.

Correction is deliberately narrow, because Photoshop has thousands of near-identical labels
("Calculate"/"Calculator", "Radius"/"Radius:") and snapping to the nearest one damages text
that was read right. A word is changed only when Photoshop never shows it, and only into a word
it does show that differs solely by characters OCR confuses (0/O, 1/l/I, E/F, ...; a capital
read is never made lower case, since Photoshop also lists "stylization:" beside "Stylization"): same
length, nothing added or dropped, punctuation around it kept. Fewest swaps wins, then the fit
keeping letters as letters ("oK" -> "OK", not "0K"); two equally good fits: no guess.
Numbers are never changed: a field's value must be read as shown.
"""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

from .corpus import CORPUS

STRINGS_FILE = CORPUS / "photoshop-ui-strings.txt"
_NUMBER = re.compile(r"^[+\-]?\d+(?:[.,]\d+)?%?$")
_EDGES = re.compile(r"^(\W*)(.*?)(\W*)$")
# Characters OCR mistakes for one another in Photoshop's dialog font.
_CONFUSED = [set("0Oo"), set("1lIi|!"), set("IT"), set("EF"), set("5Ss"), set("8B"), set("2Z"), set("6G"), set("cC"), set("vV"), set("wW"), set("xX"), set("zZ")]


def _clean(text: str) -> str:
    """A string as drawn: mnemonic markers removed."""
    return text.replace("&&", "\0").replace("&", "").replace("^", "").replace("\0", "&")


def _confusable(a: str, b: str) -> bool:
    return any(a in group and b in group for group in _CONFUSED)


def _swaps(read: str, known: str) -> tuple[int, int] | None:
    """(confusable characters swapped, of those letters made digits or digits made letters) to
    turn `read` into `known`; None if anything else differs."""
    count = kind_changes = 0
    for a, b in zip(read, known, strict=True):
        if a != b:
            if not _confusable(a, b) or (a.isupper() and b.islower()):
                return None
            count += 1
            kind_changes += a.isdigit() != b.isdigit()
    return count, kind_changes


class Corrector:
    def __init__(self, strings: list[str]) -> None:
        self.words: set[str] = set()
        for text in strings:
            for word in _clean(text).split():
                core = _EDGES.match(word).group(2)
                if core:
                    self.words.add(core)
        self.by_length: dict[int, list[str]] = defaultdict(list)
        for word in self.words:
            self.by_length[len(word)].append(word)

    @classmethod
    def from_file(cls, path: Path = STRINGS_FILE) -> Corrector | None:
        return cls(path.read_text(encoding="utf-8").splitlines()) if path.exists() else None

    def word(self, word: str) -> str:
        if word.strip("|"):
            word = word.strip("|")  # a field's text cursor read as part of its value: "30|"
        before, core, after = _EDGES.match(word).groups()
        if not core or core in self.words or _NUMBER.match(core):
            return word
        best: list[str] = []
        fewest = (len(core) + 1, 0)
        for known in self.by_length.get(len(core), ()):
            swaps = _swaps(core, known)
            if swaps is None or swaps > fewest:
                continue
            if swaps < fewest:
                best, fewest = [known], swaps
            else:
                best.append(known)
        return f"{before}{best[0]}{after}" if len(best) == 1 else word

    def line(self, text: str) -> str:
        return " ".join(self.word(w) for w in text.split())
