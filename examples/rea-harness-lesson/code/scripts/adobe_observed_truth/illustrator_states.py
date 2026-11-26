"""Illustrator document states, each built on the runner's fixture (runner_illustrator.FIXTURE_JS,
whose items are named rect, ellipse, arch, star, text and group), leaving the relevant item
selected. 91 commands were declined on the plain fixture (error BKey); retry_in_states tries each
again in every state, which shows what each needs (a raster image, a text frame, a symbol...).
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import replace

from .families import ScenarioSpec

# Run with DOC set to the fixture's name; each script ends returning q('ok').
STATE_PRELUDE = r"""
var d=harnessDoc(DOC);app.activeDocument=d;var ab=d.artboards[0].artboardRect,L=ab[0],T=ab[1];
function rgb(r,g,b){var c=new RGBColor();c.red=r;c.green=g;c.blue=b;return c;}
function item(n){return d.pageItems.getByName(n);}
function only(it){d.selection=null;it.selected=true;}
"""

STATES: dict[str, str] = {
    "raster": 'var r=d.rasterize(item("rect"));r.name="raster";only(r);return q(\'ok\');',
    "clipping": (
        'var g=d.groupItems.add();g.name="clip";item("star").move(g,ElementPlacement.PLACEATEND);'
        "var c=d.pathItems.ellipse(T-50,L+270,60,60);c.move(g,ElementPlacement.PLACEATBEGINNING);"
        "g.clipped=true;only(g);return q('ok');"
    ),
    "compound": (
        'var cp=d.compoundPathItems.add();cp.name="compound";item("ellipse").move(cp,ElementPlacement.PLACEATEND);'
        "var h=d.pathItems.ellipse(T-55,L+205,40,40);h.move(cp,ElementPlacement.PLACEATEND);only(cp);return q('ok');"
    ),
    "symbol": "var sy=d.symbolItems.add(d.symbols[0]);sy.name=\"symbol\";only(sy);return q('ok');",
    "text_on_path": "var tp=d.textFrames.pathText(item(\"arch\"));tp.contents=\"Along 123\";only(tp);return q('ok');",
    "area_text": (
        "var box=d.pathItems.rectangle(T-120,L+180,120,60);var at=d.textFrames.areaText(box);"
        "at.contents=\"Inside 123\";only(at);return q('ok');"
    ),
    "gradient": (
        "var gr=d.gradients.add();gr.type=GradientType.LINEAR;var gc=new GradientColor();gc.gradient=gr;"
        "item(\"rect\").fillColor=gc;only(item(\"rect\"));return q('ok');"
    ),
    "pattern": (
        "var pc=null;for(var i=0;i<d.swatches.length;i++){if(d.swatches[i].color.typename==\"PatternColor\")"
        "{pc=d.swatches[i].color;break;}}if(!pc)throw new Error(\"no pattern swatch\");"
        "item(\"rect\").fillColor=pc;only(item(\"rect\"));return q('ok');"
    ),
    "opacity": "var r=item(\"rect\");r.opacity=50;r.blendingMode=BlendModes.MULTIPLY;only(r);return q('ok');",
    "blend": (
        "d.selection=null;item(\"rect\").selected=true;item(\"ellipse\").selected=true;"
        "app.executeMenuCommand(\"Path Blend Make\");return q('ok');"
    ),
    "live_paint": (
        "d.selection=null;item(\"rect\").selected=true;item(\"ellipse\").selected=true;"
        "app.executeMenuCommand(\"Make Planet X\");return q('ok');"
    ),
    "two_artboards": "d.artboards.add([ab[2]+20,ab[1],ab[2]+420,ab[3]]);return q('ok');",
    "two_layers": (
        "var ly=d.layers.add();ly.name=\"second\";item(\"star\").move(ly,ElementPlacement.PLACEATBEGINNING);"
        "return q('ok');"
    ),
    "locked_hidden": (
        "d.selection=null;item(\"rect\").locked=true;item(\"ellipse\").hidden=true;"
        "item(\"star\").selected=true;item(\"arch\").selected=true;item(\"text\").selected=true;return q('ok');"
    ),
    "cmyk": "app.executeMenuCommand(\"doc-color-cmyk\");return q('ok');",
    "nothing_selected": "d.selection=null;return q('ok');",
    "one_path": "only(item(\"rect\"));return q('ok');",
    "text_only": "only(item(\"text\"));return q('ok');",
}


# States Illustrator did not survive commands in: a symbol instance (AdobeNavigator2, Flash Text,
# AdobeCheatSheetMenu) and text on a path (arrangeicon, Live DropShadow2, Live AddArrowHeads2),
# each crashing it under three different commands (2026-11-25): not retried there.
CRASHES_ILLUSTRATOR = frozenset({"symbol", "text_on_path"})
# Commands that do not act on the art (windows, panels, preferences, presets, Flash text kinds,
# the last filter, which depends on history): no state can change their answer, and retrying
# arrangeicon and bringAllToFront crashed Illustrator (2026-11-25).
NOT_ABOUT_ART = frozenset({
    "menu:Adobe Illustrator About Plug-ins2", "menu:AdobeCheatSheetMenu", "menu:AdobeNavigator2",
    "menu:Dynamic Text", "menu:FileClipboardPref", "menu:Flash Text", "menu:Input Text", "menu:SWFPresets",
    "menu:TracingPresets", "menu:arrangeicon", "menu:bringAllToFront", "menu:showAllWindows", "menu:Last Filter",
})


# Photoshop's filters, run through Illustrator's adapter, need a raster image; retried in every
# state they crashed Illustrator every 10 to 25 runs (2026-11-25), so they are tried on one.
_PHOTOSHOP_FILTER = "PSAdapter_plugin_"


def _states_for(item_id: str) -> list[str]:
    if _PHOTOSHOP_FILTER in item_id:
        return ["raster"]
    return [state for state in STATES if state not in CRASHES_ILLUSTRATOR]


def _in_states(spec: ScenarioSpec) -> list[ScenarioSpec]:
    return [replace(spec, item_id=f"{spec.item_id}@{state}", family="state_retry",
                    steps=(spec.steps[0], ("build_state", state), *spec.steps[1:]))
            for state in _states_for(spec.item_id)]


def retry_in_states(results: Iterable[str], specs: list[ScenarioSpec]) -> list[ScenarioSpec]:
    """Each spec whose latest result (results.jsonl lines) is Illustrator declining it, once in
    every state: the state built right after the fixture, then the spec's own steps."""
    latest: dict[str, str] = {}
    for line in results:
        if line.strip():
            row = json.loads(line)
            latest[row["item_id"]] = row["status"]
    return [s for spec in specs if latest.get(spec.item_id) == "refused" and spec.steps
            and spec.item_id not in NOT_ABOUT_ART
            for s in _in_states(spec)]


def main() -> None:
    """python -m scripts.adobe_observed_truth.illustrator_states --dataset <dir> --results <sweep>/results.jsonl

    Write state-families.jsonl: each declined menu command once in every state."""
    import argparse
    from dataclasses import asdict
    from pathlib import Path

    parser = argparse.ArgumentParser(description=main.__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--results", type=Path, required=True)
    args = parser.parse_args()
    rows = [json.loads(line) for line in (args.dataset / "menu-families.jsonl").read_text(encoding="utf-8").splitlines() if line]
    specs = [ScenarioSpec(**{**r, "steps": tuple(map(tuple, r["steps"])), "never_press": tuple(r["never_press"])}) for r in rows]
    retries = retry_in_states(args.results.read_text(encoding="utf-8").splitlines(), specs)
    with (args.dataset / "state-families.jsonl").open("w", encoding="utf-8", newline="\n") as out:
        out.writelines(json.dumps(asdict(s), sort_keys=True) + "\n" for s in retries)
    print(f"{len(retries)} state specs ({len(STATES)} states)")


if __name__ == "__main__":
    main()
