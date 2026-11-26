"""Link inventory items to the decompiled binaries that mention them, as each binary lands.

Anchors are the app's own internal names (tool ids, panel ids, preference keys), searched as
string literals in the pseudocode. An item not found yet waits on the binaries still being
decompiled; each newly finished binary is scanned once, so reruns are cheap. A hit is a place
to read, not a verdict.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .inventory import Item


@dataclass(frozen=True)
class Link:
    status: Literal["found", "waiting", "not_found", "no_anchor"]
    binaries: tuple[str, ...]


def link(
    anchors: dict[str, list[str]], found_by_binary: dict[str, set[str]], pending: list[str]
) -> dict[str, Link]:
    links = {}
    for item_id, names in anchors.items():
        if not names:
            links[item_id] = Link("no_anchor", ())
            continue
        hits = tuple(sorted(b for b, found in found_by_binary.items() if found & set(names)))
        if hits:
            links[item_id] = Link("found", hits)
        else:
            links[item_id] = Link("waiting" if pending else "not_found", ())
    return links


def anchors_for(item: Item) -> list[str]:
    """Internal names distinctive enough to search for; menu command numbers are too common."""
    if item.kind == "tool":
        return [item.facts["tool_id"]]
    if item.kind == "panel":
        return [item.id.removeprefix("panel:")]
    if item.kind == "preference" and len(item.name) >= 6:
        return [item.name]
    if len(command := item.facts.get("command_name", "")) >= 6:  # Illustrator's named commands
        return [command]
    return []


# A whole string literal, or the default value of a localised "$$$/Example/key=value" literal
# (how Photoshop names its panels). Scan records carry this text, so editing it rescans everything.
MATCHER = r'"(?:\$\$\$/[^"=\n]*=)?({names})"'


def scan_record(anchors: set[str], found: set[str]) -> dict:
    return {"anchors": sorted(anchors), "matcher": MATCHER, "found": sorted(found)}


def is_current(record: dict, anchors: set[str]) -> bool:
    """Whether a binary's saved scan was made with these anchors and this matcher."""
    return record.get("anchors") == sorted(anchors) and record.get("matcher") == MATCHER


def scan_binary(pseudocode: Path, anchors: set[str]) -> set[str]:
    """Which anchors appear anywhere in one binary's pseudocode, as MATCHER defines it."""
    if not anchors:
        return set()
    pattern = re.compile(MATCHER.format(names="|".join(map(re.escape, sorted(anchors)))))
    found: set[str] = set()
    for path in (pseudocode / "functions").glob("*.c"):
        found.update(pattern.findall(path.read_text(encoding="utf-8", errors="replace")))
        if found == anchors:
            break
    return found


def main() -> None:
    """python -m scripts.adobe_observed_truth.code_links --corpus <dir> --dataset <dir> --app photoshop

    Scans only binaries decompiled since the last run (state kept in the dataset folder).
    """
    import argparse
    import json
    from collections import Counter

    from .rea_corpus import is_adobe_code, is_decompiled, is_skipped

    parser = argparse.ArgumentParser(description=main.__doc__)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--app", default="photoshop")
    args = parser.parse_args()
    with (args.dataset / "inventory.jsonl").open(encoding="utf-8") as handle:
        items = [Item(**json.loads(line)) for line in handle]
    anchors = {item.id: anchors_for(item) for item in items}
    wanted = {name for names in anchors.values() for name in names}
    manifest = json.loads((args.corpus / "manifest.json").read_text(encoding="utf-8"))
    entries = [e for e in manifest if e["app"] == args.app and is_adobe_code(e) and not is_skipped(e)]

    state_path = args.dataset / "code-scan-state.json"
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
    pending, scanned_now = [], 0
    for entry in entries:
        key = f"{entry['app']}/{entry['relative']}"
        work_dir = Path(entry["work_dir"])
        if not is_decompiled(work_dir):
            pending.append(key)
            continue
        if not is_current(state.get(key, {}), wanted):  # new binary, anchors or matcher
            state[key] = scan_record(wanted, scan_binary(work_dir / "pseudocode", wanted))
            scanned_now += 1
    state_path.write_text(json.dumps(state, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    found_by_binary = {key: set(value["found"]) for key, value in state.items()}
    links = link(anchors, found_by_binary, pending)
    with (args.dataset / "code-links.jsonl").open("w", encoding="utf-8", newline="\n") as out:
        for item_id, item_link in links.items():
            record = {
                "item_id": item_id,
                "status": item_link.status,
                "binaries": item_link.binaries,
            }
            out.write(json.dumps(record) + "\n")
    summary = {
        "binaries_decompiled": len(entries) - len(pending),
        "binaries_pending": pending,
        "scanned_this_run": scanned_now,
        "items_by_status": dict(Counter(item_link.status for item_link in links.values())),
    }
    (args.dataset / "code-links-summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({k: v for k, v in summary.items() if k != "binaries_pending"}))
    print(f"pending: {len(pending)} binaries, e.g. {pending[:6]}")


if __name__ == "__main__":
    main()
