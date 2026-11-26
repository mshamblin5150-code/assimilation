"""Attach each help claim to the inventory items it is about, or say why it cannot be.

Deterministic and conservative: a claim is matched only through names the help index
extracted (named tools, panels, menus, menu paths). The map records ids, links and
statuses, never the help's wording, so it can be published.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Literal

from .inventory import Item, load_inventory

Status = Literal["matched", "matched_by_context", "unmatched", "not_behaviour", "untestable_here"]


@dataclass(frozen=True)
class Disposition:
    claim_id: str
    status: Status
    item_ids: tuple[str, ...] = ()
    reason: str | None = None
    duplicate_of: str | None = None


def map_claims(claims: Iterable[dict[str, Any]], inventory: list[Item]) -> list[Disposition]:
    names = _name_index(inventory)
    menus = [(_norm(item.path), item.id) for item in inventory if item.kind in _MENU_KINDS]
    tools = [
        (_norm(item.name.removesuffix(" Tool")), item.id)
        for item in inventory
        if item.kind == "tool"
    ]
    out = []
    first_seen: dict[str, str] = {}
    for claim in claims:
        sentence = _norm(claim["text"]).rstrip(".")
        duplicate_of = first_seen.setdefault(sentence, claim["claim_id"])
        duplicate = None if duplicate_of == claim["claim_id"] else duplicate_of
        if excluded := _excluded(claim):
            out.append(Disposition(claim["claim_id"], *excluded, duplicate_of=duplicate))
            continue
        features = claim["features"]
        found: list[str] = []
        for named in features.get("named", []):
            kind = _NAMED_KIND.get(named["kind"], named["kind"])
            name = _norm(named["name"])
            hits = names.get((kind, name), [])
            if not hits and kind == "tool":
                # "Type tool" is the family of "Horizontal Type Tool" and "Vertical Type Tool".
                hits = [item_id for tool, item_id in tools if tool.endswith(f" {name}")]
            found.extend(hits)
        for menu_path in features.get("menu_paths", []):
            wanted = _norm(menu_path)
            found.extend(
                item_id for path, item_id in menus if path == wanted or path.endswith(f"> {wanted}")
            )
        status: Status = "matched"
        if not found:
            # The sentence names nothing itself; its section ("Move tool") supplies the subject.
            status = "matched_by_context"
            for phrase in features.get("context", {}).get("named", []):
                name, _, kind_word = phrase.rpartition(" ")
                kind = _CONTEXT_KIND.get(kind_word.lower())
                if kind:
                    found.extend(names.get((kind, _norm(name)), []))
        item_ids = tuple(dict.fromkeys(found))
        if not item_ids:
            status = "unmatched"
        out.append(Disposition(claim["claim_id"], status, item_ids, duplicate_of=duplicate))
    return out


# Section headings name their subject as "<name> <kind>": "Move tool", "Layers panel".
_CONTEXT_KIND = {
    "tool": "tool",
    "panel": "panel",
    "command": "menu",
    "dialog": "menu",
    "filter": "menu",
    "adjustment": "menu",
}


# Pages about the product rather than its behaviour, by help-site section.
_NOT_BEHAVIOUR_PAGES = (
    ("/whats-new/", "release notes"),
    ("release-notes", "release notes"),
    ("technical-requirements", "system requirements"),
    ("system-requirements", "system requirements"),
)
CLOUD = re.compile(
    r"\b(generative|firefly|cloud documents?|content credentials|adobe express|"
    r"share for review|creative cloud libraries)\b",
    re.IGNORECASE,
)
# macOS-only means only Mac modifier keys are given ("Command+T", "Option-drag"): a mention of
# macOS alone ("Return on macOS", a Mac menu path) describes behaviour Windows has too.
_MAC_ONLY = re.compile(r"\b(command|cmd|option)\s*[-+]\s*\w", re.IGNORECASE)
_WINDOWS = re.compile(r"\b(windows|win|ctrl|alt)\b", re.IGNORECASE)


def _excluded(claim: dict[str, Any]) -> tuple[Status, tuple[str, ...], str] | None:
    """(status, item_ids, reason) for a claim this harness cannot test, else None."""
    for marker, reason in _NOT_BEHAVIOUR_PAGES:
        if marker in claim["url"]:
            return "not_behaviour", (), reason
    text = claim["text"]
    if CLOUD.search(text):
        return "untestable_here", (), "cloud or generative AI service"
    if _MAC_ONLY.search(text) and not _WINDOWS.search(text):
        return "untestable_here", (), "macOS only"
    return None


_MENU_KINDS = ("menu_command", "submenu")
# The help index's names for things that the inventory files under menus.
_NAMED_KIND = {kind: "menu" for kind in ("menu", "command", "dialog", "filter", "adjustment")}


def _name_index(inventory: list[Item]) -> dict[tuple[str, str], list[str]]:
    index: dict[tuple[str, str], list[str]] = {}
    for item in inventory:
        if item.kind == "tool":
            key = ("tool", _norm(item.name.removesuffix(" Tool")))
        elif item.kind == "panel":
            key = ("panel", _norm(item.name))
        elif item.kind in _MENU_KINDS:
            key = ("menu", _norm(item.name))
        else:
            continue
        index.setdefault(key, []).append(item.id)
    return index


def _norm(name: str) -> str:
    return " ".join(name.replace("…", "").replace("...", "").lower().split())


def main() -> None:
    """python -m scripts.adobe_observed_truth.claim_map --claims <claims.jsonl> --dataset <dir>"""
    import argparse
    import json
    from collections import Counter
    from pathlib import Path

    parser = argparse.ArgumentParser(description=main.__doc__)
    parser.add_argument("--claims", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True, help="holds inventory.jsonl")
    parser.add_argument("--app", default="photoshop")
    args = parser.parse_args()
    inventory = load_inventory(args.dataset / "inventory.jsonl")
    with args.claims.open(encoding="utf-8") as handle:
        claims = [c for c in map(json.loads, handle) if c["app"] == args.app]
    dispositions = map_claims(claims, inventory)
    unmatched_names: Counter[str] = Counter()
    with (args.dataset / "claim-map.jsonl").open("w", encoding="utf-8", newline="\n") as out:
        for source, disposition in zip(claims, dispositions, strict=True):
            # Ids, links and our statuses only: the help's wording stays out of the repo.
            record = {
                "claim_id": disposition.claim_id,
                "url": source["url"],
                "strength": source.get("strength"),
                "status": disposition.status,
                "item_ids": list(disposition.item_ids),
                "reason": disposition.reason,
                "duplicate_of": disposition.duplicate_of,
            }
            out.write(json.dumps(record, sort_keys=True) + "\n")
            if disposition.status == "unmatched":
                for named in source["features"].get("named", []):
                    unmatched_names[f"{named['kind']}:{named['name']}"] += 1
    matched_items = {item_id for d in dispositions for item_id in d.item_ids}
    summary = {
        "app": args.app,
        "claims": len(dispositions),
        "by_status": dict(Counter(d.status for d in dispositions)),
        "by_reason": dict(Counter(d.reason for d in dispositions if d.reason)),
        "duplicates": sum(d.duplicate_of is not None for d in dispositions),
        "inventory_items": len(inventory),
        "inventory_items_with_a_claim": len(matched_items),
        "inventory_items_without_a_claim_by_kind": dict(
            Counter(item.kind for item in inventory if item.id not in matched_items)
        ),
        "top_unmatched_names": unmatched_names.most_common(40),
    }
    (args.dataset / "claim-map-summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({k: summary[k] for k in ("claims", "by_status", "by_reason", "duplicates")}))


if __name__ == "__main__":
    main()
