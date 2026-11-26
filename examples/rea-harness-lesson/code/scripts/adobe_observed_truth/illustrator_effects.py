"""Illustrator's vector live effects swept setting by setting (runner_illustrator apply_effect).

Each effect is applied by script (`PageItem.applyEffect` with a LiveEffect dictionary) to one item of
the scratch fixture, starting from the defaults its dialog showed in the dialog survey, with one
setting changed per spec; the result is expanded (Object > Expand Appearance) and measured as
geometry. The setting keys are the ones each effect's own plugin carries beside its name, kept
where a 2026-11-25 probe saw them change the result (alone, or with the others set). Types: R real,
I integer, B true/false. Warp (Adobe Deform) is left out: no key combination tried changed it.
Effects that draw pixels (shadows, glows, feather, blur, the Photoshop filters) need a pixel
measure and are not here.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .families import NEVER_PRESS, ScenarioSpec

FAR = 1_000_000  # as sweeps.FAR: a setting that takes it unchanged accepts any value


@dataclass(frozen=True)
class Effect:
    name: str  # the live effect's own name
    menu: str  # the menu command that opens its dialog
    item: str  # the fixture item it is applied to
    base: dict[str, tuple[str, float]]  # key: (type, the dialog's default)
    vary: dict[str, list[float]] = field(default_factory=dict)


EFFECTS = [
    Effect("Adobe Offset Path", "Live Offset Path", "rect", {"ofst": ("R", 10), "jntp": ("I", 2), "mlim": ("R", 4)},
           {"ofst": [-20, -5, 0, 5, 20], "jntp": [0, 1, 3], "mlim": [1, 10]}),
    Effect("Adobe Outline Stroke", "Live Outline Stroke", "arch", {}),
    Effect("Adobe Punk and Bloat", "Live Pucker & Bloat", "star", {"d_factor": ("R", 0)},
           {"d_factor": [-1, -0.5, -0.1, 0.1, 0.5, 1, 2]}),
    Effect("Adobe Roughen", "Live Roughen", "rect", {"size": ("R", 5), "dtal": ("R", 10), "asiz": ("I", 0), "smth": ("I", 0)},
           {"size": [0, 1, 20, 100], "dtal": [0, 1, 50, 100], "asiz": [1], "smth": [1]}),
    Effect("Adobe Round Corners", "Live Round Corners", "star", {"radius": ("R", 10)}, {"radius": [0, 2, 30, 100]}),
    Effect("Adobe Zigzag", "Live Zig Zag", "rect",
           {"amount": ("R", 10), "relAmount": ("R", 10), "ridges": ("I", 4), "roundness": ("I", 0), "absoluteness": ("I", 1)},
           {"amount": [0, 2, 40], "relAmount": [5, 50], "ridges": [0, 1, 10, 100], "roundness": [1], "absoluteness": [0]}),
    Effect("Adobe Twirl", "Live Twist", "star", {"angle": ("R", 0)}, {"angle": [-180, -45, 10, 45, 180, 720]}),
    Effect("Adobe Transform", "Live Transform", "rect",
           {"scaleH_Factor": ("R", 1), "scaleV_Factor": ("R", 1), "moveH_Pts": ("R", 0), "moveV_Pts": ("R", 0),
            "rotate_Radians": ("R", 0), "numCopies": ("I", 0), "pinPoint": ("I", 4), "reflectX": ("B", 0),
            "reflectY": ("B", 0), "randomize": ("B", 0)},
           {"scaleH_Factor": [0, 0.5, 2], "scaleV_Factor": [0.5, 2], "moveH_Pts": [-30, 30], "moveV_Pts": [30],
            "rotate_Radians": [0.5, 3.14159], "numCopies": [1, 3], "pinPoint": [0, 8], "reflectX": [1], "reflectY": [1],
            "randomize": [1]}),
    Effect("Adobe Scribble and Tweak", "Live Tweak", "rect",
           {"horz": ("R", 10), "vert": ("R", 10), "absoluteness": ("I", 0), "anch": ("B", 1), "in": ("B", 0), "out": ("B", 0),
            "ahor": ("R", 0), "aver": ("R", 0)},
           {"horz": [0, 50], "vert": [0, 50], "absoluteness": [1], "anch": [0], "in": [1], "out": [1]}),
    Effect("Adobe Shape Effects", "Live Rectangle", "star",
           {"Shape": ("I", 0), "Absolute": ("I", 1), "AbsWidth": ("R", 18), "AbsHeight": ("R", 18), "RelWidth": ("R", 0),
            "RelHeight": ("R", 0), "CornerRadius": ("R", 9)},
           {"Shape": [1, 2], "Absolute": [0], "AbsWidth": [0, 60], "AbsHeight": [0, 60], "CornerRadius": [0, 30]}),
    Effect("Adobe Add Arrowheads", "Live AddArrowHeads2", "arch", {"head_arrow": ("I", 1), "tail_arrow": ("I", 0), "scale": ("R", 100)},
           {"head_arrow": [0, 5, 20], "tail_arrow": [1, 5], "scale": [50, 300]}),
    Effect("Adobe Pathfinder", "Live Pathfinder Add", "overlap", {"Command": ("I", 0)},
           {"Command": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]}),
]


def _number(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else str(value)


def effect_data(effect: Effect, key: str | None = None, value: float | None = None) -> str:
    """The effect's dictionary as `applyEffect` reads it: its defaults, `key` set to `value`."""
    parts = []
    for name, (kind, default) in effect.base.items():
        parts.append(f"{kind} {name} {_number(value if name == key else default)} ")
    return "".join(parts)


def effect_specs(effects: list[Effect]) -> list[ScenarioSpec]:
    """Per effect: its defaults twice (a random effect shows as not repeating), then one spec per
    changed setting; real settings also get the far values."""
    specs = []
    for effect in effects:
        runs = [("defaults", effect_data(effect)), ("defaults-again", effect_data(effect))]
        for key, values in effect.vary.items():
            far = [FAR, -FAR] if effect.base[key][0] == "R" else []
            runs += [(f"{key}={_number(v)}", effect_data(effect, key, v)) for v in [*values, *far]]
        for label, data in runs:
            steps = (("new_fixture",), ("apply_effect", effect.name, effect.item, data), ("record", "effect"),
                     ("close_throwaway_document",))
            specs.append(ScenarioSpec(f"effect:{effect.name}@{label}", "live_effect", "run", False, steps, None, NEVER_PRESS))
    return specs


_EMPTY = 1e8  # bounds start at +-1e9 in the measuring script; an empty result never moves them


def measured(raw: list) -> dict:
    """The measuring script's answer [error, items, points, area, left, top, right, bottom] as a
    record; a result with no points has no bounds."""
    error, items, points, area, *bounds = raw
    keep = points > 0 and all(abs(b) < _EMPTY for b in bounds)
    return {"error": error, "items": items, "points": points, "area": area, "bounds": bounds if keep else None}


def _fingerprint(effect: dict | None) -> tuple | None:
    if not effect:
        return None
    return (effect.get("error"), effect.get("items"), effect.get("points"), effect.get("area"),
            tuple(effect["bounds"]) if effect.get("bounds") else None)


def effect_sheets(effects: list[Effect], rows: list[dict]) -> list[dict]:
    """One sheet per effect swept (`rows`: the sweep's results, the last run of each spec kept):
    whether its defaults measured the same twice, and per setting each value's measure and whether
    it differs from the defaults (None when the defaults do not repeat)."""
    latest = {row["item_id"]: row for row in rows if row.get("status") == "ok"}

    def seen(effect: Effect, label: str) -> dict | None:
        row = latest.get(f"effect:{effect.name}@{label}")
        return (row or {}).get("observations", {}).get("effect")

    sheets = []
    for effect in effects:
        base, again = seen(effect, "defaults"), seen(effect, "defaults-again")
        if base is None:
            continue
        repeatable = again is not None and _fingerprint(base) == _fingerprint(again)
        settings = {}
        for key, (kind, default) in effect.base.items():
            far = [FAR, -FAR] if kind == "R" else []
            values = []
            for value in [*effect.vary.get(key, []), *far]:
                result = seen(effect, f"{key}={_number(value)}")
                if result is None:
                    continue
                changed = (_fingerprint(result) != _fingerprint(base)) if repeatable else None
                values.append({"value": value, "changed": changed,
                               **{k: result.get(k) for k in ("error", "items", "points", "area", "bounds")}})
            settings[key] = {"type": kind, "default": default, "acts": any(v["changed"] for v in values),
                             "values": values}
        sheets.append({"effect": effect.name, "menu": effect.menu, "item": effect.item, "repeatable": repeatable,
                       "defaults": {k: base.get(k) for k in ("error", "items", "points", "area", "bounds")},
                       "settings": settings})
    return sheets


def main() -> None:
    """python -m scripts.adobe_observed_truth.illustrator_effects --dataset <dir>: write effect-families.jsonl."""
    import argparse
    import json
    from dataclasses import asdict
    from pathlib import Path

    parser = argparse.ArgumentParser(description=main.__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--sheets", type=Path, help="a sweep's results.jsonl: write effect-sheets.jsonl instead")
    args = parser.parse_args()
    if args.sheets:
        rows = [json.loads(line) for line in args.sheets.read_text(encoding="utf-8").splitlines() if line.strip()]
        sheets = effect_sheets(EFFECTS, rows)
        with (args.dataset / "effect-sheets.jsonl").open("w", encoding="utf-8", newline="\n") as out:
            out.writelines(json.dumps(s, sort_keys=True) + "\n" for s in sheets)
        print(f"{len(sheets)} effect sheets")
        return
    specs = effect_specs(EFFECTS)
    with (args.dataset / "effect-families.jsonl").open("w", encoding="utf-8", newline="\n") as out:
        out.writelines(json.dumps(asdict(s), sort_keys=True) + "\n" for s in specs)
    print(f"{len(specs)} effect specs over {len(EFFECTS)} effects")


if __name__ == "__main__":
    main()
