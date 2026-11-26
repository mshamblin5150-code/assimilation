"""Where each driven dialog control lives in the decompiled code, for REA.

A control row names its dialog (a menu path) and its label. The dialog's binary is the filter
plug-in that adds that menu item (plugin-parameters.jsonl), or the app itself. In that binary a
control is found two ways: a filter setting of the same name, whose four-letter code the
plug-in's functions compare against (plugin_params); or one of the app's interface strings,
"$$$/Example/Key=Label", whose literal the functions that draw or use the control carry (a plug-in's
dialog may draw shared controls with the app's own strings, so the app is searched next). A control
no name places is found by the functions seen running only while it was driven, if its dialog
was driven live: the interface thread's stack sampled, then the decomp callees of what sampling
caught hooked through REA (runtime_links discoveries). A binary
not yet decompiled leaves the control waiting. Only binary names, codes, string keys and
function addresses are recorded: learnings, never Adobe's code or text.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from .rea_corpus import is_decompiled, is_skipped

APP_BINARY = "Photoshop.exe"  # a dialog no plug-in adds is the app's own

Strings = dict[str, dict[str, list[tuple[str, str]]]]  # binary -> label -> [(key, function)]


def _norm(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", text.lower()))


def link_control(
    dialog: str,
    label: str,
    plugins: dict[str, dict[str, Any]],
    strings: Strings,
    pending: set[str],
    data: dict[str, dict[str, list[str]]] | None = None,
) -> dict[str, Any]:
    """The code of the control `label` in `dialog`: status found, waiting (its binary is still
    being decompiled) or not_found; the binary; how it was found (via a setting's code, an
    interface string's key in a function, or failing both, that key in the binary's data: the
    anchor); and the functions using that anchor (none for a key only in data)."""
    plugin = plugins.get(dialog)
    binary = plugin["binary"] if plugin else APP_BINARY
    want = re.sub(r"(?<=\S) v$", "", _norm(label))  # "Pixels V": a dropdown read with its arrow
    if len(re.findall(r"[a-z]", want)) < 3:  # "6", "D", "OK": a value or a stray letter, not a name
        return {"status": "not_found", "binary": binary, "via": None, "anchor": None, "functions": []}
    named = _settings_named(want, (plugin or {}).get("settings", []))
    if named:
        return _found(binary, "setting", ",".join(s["code"] for s in named), [f for s in named for f in s["functions"]])
    for host in dict.fromkeys((binary, APP_BINARY)):  # a plug-in's dialog may use the app's strings
        if host in pending:
            return {"status": "waiting", "binary": host, "via": None, "anchor": None, "functions": []}
        uses = strings.get(host, {}).get(want, [])
        if uses:
            keys = sorted({key for key, _ in uses})
            return _found(host, "ui_string", keys[0], [f for key, f in uses if key == keys[0]])
    if keys := sorted((data or {}).get(binary, {}).get(want, [])):  # a layout or resource string
        return _found(binary, "ui_string_data", keys[0], [])
    return {"status": "not_found", "binary": binary, "via": None, "anchor": None, "functions": []}


def _settings_named(want: str, settings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The settings the label names: every word of the setting's name is in the label ("Blur
    Method" names Method), the most words winning. Settings with equally good names (Filter
    Gallery has two called Size) are all returned: which one the dialog shows is not known."""
    words = set(want.split())
    fits = [s for s in settings if s["functions"] and set(_norm(s["name"]).split()) <= words and _norm(s["name"])]
    best = max((len(_norm(s["name"]).split()) for s in fits), default=0)
    return [s for s in fits if len(_norm(s["name"]).split()) == best]


_UI_STRING = re.compile(r'"(\$\$\$/[^"=]+)=([^"]*)"')


def ui_labels(functions: Iterable[tuple[str, str]]) -> dict[str, list[tuple[str, str]]]:
    """Every interface string literal in the functions (address, pseudocode), by its label
    (normalised): the key and each function carrying it."""
    found: dict[str, list[tuple[str, str]]] = {}
    for address, text in functions:
        for key, label in sorted(set(_UI_STRING.findall(text))):
            if want := _norm(label.replace("&", "").replace("^", "")):
                found.setdefault(want, []).append((key, address))
    return found


_DATA_STRING = re.compile(rb"(\$\$\$/([A-Za-z0-9_./-]{1,160}))=([^\x00-\x1f'\"()]{1,160})")
SCRIPTING_DICTIONARY = ("Actions/",)  # names settings for scripts, not dialog controls


def data_labels(data: bytes, skip: tuple[str, ...] = SCRIPTING_DICTIONARY) -> dict[str, list[str]]:
    """Every interface string kept in a binary's data (layout descriptions, resources) rather
    than in a function, by its label (normalised): the keys carrying it."""
    found: dict[str, list[str]] = {}
    for raw_key, raw_path, raw_label in _DATA_STRING.findall(data):
        key = raw_key.decode("ascii")
        want = _norm(raw_label.decode("latin-1").replace("&", "").replace("^", ""))
        if want and not raw_path.decode("ascii").startswith(skip) and key not in found.get(want, []):
            found.setdefault(want, []).append(key)
    return found


def _labels_of(work_dir: Path) -> dict[str, list[tuple[str, str]]]:
    """One decompiled binary's interface strings by label, scanned once and kept beside its
    pseudocode (local: never published)."""
    cache = work_dir / "ui-labels.json"
    if cache.exists():
        return {k: [tuple(u) for u in v] for k, v in json.loads(cache.read_text(encoding="utf-8")).items()}
    functions = (
        (p.stem, p.read_text(encoding="utf-8", errors="replace"))
        for p in sorted((work_dir / "pseudocode" / "functions").glob("*.c"))
    )
    labels = ui_labels(functions)
    cache.write_text(json.dumps(labels, sort_keys=True), encoding="utf-8")
    return labels


def build(corpus: Path, dataset: Path, app: str = "photoshop") -> dict[str, Any]:
    """Write control-code.jsonl: one line per control driven (dialog and label, as in
    control-actions.jsonl) with where its code is. Binaries are named by their path in the
    app's install folder, so REA can open them."""
    plugins = {r["menu_path"]: r for r in _read_jsonl(dataset / "plugin-parameters.jsonl") if r.get("menu_path")}
    manifest = json.loads((corpus / "manifest.json").read_text(encoding="utf-8"))
    entries = {Path(e["relative"]).name: e for e in manifest if e["app"] == app}
    pending = {name for name, e in entries.items() if not is_decompiled(Path(e["work_dir"])) and not is_skipped(e)}
    controls = {
        (r["dialog"], r["label"]): None
        for r in _read_jsonl(dataset / "control-actions.jsonl")
        if isinstance(r.get("label"), str) and r["label"].strip() and r.get("dialog")
    }
    hosts = {plugins[d]["binary"] if d in plugins else APP_BINARY for d, _ in controls} | {APP_BINARY}
    strings = {b: _labels_of(Path(entries[b]["work_dir"])) for b in hosts if b in entries and b not in pending}
    data = {b: data_labels(Path(entries[b]["path"]).read_bytes()) for b in strings}
    pilot = dataset / "runtime-links-pilot.jsonl"  # what REA saw the functions do live, if hooked
    runtime = _read_jsonl(pilot) if pilot.exists() else []
    discovery: dict[tuple[str, str], list[dict[str, Any]]] = {}  # what ran only for each control, if driven live
    if (found_live := dataset / "runtime-discovery.jsonl").exists():
        for row in _read_jsonl(found_live):
            if isinstance(row["label"], str):  # a hashed label (not Photoshop's own) names nothing
                discovery.setdefault((row["dialog"], _bare(row["label"])), []).append(row)
    records = []
    for dialog, label in controls:
        link = with_discovery(link_control(dialog, label, plugins, strings, pending, data), discovery.get((dialog, _bare(label)), []))
        where = entries.get(link["binary"])
        record = {"dialog": dialog, "label": label, **link, "binary": where["relative"] if where else link["binary"]}
        records.append(with_runtime(record, runtime))
    with (dataset / "control-code.jsonl").open("w", encoding="utf-8", newline="\n") as out:
        out.writelines(json.dumps(r) + "\n" for r in records)
    summary = {
        "controls": len(records),
        "by_status": dict(Counter(r["status"] for r in records)),
        "by_via": dict(Counter(r["via"] for r in records if r["via"])),
        "binaries_waiting": sorted({r["binary"] for r in records if r["status"] == "waiting"}),
    }
    (dataset / "control-code-summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def with_discovery(link: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    """`link` (link_control's) or, when no name placed the control, the functions seen running
    only while it was driven (runtime-discovery.jsonl rows for this control: runtime_links
    discoveries) in one binary, the dialog's own first, then the app: every row there merged,
    `via` the ways they were seen (sampled, runtime: "sampled+runtime") and their anchors."""
    if link["status"] != "not_found" or not rows:
        return link
    rank = {link["binary"]: 0, APP_BINARY: 1}
    binary = min((r["binary"] for r in rows), key=lambda b: (rank.get(b, 2), b))
    here = [r for r in rows if r["binary"] == binary]
    ways = list(dict.fromkeys(r["via"] for r in here))
    anchors = list(dict.fromkeys(r["anchor"] for r in here))
    return _found(binary, "+".join(ways), ",".join(anchors), [f for r in here for f in r["functions"]])


def with_runtime(record: dict[str, Any], runtime: list[dict[str, Any]]) -> dict[str, Any]:
    """`record` with what REA saw its functions do in the running app (runtime_links: the
    functions hooked while the harness drove the dialog and the filter ran). Level "filter": they
    ran once per run of the filter (its settings read or written) and never while a control was
    driven; "control": one fired while a control was driven; "not seen": hooked, never fired. A
    control none of whose functions were hooked is returned unchanged."""
    hooked = {r["function"]: r for r in runtime if r["filter"] == record.get("dialog")}
    seen = [hooked[f] for f in record.get("functions", []) if f in hooked]
    if not seen:
        return record
    if any(r["fired_while_controls_driven"] for r in seen):
        level = "control"
    elif any(r["calls"] for r in seen):
        level = "filter"
    else:
        level = "not seen"
    keep = ("function", "phases", "calls", "fired_while_controls_driven", "frida_evidence")
    return {**record, "runtime": {"level": level, "functions": [{k: r[k] for k in keep} for r in seen]}}


def _bare(label: str) -> str:
    """A label as the drive logs it and as the dialog reads it alike: no trailing colon."""
    return label.strip().rstrip(":").strip()


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def main() -> None:
    """python -m scripts.adobe_observed_truth.control_code --corpus <dir> --dataset <dir> [--app photoshop]

    Run plugin_params build first: it names each filter's binary and setting codes."""
    import argparse

    parser = argparse.ArgumentParser(description=main.__doc__)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--app", default="photoshop")
    args = parser.parse_args()
    print(json.dumps(build(args.corpus, args.dataset, args.app), indent=2))


def _found(binary: str, via: str, anchor: str, functions: list[str]) -> dict[str, Any]:
    return {"status": "found", "binary": binary, "via": via, "anchor": anchor, "functions": sorted(set(functions))}


if __name__ == "__main__":
    main()
