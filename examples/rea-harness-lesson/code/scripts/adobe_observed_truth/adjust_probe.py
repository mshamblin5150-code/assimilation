"""The adjustment probe: Photoshop's tonal and colour adjustments as transfer curves.

Each spec opens the retouch probe's ramp image (every grey level, and a red-to-white saturation
ramp), runs one adjustment by its own event with settings in the descriptor (no dialog), and records
the output for every input level (retouch_probe.measure).
"""

from __future__ import annotations

import json
from typing import Any

from .families import ScenarioSpec

_COMPOSITE = ("var r=new ActionReference();r.putEnumerated(charIDToTypeID('Chnl'),charIDToTypeID('Chnl'),charIDToTypeID('Cmps'));"
              "a.putReference(charIDToTypeID('Chnl'),r);")


def adjust_js(kind: str, p: dict[str, Any]) -> str:
    """ExtendScript running one adjustment on the active document with settings `p`."""
    c = "charIDToTypeID"
    if kind == "levels":
        return ("var d=new ActionDescriptor(),l=new ActionList(),a=new ActionDescriptor();" + _COMPOSITE +
                f"var i=new ActionList();i.putInteger({p['black']});i.putInteger({p['white']});a.putList({c}('Inpt'),i);"
                f"a.putDouble({c}('Gmm '),{float(p['gamma'])});"
                f"var o=new ActionList();o.putInteger({p.get('out_black', 0)});o.putInteger({p.get('out_white', 255)});a.putList({c}('Otpt'),o);"
                f"l.putObject({c}('LvlA'),a);d.putList({c}('Adjs'),l);executeAction({c}('Lvls'),d,DialogModes.NO);'null';")
    if kind == "curves":
        points = "".join(f"var q=new ActionDescriptor();q.putDouble({c}('Hrzn'),{float(x)});q.putDouble({c}('Vrtc'),{float(y)});"
                         f"pts.putObject({c}('Pnt '),q);" for x, y in p["points"])
        return ("var d=new ActionDescriptor(),l=new ActionList(),a=new ActionDescriptor();" + _COMPOSITE +
                f"var pts=new ActionList();{points}a.putList({c}('Crv '),pts);l.putObject({c}('CrvA'),a);"
                f"d.putList({c}('Adjs'),l);executeAction({c}('Crvs'),d,DialogModes.NO);'null';")
    if kind == "brightness_contrast":
        return (f"var d=new ActionDescriptor();d.putInteger({c}('Brgh'),{p['brightness']});d.putInteger({c}('Cntr'),{p['contrast']});"
                f"d.putBoolean(stringIDToTypeID('useLegacy'),{json.dumps(p['legacy'])});executeAction({c}('BrgC'),d,DialogModes.NO);'null';")
    if kind == "hue_saturation":
        return (f"var d=new ActionDescriptor(),l=new ActionList(),a=new ActionDescriptor();d.putBoolean({c}('Clrz'),false);"
                f"a.putInteger({c}('H   '),{p['hue']});a.putInteger({c}('Strt'),{p['saturation']});a.putInteger({c}('Lght'),{p['lightness']});"
                f"l.putObject({c}('Hst2'),a);d.putList({c}('Adjs'),l);executeAction({c}('HStr'),d,DialogModes.NO);'null';")
    if kind == "exposure":
        return (f"var d=new ActionDescriptor();d.putDouble({c}('Exps'),{float(p['exposure'])});d.putDouble({c}('Ofst'),{float(p['offset'])});"
                f"d.putDouble(stringIDToTypeID('gammaCorrection'),{float(p['gamma'])});executeAction({c}('Exps'),d,DialogModes.NO);'null';")
    if kind == "vibrance":
        return (f"var d=new ActionDescriptor();d.putInteger(stringIDToTypeID('vibrance'),{p['vibrance']});"
                f"d.putInteger({c}('Strt'),{p['saturation']});executeAction(stringIDToTypeID('vibrance'),d,DialogModes.NO);'null';")
    if kind == "threshold":
        return f"var d=new ActionDescriptor();d.putInteger({c}('Lvl '),{p['level']});executeAction({c}('Thrs'),d,DialogModes.NO);'null';"
    if kind == "posterize":
        return f"var d=new ActionDescriptor();d.putInteger({c}('Lvls'),{p['levels']});executeAction({c}('Pstr'),d,DialogModes.NO);'null';"
    raise ValueError(kind)


CASES: list[tuple[str, str, dict[str, Any]]] = [
    *(("levels", f"black={b}:white={w}:gamma={g}:out={lo}-{hi}", {"black": b, "white": w, "gamma": g, "out_black": lo, "out_white": hi})
      for b, w, g, lo, hi in ((0, 255, 1.0, 0, 255), (50, 255, 1.0, 0, 255), (0, 200, 1.0, 0, 255), (0, 255, 0.5, 0, 255),
                              (0, 255, 2.0, 0, 255), (0, 255, 1.0, 50, 200), (30, 220, 1.4, 0, 255),
                              *((0, 255, g, 0, 255) for g in (1.1, 1.2, 1.5, 3.0, 5.0, 9.99)))),
    *(("curves", name, {"points": pts}) for name, pts in (
        ("lift", [(0, 0), (128, 160), (255, 255)]), ("s_curve", [(0, 0), (64, 40), (192, 215), (255, 255)]),
        ("strong", [(0, 0), (128, 200), (255, 255)]), ("five", [(0, 10), (60, 30), (128, 140), (190, 200), (255, 240)]))),
    *(("brightness_contrast", f"brightness={b}:contrast={k}" + (":legacy" if legacy else ""), {"brightness": b, "contrast": k, "legacy": legacy})
      for b, k, legacy in ((50, 0, False), (-50, 0, False), (0, 50, False), (0, -50, False), (50, 0, True), (0, 50, True), (0, -50, True))),
    *(("hue_saturation", f"hue={h}:saturation={s}:lightness={li}", {"hue": h, "saturation": s, "lightness": li})
      for h, s, li in ((0, 50, 0), (0, -50, 0), (0, -100, 0), (0, 0, 50), (0, 0, -50), (60, 0, 0))),
    *(("exposure", f"exposure={e}:offset={o}:gamma={g}", {"exposure": e, "offset": o, "gamma": g})
      for e, o, g in ((1.0, 0.0, 1.0), (-1.0, 0.0, 1.0), (0.0, 0.1, 1.0), (0.0, 0.0, 2.0))),
    *(("vibrance", f"vibrance={v}:saturation={s}", {"vibrance": v, "saturation": s}) for v, s in ((50, 0), (-50, 0), (0, 50))),
    *(("threshold", f"level={t}", {"level": t}) for t in (64, 128, 200)),
    *(("posterize", f"levels={n}", {"levels": n}) for n in (2, 4, 7)),
]


def adjust_specs() -> list[ScenarioSpec]:
    return [ScenarioSpec(f"adjust:{kind}:{name}", "adjust_probe", "run", False,
                         (("open_test_image", "ramp"), ("adjust", kind, params), ("record", "curve"), ("close_throwaway_document",)))
            for kind, name, params in CASES]


def published_rows(results: Any) -> list[dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for row in results:
        if row["item_id"].startswith("adjust:") and row.get("status") == "ok" and "curve" in (row.get("observations") or {}):
            latest[row["item_id"]] = {"item_id": row["item_id"], **row["observations"]["curve"]}
    return list(latest.values())


def main() -> None:
    """python -m scripts.adobe_observed_truth.adjust_probe --dataset <dir> [--results <sweep>/results.jsonl]"""
    import argparse
    from dataclasses import asdict
    from pathlib import Path

    parser = argparse.ArgumentParser(description=main.__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--results", type=Path)
    args = parser.parse_args()
    if args.results:
        rows = published_rows(json.loads(l) for l in args.results.read_text(encoding="utf-8").splitlines() if l.strip())
        with (args.dataset / "adjust-probe.jsonl").open("w", encoding="utf-8", newline="\n") as out:
            out.writelines(json.dumps(r, sort_keys=True) + "\n" for r in rows)
        print(f"{len(rows)} adjust probe rows written")
        return
    specs = adjust_specs()
    with (args.dataset / "adjust-families.jsonl").open("w", encoding="utf-8", newline="\n") as out:
        out.writelines(json.dumps(asdict(s), sort_keys=True) + "\n" for s in specs)
    print(f"{len(specs)} adjust probe specs")


if __name__ == "__main__":
    main()
