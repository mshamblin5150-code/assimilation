"""A decompiled binary's functions, for reading live observations against the decomp.

REA's Ghidra decompile journal (pseudocode/decompile-journal.jsonl) lists every function with its
address, name and body ranges. FunctionIndex answers which function holds an address (a return
address the stack sampler found, mapped to Ghidra's addresses) and which functions a function's
pseudocode names: its callees, and the callbacks it passes on, which is where a control's handler
is usually registered. The index is kept beside the journal (local: never published).
"""

from __future__ import annotations

import bisect
import json
import re
from collections.abc import Iterable
from pathlib import Path

_IDENTIFIER = re.compile(r"[A-Za-z_~][A-Za-z0-9_]*(?:::[A-Za-z_~][A-Za-z0-9_]*)*")
_UNNAMED = re.compile(r"FUN_([0-9a-f]{6,16})")


class FunctionIndex:
    def __init__(self, functions: Iterable[tuple[str, str, list[tuple[int, int]]]]):
        """`functions`: (address, name, body ranges as inclusive (start, end))."""
        self._rows = list(functions)
        self._pieces = sorted((start, end, address) for address, _, ranges in self._rows for start, end in ranges)
        self._starts = [p[0] for p in self._pieces]
        self._named: dict[str, str] = {}
        for address, name, _ in self._rows:
            self._named.setdefault(name, address)

    @classmethod
    def from_journal(cls, lines: Iterable[str]) -> FunctionIndex:
        functions = []
        for line in lines:
            if not line.strip():
                continue
            record = json.loads(line)
            ranges = [(int(r["start"], 16), int(r["end"], 16)) for r in (record.get("body") or {}).get("ranges", [])]
            if ranges and record["address"].startswith("0x"):
                functions.append((record["address"], record["name"], ranges))
        return cls(functions)

    def containing(self, address: int) -> str | None:
        """The function whose body holds `address` (a Ghidra address), or None."""
        at = bisect.bisect_right(self._starts, address) - 1
        while at >= 0:
            start, end, function = self._pieces[at]
            if start <= address <= end:
                return function
            if address - start > 1 << 24:  # no body is this long: stop looking back
                return None
            at -= 1
        return None

    def callees(self, pseudocode: str) -> list[str]:
        """The functions a function's pseudocode names (calls, and functions passed as values),
        by address, other than itself; names the journal does not hold are not in this binary."""
        header = pseudocode.split("{", 1)[0].split("(", 1)[0]
        own = (_IDENTIFIER.findall(header) or [None])[-1]
        found = set()
        for token in set(_IDENTIFIER.findall(pseudocode)) - {own}:
            if token in self._named:
                found.add(self._named[token])
            elif unnamed := _UNNAMED.fullmatch(token):
                found.add(f"0x{unnamed.group(1)}")
        return sorted(found, key=lambda a: int(a, 16))

    def rows(self) -> list[tuple[str, str, list[tuple[int, int]]]]:
        return list(self._rows)


def load_index(work_dir: Path) -> FunctionIndex:
    """The index of one decompiled binary, scanned from its journal once and kept beside it."""
    kept = work_dir / "function-index.json"
    if kept.exists():
        rows = json.loads(kept.read_text(encoding="utf-8"))
        return FunctionIndex((a, n, [tuple(r) for r in ranges]) for a, n, ranges in rows)
    with (work_dir / "pseudocode" / "decompile-journal.jsonl").open(encoding="utf-8") as journal:
        index = FunctionIndex.from_journal(journal)
    kept.write_text(json.dumps(index.rows()), encoding="utf-8")
    return index
