"""Change 1: add JPG classification without moving files."""
from pathlib import Path


def preview(folder):
    rows = []
    for path in sorted(Path(folder).iterdir()):
        if not path.is_file():
            continue
        category = {".txt": "Text", ".jpg": "Images"}.get(path.suffix, "Keep")
        rows.append({"source": path.name, "category": category,
                     "destination": None if category == "Keep"
                     else f"{category}/{path.name}"})
    return {"rows": rows}
