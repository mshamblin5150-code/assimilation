"""What each filter plug-in says about its own settings, and where the decompiled code reads them.

Photoshop 2026 plug-ins carry a JSON_PIPL resource: per filter its name, menu category,
scripting event code, entry function, and terminology (each setting's name, four-letter code
and type, and the choices of each choice setting). A dialog control is one of those settings;
the plug-in's code compares descriptor keys against the four-letter codes as 32-bit numbers,
so searching the decompiled functions for those numbers shows where each setting is read.
Only names, codes and function addresses are recorded: learnings, never Adobe's code.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .inventory import load_inventory


@dataclass(frozen=True)
class Choice:
    name: str
    code: str


@dataclass(frozen=True)
class Setting:
    name: str
    code: str
    type: str
    choices: tuple[Choice, ...]


@dataclass(frozen=True)
class Plugin:
    name: str
    category: str | None
    kind: str | None
    menu_path: str | None
    event: str | None
    entry_point: str | None
    settings: tuple[Setting, ...]


def code_number(code: str) -> str:
    """A four-letter code as the 32-bit number Ghidra prints: "Amnt" -> "0x416d6e74"."""
    return "0x" + code.encode("latin-1").hex()


_HEX = re.compile(r"\b0x[0-9a-f]+\b")


def functions_using(
    functions: Iterable[tuple[str, str]], numbers: set[str]
) -> dict[str, list[str]]:
    """For each number, the addresses of the functions (address, pseudocode) that use it as a
    whole constant; a longer constant that merely contains its digits does not count."""
    found: dict[str, list[str]] = {number: [] for number in numbers}
    for address, text in functions:
        for number in numbers & set(_HEX.findall(text)):
            found[number].append(address)
    return found


def _readable(zstring: str | None) -> str:
    """"$$$/Example/Actions/keyAmount=Amount" -> "Amount"."""
    return (zstring or "").rsplit("=", 1)[-1].strip()


def _menu_path(kind: str | None, category: str | None, name: str) -> str | None:
    if kind != "Filter" or not category or category.startswith("**Hidden**"):
        return None
    if category.startswith("***"):  # its own top-level entry: Filter > Liquify
        return f"Filter > {name}"
    return f"Filter > {category} > {name}"


def _settings(pipl: dict[str, Any]) -> tuple[Setting, ...]:
    suites = (pipl.get("Terminology") or {}).get("Suites", [])
    choices = {
        enum["EnumID"]: tuple(
            Choice(_readable(e.get("EnumName")), e["EnumKeyword"]) for e in enum["Enumerators"]
        )
        for suite in suites
        for enum in suite.get("Enumerations", [])
    }
    return tuple(
        Setting(
            _readable(p.get("ParamName")),
            p["ParamKeyword"],
            p.get("ParamType", ""),
            choices.get(p.get("ParamType", ""), ())
            if (p.get("ParamFlagBits") or {}).get("Enumerated")
            else (),
        )
        for suite in suites
        for event in suite.get("Events", [])
        for p in event.get("Parameters", [])
    )


def numbers_of(plugin: Plugin) -> set[str]:
    """Every code of a plug-in's settings and choices, as the numbers to search code for."""
    return {code_number(s.code) for s in plugin.settings} | {
        code_number(c.code) for s in plugin.settings for c in s.choices
    }


def own_functions(plugin: Plugin, uses: dict[str, list[str]]) -> list[str]:
    """Functions reading every one of the plug-in's setting codes: its own settings code, since
    one binary can host many filters sharing codes like Amnt. A single setting cannot tell."""
    codes = {code_number(s.code) for s in plugin.settings}
    if len(codes) < 2:
        return []
    shared = set.intersection(*(set(uses.get(code, [])) for code in codes))
    return sorted(shared)


def plugin_record(
    plugin: Plugin,
    *,
    binary: str,
    exports: dict[str, str],
    menu_items: dict[str, str],
    uses: dict[str, list[str]],
) -> dict[str, Any]:
    """The published learning for one filter: its menu item, event, entry function, and for
    each setting and choice the decompiled functions that use its code."""
    return {
        "item_id": menu_items.get(plugin.menu_path or ""),
        "menu_path": plugin.menu_path,
        "binary": binary,
        "event": plugin.event,
        "entry_point": plugin.entry_point,
        "entry_function": exports.get(plugin.entry_point or ""),
        "own_functions": own_functions(plugin, uses),
        "settings": [
            {
                "name": s.name,
                "code": s.code,
                "type": s.type,
                "functions": uses.get(code_number(s.code), []),
                "choices": [
                    {"name": c.name, "code": c.code, "functions": uses.get(code_number(c.code), [])}
                    for c in s.choices
                ],
            }
            for s in plugin.settings
        ],
    }


def _pipl_text(folder: Path) -> tuple[str, str] | None:
    """(binary name, JSON_PIPL text) for one corpus folder, if its binary carries one."""
    resources = folder / "inspect-pe-resources.json"
    if not resources.exists():
        return None
    result = json.loads(resources.read_text(encoding="utf-8"))["normalized_result"]
    binary = Path(result["artifact"]["path"])
    for resource in result.get("resources", []):
        if (resource.get("name") or {}).get("name") == "JSON_PIPL":
            location = resource["payload"]["location"]
            with binary.open("rb") as handle:
                handle.seek(location["offset"])
                return binary.name, handle.read(location["bytes"]).decode("utf-8-sig")
    return None


def _exports(folder: Path) -> dict[str, str]:
    path = folder / "inspect-native-exports.json"
    if not path.exists():
        return {}
    exports = json.loads(path.read_text(encoding="utf-8"))["normalized_result"].get("exports", [])
    return {e["name"]: e["address"] for e in exports if e.get("name") and e.get("address")}


def _functions(folder: Path) -> Iterator[tuple[str, str]]:
    for path in sorted((folder / "pseudocode" / "functions").glob("*.c")):
        yield path.stem, path.read_text(encoding="utf-8", errors="replace")


def build(corpus: Path, dataset: Path) -> dict[str, Any]:
    """Write plugin-parameters.jsonl for every plug-in in the corpus folder; return a summary."""
    menu_items = {
        item.path: item.id for item in load_inventory(dataset / "inventory.jsonl")
        if item.kind == "menu_command"
    }
    records: list[dict[str, Any]] = []
    no_code: list[str] = []
    for folder in sorted(p for p in corpus.iterdir() if p.is_dir()):
        found = _pipl_text(folder)
        if found is None:
            continue
        binary, text = found
        plugins = read_plugins(text)
        numbers = set().union(*(numbers_of(p) for p in plugins))
        decompiled = (folder / "pseudocode" / "functions").is_dir()
        if not decompiled:
            no_code.append(binary)
        uses = functions_using(_functions(folder), numbers) if decompiled and numbers else {}
        exports = _exports(folder)
        records += [
            plugin_record(p, binary=binary, exports=exports, menu_items=menu_items, uses=uses)
            for p in plugins
        ]
    with (dataset / "plugin-parameters.jsonl").open("w", encoding="utf-8", newline="\n") as out:
        for record in records:
            out.write(json.dumps(record, sort_keys=True) + "\n")
    settings = [s for r in records for s in r["settings"]]
    summary = {
        "plugins": len(records),
        "on_a_menu_item": sum(r["item_id"] is not None for r in records),
        "settings": len(settings),
        "settings_found_in_code": sum(bool(s["functions"]) for s in settings),
        "plugins_with_own_functions": sum(bool(r["own_functions"]) for r in records),
        "binaries_not_yet_decompiled": sorted(no_code),
    }
    (dataset / "plugin-parameters-summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    return summary


def query(dataset: Path, text: str) -> list[str]:
    """Readable lines for every plug-in whose menu path, entry point or event matches `text`."""
    lines: list[str] = []
    wanted = text.lower()
    with (dataset / "plugin-parameters.jsonl").open(encoding="utf-8") as handle:
        for record in map(json.loads, handle):
            names = " ".join(str(record.get(k) or "") for k in ("menu_path", "entry_point", "event"))
            if wanted not in names.lower():
                continue
            lines.append(
                f"{record['menu_path'] or '(no menu item)'}  [{record['item_id']}]  event "
                f"{record['event']}  entry {record['entry_point']} at {record['entry_function']}"
                f"  ({record['binary']})"
            )
            lines.append(
                "    its own settings code (reads every setting): "
                f"{', '.join(record.get('own_functions') or []) or 'not singled out'}"
            )
            for s in record["settings"]:
                lines.append(
                    f"    {s['name']} ({s['code']}, {s['type']}): read in "
                    f"{', '.join(s['functions']) or 'no function found yet'}"
                )
                lines += [f"        - {c['name']} ({c['code']})" for c in s["choices"]]
    return lines


def main() -> None:
    """python -m scripts.adobe_observed_truth.plugin_params build|query ..."""
    import argparse

    parser = argparse.ArgumentParser(description=main.__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    make = sub.add_parser("build", help="read every plug-in in the corpus and link it to code")
    make.add_argument("--corpus", type=Path, required=True, help="e.g. adobe-rea-corpus/photoshop")
    make.add_argument("--dataset", type=Path, required=True)
    ask = sub.add_parser("query", help="show a filter's settings and the code reading them")
    ask.add_argument("--dataset", type=Path, required=True)
    ask.add_argument("text")
    args = parser.parse_args()
    if args.command == "build":
        print(json.dumps(build(args.corpus, args.dataset), indent=2))
    else:
        print("\n".join(query(args.dataset, args.text)) or f"nothing matches {args.text!r}")


def read_plugins(pipl_json: str) -> list[Plugin]:
    """Every plug-in a JSON_PIPL resource describes."""
    plugins = []
    for pipl in json.loads(pipl_json)["PiPLs"]:
        name = str(pipl.get("Name", "")).removesuffix("...").strip()
        plugins.append(
            Plugin(
                name=name,
                category=pipl.get("Category"),
                kind=pipl.get("Kind"),
                menu_path=_menu_path(pipl.get("Kind"), pipl.get("Category"), name),
                event=(pipl.get("HasTerminology") or {}).get("EventID"),
                entry_point=pipl.get("CodeEntryPointWin64"),
                settings=_settings(pipl),
            )
        )
    return plugins


if __name__ == "__main__":
    main()
