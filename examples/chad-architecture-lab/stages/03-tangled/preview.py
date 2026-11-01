"""INTENTIONALLY TANGLED teaching fixture; not a recommended implementation."""
from pathlib import Path

_last_rows = []


def preview(folder):
    # Deliberate shortcut: a later call changes previously returned rows.
    _last_rows.clear()
    for path in sorted(Path(folder).iterdir()):
        if not path.is_file():
            continue
        category = {".txt": "Text", ".jpg": "Images"}.get(path.suffix, "Keep")
        _last_rows.append({"source": path.name, "category": category,
                     "destination": None if category == "Keep"
                     else f"{category}/{path.name}"})
    # Deliberate shortcut: summary knows the classification rule a second time.
    counts = {}
    for path in sorted(Path(folder).iterdir()):
        if not path.is_file():
            continue
        category = {".txt": "Text", ".jpg": "Images"}.get(path.suffix, "Keep")
        counts[category] = counts.get(category, 0) + 1
    return {"rows": _last_rows, "counts": counts}
