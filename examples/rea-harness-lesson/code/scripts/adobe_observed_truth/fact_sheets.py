"""One fact sheet per Photoshop feature: what the mapping knows that is needed to rebuild it.

The goal of the mapping (2026-11-24) is enough to rebuild every feature, not every code path.
A sheet joins, for one inventory item: its settings as Photoshop recorded them (key, type, unit,
default), the range Photoshop accepts (read back from the sweep's far-out probes) and what each
value tried did to the test chart; what it did in the document states that change it (pass B for
filters, adjustments and fills; pass C for tools); the decompiled functions that ran only for it,
by binary (feature-code.jsonl); and the code found behind its dialog's controls (control-code.jsonl).
Only numbers, Photoshop's scripting keys and labels already in the dataset are carried: no
pixels, no interface text.
"""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Iterable
from typing import Any

from .document_states import STATES
from .sweeps import FAR

Row = dict[str, Any]


def _pixels(row: Row | None) -> Row | None:
    pixels = ((row or {}).get("observations") or {}).get("pixels")
    return pixels if isinstance(pixels, dict) else None


def _changed(row: Row | None) -> float | None:
    pixels = _pixels(row)
    return pixels.get("changed_fraction") if pixels else None


def _latest(results: Iterable[Row]) -> dict[str, Row]:
    latest: dict[str, Row] = {}
    for row in results:
        latest[row["item_id"]] = row
    return latest


def _used(row: Row, key: str) -> Any:
    sweep = (row.get("observations") or {}).get("sweep") or {}
    return next((s.get("default") for s in sweep.get("used") or [] if s.get("key") == key), None)


def _anchors(key: str, codes: set[str], declared: list[Row]) -> list[Row]:
    """The plug-in settings whose 4-char code is this key's: the functions comparing that code,
    and per choice the functions comparing the choice's code."""
    return [{"binary": binary, "code": s["code"], "functions": sorted(s.get("functions") or []),
             "choices": [{"code": c["code"], "functions": sorted(c.get("functions") or [])}
                         for c in s.get("choices") or []]}
            for binary, s in declared if s["code"] in codes]


def _setting(setting: Row, event: str, rows: dict[str, Row], anchors: list[Row]) -> Row:
    key, default = setting["key"], setting.get("default")
    tried, bounds = [], {"min": None, "max": None}
    for item_id, row in rows.items():
        if not item_id.startswith(f"sweep:{event}:"):
            continue
        name = item_id.split(":", 2)[2]
        if name.startswith("default#"):
            if name != "default#1":
                continue
            value = default
        elif name.startswith(f"{key}="):
            value = json.loads(name[len(key) + 1:])
        else:
            continue
        used = _used(row, key) if row.get("status") == "ok" else None
        if isinstance(value, (int, float)) and not isinstance(value, bool) and abs(value) == FAR:
            if used == value:  # taken as given: no clamp within the probe's span
                bounds["accepts_far_values"] = True
            else:
                bounds["min" if value < 0 else "max"] = used
        tried.append({"value": value, "used": used, "status": row.get("status"), "changed_fraction": _changed(row),
                      "mean_delta": (_pixels(row) or {}).get("mean_delta")})
    numeric = all(isinstance(t["value"], (int, float)) and not isinstance(t["value"], bool) for t in tried)
    if numeric:
        tried.sort(key=lambda t: t["value"])
    sheet = {k: setting[k] for k in ("key", "type", "unit", "default", "choices") if k in setting}
    return {**sheet, "range": bounds if setting["type"] in ("integer", "double", "unit") else None, "tried": tried,
            "code": anchors}


def _states(item_id: str, rows: dict[str, Row]) -> dict[str, Row]:
    """Per document state, the feature's run there: the applied effect (`@chart@<state>`) when
    there is one, else the command or tool use (`@<state>`, `@use@<state>`)."""
    found: dict[str, tuple[int, Row]] = {}
    for run_id, row in rows.items():
        parts = run_id.split("@")
        if parts[0] != item_id or len(parts) < 2 or parts[-1] not in STATES:
            continue
        rank = 0 if parts[1:-1] == ["chart"] else 1
        if parts[-1] not in found or rank < found[parts[-1]][0]:
            found[parts[-1]] = (rank, row)
    return {state: {"status": row.get("status"), "changed_fraction": _changed(row), **_beyond(row, rows.get(f"state:{state}"))}
            for state, (_, row) in sorted(found.items(), key=lambda kv: list(STATES).index(kv[0]))}


def _beyond(row: Row, alone: Row | None) -> Row:
    """Against the state built alone (state_baselines): what the state did to the chart, and
    whether the feature's run ended on a different image (its own effect there)."""
    if not alone or not _pixels(alone):
        return {}
    after, baseline = (_pixels(row) or {}).get("after_sha256"), _pixels(alone).get("after_sha256")
    return {"state_alone": _changed(alone),
            "changed_beyond_state": None if not (after and baseline) else after != baseline}


def build_sheets(
    inventory: Iterable[Row],
    results: Iterable[Row],
    feature_code: Iterable[Row],
    control_code: Iterable[Row],
    *,
    plugin_parameters: Iterable[Row],
    terminology: Iterable[Row],
) -> list[Row]:
    """A sheet for every inventory item the sweeps ran or found code for (results: a sweep's
    results.jsonl rows, the latest per item counting)."""
    rows = _latest(results)
    code: dict[str, dict[str, int]] = defaultdict(dict)
    for row in feature_code:
        code[row["item_id"]][row["binary"]] = len(row["functions"])
    controls: dict[str, list[Row]] = defaultdict(list)
    for row in control_code:
        controls[row["dialog"]].append({"label": row["label"], "status": row["status"], "binary": row.get("binary"),
                                        "via": row.get("via"), "functions": len(row.get("functions") or [])})
    codes_of: dict[str, set[str]] = defaultdict(set)
    for term in terminology:
        if term.get("code"):
            codes_of[term["name"]].add(term["code"])
    declared: dict[str, list[tuple[str, Row]]] = defaultdict(list)
    for plugin in plugin_parameters:
        if plugin.get("item_id"):
            declared[plugin["item_id"]] += [(plugin["binary"], s) for s in plugin["settings"]]
    ran = {run_id.split("@")[0] for run_id in rows}
    sheets = []
    for item in inventory:
        item_id = item["id"]
        if item_id not in ran and item_id not in code:
            continue
        recorded = ((rows.get(f"{item_id}@settings") or {}).get("observations") or {}).get("event_settings") or {}
        event = recorded.get("event")
        # Its work on the chart: a filter's effect applied, a tool used, else the command run.
        chart = rows.get(f"{item_id}@chart") or rows.get(f"{item_id}@use") or rows.get(item_id)
        sheets.append({
            "item_id": item_id,
            "kind": item["kind"],
            "name": item["name"],
            "path": item.get("path"),
            "event": event,
            "on_chart": {"status": (chart or {}).get("status"), **(_pixels(chart) or {})},
            "settings": [_setting(s, event, rows, _anchors(s["key"], codes_of[s["key"]], declared[item_id]))
                         for s in recorded.get("settings") or []] if event else [],
            "states": _states(item_id, rows),
            "code": code.get(item_id, {}),
            "controls": controls.get((item.get("path") or "").removesuffix("..."), []),
        })
    return sheets


def main() -> None:
    """python -m scripts.adobe_observed_truth.fact_sheets --dataset <dir> --results <sweep>/results.jsonl

    Write feature-sheets.jsonl. The sweep's results are read first and the dataset's after, so
    the dataset's readings of each command's defaults win (a sweep's later readings can hold
    last-used values)."""
    import argparse
    from pathlib import Path

    parser = argparse.ArgumentParser(description=main.__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--results", type=Path, action="append", default=[])
    args = parser.parse_args()

    def rows(path: Path) -> list[Row]:
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

    d = args.dataset
    results = [row for path in (*args.results, d / "results.jsonl") for row in rows(path)]
    sheets = build_sheets(rows(d / "inventory.jsonl"), results, rows(d / "feature-code.jsonl"),
                          rows(d / "control-code.jsonl"), plugin_parameters=rows(d / "plugin-parameters.jsonl"),
                          terminology=rows(d / "terminology.jsonl"))
    with (d / "feature-sheets.jsonl").open("w", encoding="utf-8", newline="\n") as out:
        out.writelines(json.dumps(s, sort_keys=True) + "\n" for s in sheets)
    with_settings = [s for s in sheets if s["settings"]]
    ranged = sum(1 for s in with_settings for t in s["settings"] if (t["range"] or {}).get("max") is not None)
    print(json.dumps({"sheets": len(sheets), "with_settings": len(with_settings),
                      "with_states": sum(1 for s in sheets if s["states"]),
                      "with_code": sum(1 for s in sheets if s["code"]), "settings_with_a_max": ranged}))


if __name__ == "__main__":
    main()
