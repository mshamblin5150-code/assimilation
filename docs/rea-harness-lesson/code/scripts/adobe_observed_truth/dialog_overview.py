"""The dialog survey as something to read: per dialog its text top to bottom and each dropdown's
choices (runner_illustrator survey_dialog rows). The text is the program's own, so the overview
stays beside the captures; only counts are published.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _lines(words: list[dict[str, Any]]) -> list[str]:
    rows: dict[int, list[dict[str, Any]]] = {}
    for word in words:
        rows.setdefault(word.get("line", 0), []).append(word)
    ordered = sorted(rows.values(), key=lambda ws: min(w["y"] for w in ws))
    return [" ".join(w["text"] for w in sorted(ws, key=lambda w: w["x"])) for ws in ordered]


def _name(item_id: str) -> str:
    return item_id.split(":", 1)[-1].split("@", 1)[0]


def overview(rows: list[dict[str, Any]]) -> str:
    """Markdown: one section per dialog, in the order given."""
    out = ["# Dialog survey", ""]
    for row in rows:
        out += [f"## {_name(row['item_id'])}", "", f"Capture: {row['image']}", "", *_lines(row["words"]), ""]
        if row["dropdowns"]:
            out.append("Dropdowns:")
            for d in row["dropdowns"]:
                listed = " | ".join(d["choices"]) if d["opened"] else "no list opened"
                out.append(f"- ({d['at'][0]}, {d['at'][1]}): {listed}")
            out.append("")
    return "\n".join(out)


def counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    dropdowns = [d for row in rows for d in row["dropdowns"]]
    return {"dialogs": len(rows), "with_dropdowns": sum(bool(row["dropdowns"]) for row in rows),
            "dropdowns": len(dropdowns), "lists_opened": sum(d["opened"] for d in dropdowns),
            "choices": sum(len(d["choices"]) for d in dropdowns)}


def main() -> None:
    """python -m scripts.adobe_observed_truth.dialog_overview <dialog-survey-full.jsonl>: write the
    overview beside it (dialog-survey-overview.md) and print the counts."""
    import argparse

    parser = argparse.ArgumentParser(description=main.__doc__)
    parser.add_argument("survey", type=Path)
    args = parser.parse_args()
    latest: dict[str, dict[str, Any]] = {}
    for line in args.survey.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            latest[row["item_id"]] = row  # a dialog surveyed again: its last look
    rows = list(latest.values())
    (args.survey.parent / "dialog-survey-overview.md").write_text(overview(rows), encoding="utf-8")
    print(json.dumps(counts(rows)))


if __name__ == "__main__":
    main()
