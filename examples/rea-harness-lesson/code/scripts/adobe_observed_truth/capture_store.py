"""Keep the harness's dialog captures small: one file per distinct image.

Every run captures each dialog it opens, so most dialogs are captured again and again, byte
for byte the same (499 of 1,076 files on 2026-11-10). REA does not need the files: a results
row records each capture's name and SHA-256 inside its Evidence, and a parity observation
carries its screenshot inline. The files serve the catalogue (dialog-controls.jsonl names
some), the OCR answer key and debugging. So duplicates go, one copy stays, and
captures-manifest.jsonl maps every name ever written to the copy kept.

    python -m scripts.adobe_observed_truth.capture_store --captures <dir> --dataset <dir> [--apply]
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path

from .corpus import CORPUS
from typing import Any


def plan_dedupe(files: list[tuple[str, str, float]], pinned: set[str]) -> list[dict[str, Any]]:
    """For (name, sha256, mtime) files: which file each name's image is kept as. The kept copy
    of an image is a pinned name if there is one, else the oldest."""
    by_hash: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for name, sha, mtime in files:
        by_hash[sha].append((name, mtime))
    keep = {
        sha: min(names, key=lambda n: (n[0] not in pinned, n[1], n[0]))[0] for sha, names in by_hash.items()
    }
    return [{"name": name, "sha256": sha, "kept_as": keep[sha]} for name, sha, _ in files]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--captures", type=Path, default=CORPUS / "captures")
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--apply", action="store_true", help="delete the duplicates (default: report only)")
    args = parser.parse_args()

    pinned = {
        json.loads(line).get("image")
        for line in (args.dataset / "dialog-controls.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    }
    files = [(p.name, _sha256(p), p.stat().st_mtime) for p in sorted(args.captures.glob("*.png"))]
    plan = plan_dedupe(files, {n for n in pinned if n})
    extra = [p for p in plan if p["kept_as"] != p["name"]]
    freed = sum((args.captures / p["name"]).stat().st_size for p in extra)
    print(f"{len(files)} captures, {len(files) - len(extra)} distinct; {len(extra)} duplicates, {freed / 1e6:.1f} MB")
    if not args.apply:
        print("report only: run with --apply to delete the duplicates")
        return
    manifest = args.captures.parent / "captures-manifest.jsonl"
    with manifest.open("a", encoding="utf-8", newline="\n") as out:  # names from earlier passes stay
        for entry in plan:
            out.write(json.dumps(entry) + "\n")
    for entry in extra:
        (args.captures / entry["name"]).unlink()
    print(f"deleted {len(extra)}; every name resolves through {manifest}")


if __name__ == "__main__":
    main()
