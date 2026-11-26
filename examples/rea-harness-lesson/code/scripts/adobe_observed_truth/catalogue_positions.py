"""Give each catalogued control its position in its dialog's capture.

The catalogue (dialog-controls.jsonl) says what each dialog holds but not where, and its labels
describe controls rather than quote them ("Set Black Point eyedropper"), so the harness could
not place most mouse-only controls (2026-11-10). Annotators do not draw boxes, which vision
reading does imprecisely: each capture gets an overlay of numbered items found the way the
harness finds them live (D: drawn things, the same pixel analysis; T: text lines, the same OCR),
and the annotator names which items each control is. The catalogue keeps the union of those
items as fractions of the capture ("box": [x0, y0, x1, y1]), so positions hold at any scale.

    python -m scripts.adobe_observed_truth.catalogue_positions prepare --dataset <dir> --work <dir>
    python -m scripts.adobe_observed_truth.catalogue_positions merge --dataset <dir> --work <dir>
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from .corpus import CORPUS

Rect = tuple[int, int, int, int]
CAPTURES = CORPUS / "captures"


def apply_positions(
    row: dict[str, Any], answer: dict[str, list[str] | None], items: dict[str, Rect], size: tuple[int, int]
) -> dict[str, Any]:
    """`row` with each control's box: the union of the items its answer names (control index ->
    item ids), as fractions of the capture (`size` is height, width). A control with no answer,
    or naming an item the capture does not have, gets none: nothing is guessed."""
    height, width = size
    controls = []
    for index, control in enumerate(row["controls"]):
        named = answer.get(str(index)) or []
        rects = [items[i] for i in named if i in items]
        out = {k: v for k, v in control.items() if k != "box"}
        if named and len(rects) == len(named):
            x0, y0 = min(r[0] for r in rects), min(r[1] for r in rects)
            x1, y1 = max(r[2] for r in rects), max(r[3] for r in rects)
            out["box"] = [round(x0 / width, 4), round(y0 / height, 4), round(x1 / width, 4), round(y1 / height, 4)]
        controls.append(out)
    return {**row, "controls": controls}


def numbered_items(image: np.ndarray, lines: list[tuple[str, Rect]]) -> dict[str, dict[str, Any]]:
    """The capture's drawn things (D1...) and text lines (T1...), in reading order."""
    from .control_drivers import mouse_candidates

    drawn = sorted(mouse_candidates(image, [], [r for _, r in lines]), key=lambda r: (r[1] // 10, r[0]))
    text = sorted(lines, key=lambda line: (line[1][1] // 10, line[1][0]))
    items: dict[str, dict[str, Any]] = {}
    for n, rect in enumerate(drawn, 1):
        items[f"D{n}"] = {"rect": list(rect)}
    for n, (words, rect) in enumerate(text, 1):
        items[f"T{n}"] = {"rect": list(rect), "text": words}
    return items


def overlay(image: np.ndarray, items: dict[str, dict[str, Any]]) -> Any:
    """The capture with every item outlined and numbered: drawn things red, text lines blue."""
    from PIL import Image, ImageDraw, ImageFont

    scale = 2 if image.shape[1] < 900 else 1  # small dialogs are drawn larger so ids stay legible
    picture = Image.fromarray(image).convert("RGB").resize((image.shape[1] * scale, image.shape[0] * scale))
    draw = ImageDraw.Draw(picture)
    font = ImageFont.load_default(size=11 * scale)
    for item_id, item in items.items():
        x0, y0, x1, y1 = (v * scale for v in item["rect"])
        drawn = item_id.startswith("D")
        colour = (255, 40, 40) if drawn else (60, 140, 255)
        draw.rectangle((x0, y0, x1, y1), outline=colour, width=1)
        # Drawn things are numbered above their top-left corner, text lines below their
        # bottom-right, so the two never cover each other where a field holds its text.
        tag_w, tag_h = 7 * scale * len(item_id), 12 * scale
        tx, ty = (x0, y0 - tag_h) if drawn else (x1 - tag_w, y1)
        draw.rectangle((tx, ty, tx + tag_w, ty + tag_h), fill=colour)
        draw.text((tx + 1, ty), item_id, fill=(255, 255, 255), font=font)
    return picture


def prepare(dataset: Path, work: Path, captures: Path = CAPTURES) -> int:
    """An overlay and an items file for every catalogued capture (OCR text stays in `work`)."""
    from PIL import Image

    from .control_catalogue import load
    from .control_pass import _lines
    from .dialog_surface import Ocr

    work.mkdir(parents=True, exist_ok=True)
    ocr = Ocr()
    done = 0
    try:
        for row in load(dataset / "dialog-controls.jsonl"):
            source = captures / row["image"]
            target = work / f"{Path(row['image']).stem}.items.json"
            if not source.exists() or target.exists():
                continue
            image = np.asarray(Image.open(source).convert("RGB"))
            items = numbered_items(image, _lines(ocr.words(image)))
            overlay(image, items).save(work / f"{Path(row['image']).stem}.overlay.png")
            target.write_text(json.dumps({"size": list(image.shape[:2]), "items": items}), encoding="utf-8")
            done += 1
    finally:
        ocr.close()
    return done


def merge(dataset: Path, work: Path) -> dict[str, int]:
    """dialog-controls.jsonl rewritten with the boxes the answers give (work/*.answer.json)."""
    from .control_catalogue import load

    path = dataset / "dialog-controls.jsonl"
    rows, placed, total = [], 0, 0
    for row in load(path):
        stem = Path(row["image"]).stem
        items_file, answer_file = work / f"{stem}.items.json", work / f"{stem}.answer.json"
        if items_file.exists() and answer_file.exists():
            found = json.loads(items_file.read_text(encoding="utf-8"))
            items = {k: tuple(v["rect"]) for k, v in found["items"].items()}
            row = apply_positions(row, json.loads(answer_file.read_text(encoding="utf-8")), items, tuple(found["size"]))
        placed += sum("box" in c for c in row["controls"])
        total += len(row["controls"])
        rows.append(row)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    return {"controls": total, "with_box": placed}


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("step", choices=["prepare", "merge"])
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--work", type=Path, default=CORPUS / "catalogue-positions")
    args = parser.parse_args()
    if args.step == "prepare":
        print(f"prepared {prepare(args.dataset, args.work)} captures in {args.work}")
    else:
        print(json.dumps(merge(args.dataset, args.work)))


if __name__ == "__main__":
    main()
