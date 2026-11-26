"""Deeper probes: vary one setting of a filter or adjustment at a time, from its recorded
defaults, so each setting's code (the 4-char keys the decompiled plug-ins compare against) is
reached with known values and its effect on the probe chart is measured.

Settings come from the descriptor Photoshop returned when the command ran at its defaults
(action_settings.py). Each sweep replays the command by script with no dialog: every recorded
setting at its default except the one being varied. This sets a setting exactly as its dialog
slider would, by the key the plug-in reads, which is what the decompiled code compares.
"""

from __future__ import annotations

import json
from typing import Any

# Never varied: GEfk names which Filter Gallery filter runs (another command, not a setting),
# and presetKind only says whether a saved preset was used.
_NOT_SETTINGS = frozenset({"GEfk", "presetKind"})
DEFAULT_REPEATS = 3  # identical results three times over: the command is deterministic here


def sweep_values(setting: dict[str, Any]) -> list[Any]:
    """The values a setting is tried at, its default excluded: a quarter, half, double and
    four times a number (1, 10 and 100 when it is 0), every other choice, the other on/off."""
    kind, default = setting["type"], setting.get("default")
    if kind == "boolean":
        return [not default]
    if kind == "choice":
        default = setting.get("default_code") or default
        return [option for option in setting.get("options", []) if option != default]
    if kind not in ("integer", "double", "unit") or not isinstance(default, (int, float)):
        return []
    if isinstance(default, bool):
        return []
    if default == 0:
        candidates: list[float] = [1, 10, 100]
    else:
        candidates = [default * factor for factor in (0.25, 0.5, 2, 4)]
    whole = kind == "integer"
    values: list[Any] = []
    for candidate in candidates:
        value = round(candidate) if whole else float(candidate)
        if value != default and value not in values:
            values.append(value)
    return values


def with_options(
    settings: list[dict[str, Any]],
    codes_of: dict[str, set[str]],
    pipl_choices: dict[str, list[str]],
) -> list[dict[str, Any]]:
    """Give each choice its options: the 4-char codes its plug-in declares for that setting
    (the codes the decompiled plug-in compares against), and the code of its default. A
    choice no plug-in declares (a built-in) keeps no options and is not swept."""
    out = []
    for setting in settings:
        if setting["type"] == "choice" and "options" not in setting:
            declared = [
                pipl_choices[c] for c in sorted(codes_of.get(setting["key"], ())) if c in pipl_choices
            ]
            if declared:
                options = declared[0]
                default_codes = codes_of.get(str(setting.get("default")), set()) & set(options)
                setting = {
                    **setting,
                    "options": options,
                    "default_code": next(iter(sorted(default_codes)), None),
                }
        out.append(setting)
    return out


def sweep_specs(event: str, settings: list[dict[str, Any]]) -> list[Any]:
    """The sweep of one command: its defaults replayed three times, then each setting alone at
    each of its sweep values. A command with nested settings (colour objects, lists) is left
    out until they can be replayed whole: setting only part of it would leave the rest at
    whatever was last used."""
    from .families import NEVER_PRESS, ScenarioSpec

    if not settings or any("." in s["key"] or "[" in s["key"] for s in settings):
        return []

    def spec(name: str, overrides: dict[str, Any]) -> Any:
        steps = (
            ("open_test_image", "chart"),
            ("sweep_event", event, settings, overrides),
            ("record", "dialogs", "sweep", "pixels"),
            ("cancel_dialogs",),
            ("close_throwaway_document",),
        )
        return ScenarioSpec(
            f"sweep:{event}:{name}", "setting_sweep", "run", False, steps, None, NEVER_PRESS
        )

    specs = [spec(f"default#{n}", {}) for n in range(1, DEFAULT_REPEATS + 1)]
    for setting in settings:
        if setting["key"] in _NOT_SETTINGS:
            continue
        for value in sweep_values(setting) + range_probes(setting):
            specs.append(spec(f"{setting['key']}={json.dumps(value)}", {setting["key"]: value}))
    return specs


FAR = 1_000_000


def range_probes(setting: dict[str, Any]) -> list[Any]:
    """A number tried far below and far above any range it could have: the value Photoshop reads
    back (the sweep's `used`) is the bound it clamps to, so a fact sheet gets the real minimum and
    maximum (the sweep values only hit a clamp by chance: Fill opacity 200 read back 100)."""
    default = setting.get("default")
    if setting["type"] not in ("integer", "double", "unit") or isinstance(default, bool) \
            or not isinstance(default, (int, float)):
        return []
    return [-FAR, FAR] if setting["type"] == "integer" else [float(-FAR), float(FAR)]


def specs_from_results(
    lines: list[str],
    codes_of: dict[str, set[str]],
    pipl_choices: dict[str, list[str]],
) -> list[Any]:
    """Every command's sweep, from the latest defaults recorded for it in results.jsonl
    (a later reading replaces an earlier one); a line cut short is skipped."""
    latest: dict[str, list[dict[str, Any]]] = {}
    for line in lines:
        try:
            row = json.loads(line)
        except ValueError:
            continue
        recorded = (row.get("observations") or {}).get("event_settings")
        if row.get("status") == "ok" and recorded and recorded.get("settings"):
            latest[recorded["event"]] = recorded["settings"]
    return [
        spec
        for event, settings in latest.items()
        for spec in sweep_specs(event, with_options(settings, codes_of, pipl_choices))
    ]


def main() -> None:
    """Write sweep-families.jsonl: the setting sweeps the runner runs with --specs."""
    import argparse
    from collections import Counter, defaultdict
    from dataclasses import asdict
    from pathlib import Path

    parser = argparse.ArgumentParser(description=main.__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--results", type=Path, action="append", default=[],
                        help="a sweep's results.jsonl too, for commands the dataset's results lack "
                             "(the dataset's readings win: a sweep's later ones can hold last-used values)")
    args = parser.parse_args()

    def rows(name: str) -> list[dict[str, Any]]:
        with (args.dataset / name).open(encoding="utf-8") as handle:
            return [json.loads(line) for line in handle if line.strip()]

    codes_of: dict[str, set[str]] = defaultdict(set)
    for term in rows("terminology.jsonl"):
        if term["code"]:
            codes_of[term["name"]].add(term["code"])
    pipl_choices: dict[str, list[str]] = {}
    for plugin in rows("plugin-parameters.jsonl"):
        for setting in plugin["settings"]:
            if setting["choices"]:
                pipl_choices.setdefault(setting["code"], [c["code"] for c in setting["choices"]])
    lines = [line for path in (*args.results, args.dataset / "results.jsonl")
             for line in path.read_text(encoding="utf-8").splitlines()]
    specs = specs_from_results(lines, codes_of, pipl_choices)
    with (args.dataset / "sweep-families.jsonl").open("w", encoding="utf-8", newline="\n") as out:
        for spec in specs:
            out.write(json.dumps(asdict(spec), sort_keys=True) + "\n")
    events = Counter(spec.item_id.split(":")[1] for spec in specs)
    print(json.dumps({"specs": len(specs), "commands": len(events)}))


def descriptor_puts(
    settings: list[dict[str, Any]], overrides: dict[str, Any]
) -> list[tuple[Any, ...]]:
    """How the replay descriptor is built: one ActionDescriptor put per recorded setting, by
    its recorded type, at its default unless overridden. Choice values are a stringID name
    (recorded defaults) or a plug-in's 4-char code (swept options)."""
    puts: list[tuple[Any, ...]] = []
    for setting in settings:
        key, kind = setting["key"], setting["type"]
        value = overrides.get(key, setting.get("default"))
        if kind == "unit":
            puts.append(("putUnitDouble", key, setting["unit"], float(value)))
        elif kind == "double":
            puts.append(("putDouble", key, float(value)))
        elif kind == "integer":
            puts.append(("putInteger", key, int(value)))
        elif kind == "boolean":
            puts.append(("putBoolean", key, bool(value)))
        elif kind == "string":
            puts.append(("putString", key, str(value)))
        elif kind == "choice":
            which = {"code": value} if key in overrides else {"name": value}
            puts.append(("putEnumerated", key, setting["choices"], which))
    return puts


def replay_script(event: str, settings: list[dict[str, Any]], overrides: dict[str, Any]) -> str:
    """ExtendScript that runs `event` with no dialog and the replay descriptor, returning
    {"descriptor": the settings Photoshop says it used, "error": its message if it declined}.
    Photoshop's own answer is kept: a value it clamps or refuses shows the setting's range."""
    from .action_settings import _DESCRIPTOR_JS

    def tid(name: str) -> str:
        return f"stringIDToTypeID({json.dumps(name)})"

    lines = ["var d=new ActionDescriptor();"]
    for put in descriptor_puts(settings, overrides):
        method, key = put[0], tid(put[1])
        if method == "putUnitDouble":
            lines.append(f"d.putUnitDouble({key},{tid(put[2])},{json.dumps(put[3])});")
        elif method == "putEnumerated":
            which = put[3]
            value = (
                f"charIDToTypeID({json.dumps(which['code'])})"
                if "code" in which
                else tid(which["name"])
            )
            lines.append(f"d.putEnumerated({key},{tid(put[2])},{value});")
        else:
            lines.append(f"d.{method}({key},{json.dumps(put[2])});")
    name = json.dumps(event)
    return (
        _DESCRIPTOR_JS
        + "".join(lines)
        + (
            "var r=null,err='';"
            f"try{{r=executeAction(stringIDToTypeID({name}),d,DialogModes.NO);}}"
            "catch(e){err=String(e);}"
            f"'{{\"descriptor\":'+(r?o2j(r,{name}):'null')+',\"error\":'+q(err)+'}}';"
        )
    )


if __name__ == "__main__":
    main()
