"""Fictional starting checkpoint: text and unknown files, preview only."""
from pathlib import Path


def preview(folder):
    rows = []
    for path in sorted(Path(folder).iterdir()):
        if not path.is_file():
            continue
        category = "Text" if path.suffix == ".txt" else "Keep"
        rows.append({"source": path.name, "category": category,
                     "destination": None if category == "Keep"
                     else f"{category}/{path.name}"})
    return {"rows": rows}
