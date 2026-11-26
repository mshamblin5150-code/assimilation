"""What an Illustrator command did to a document, from vector snapshots before and after.

A snapshot (runner_illustrator's SNAPSHOT_JS) lists the document's page items, each as plain facts
(type, bounds in milli-points, point count, closed, fill and stroke, stroke width, opacity, child
count, text length) and the document's own facts (artboards, layers, swatches, symbols, graphic
styles, selection, colour space). The change is what disappeared and what appeared; items of the
same type that disappeared and appeared are paired in order, so a moved or recoloured path counts
as a changed field, not as one removed and one added. This is the Illustrator counterpart of the
Photoshop pixel change: it says what kind of thing a command did, not how it looks.
"""

from __future__ import annotations

import json
from collections import Counter
from typing import Any


def _key(item: dict[str, Any]) -> str:
    return json.dumps(item, sort_keys=True)


def vector_change(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    """Counts of items added and removed by type, how many paired items changed each field, and
    each document fact that changed as [before, after]."""
    old, new = Counter(map(_key, before["items"])), Counter(map(_key, after["items"]))
    gone = [json.loads(k) for k in (old - new).elements()]
    came = [json.loads(k) for k in (new - old).elements()]
    fields: Counter[str] = Counter()
    unpaired_came = []
    for item in came:
        match = next((g for g in gone if g.get("type") == item.get("type")), None)
        if match is None:
            unpaired_came.append(item)
            continue
        gone.remove(match)
        fields.update(k for k in sorted(set(match) | set(item)) if match.get(k) != item.get(k))
    document = {k: [before["document"].get(k), after["document"].get(k)]
                for k in sorted(set(before["document"]) | set(after["document"]))
                if before["document"].get(k) != after["document"].get(k)}
    added = dict(Counter(i.get("type") for i in unpaired_came))
    removed = dict(Counter(i.get("type") for i in gone))
    return {"changed": bool(added or removed or fields or document), "added": added, "removed": removed,
            "fields": dict(fields), "document": document,
            "items_before": len(before["items"]), "items_after": len(after["items"])}
