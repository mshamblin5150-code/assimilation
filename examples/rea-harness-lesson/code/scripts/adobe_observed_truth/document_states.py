"""Document states built on the test chart, for the commands a flat chart cannot run.

Many Photoshop commands need something on the canvas: Smart Objects need a smart object, Type
a text layer, Layer Mask a mask, Merge and Align several layers, Ungroup a group, Stroke a
selection, Layer from Background a background. On the flat chart Photoshop declines them
("not currently available"), so their code never runs. Each state here is an ExtendScript run
on the opened chart that builds one such thing, the same every time; retry_in_states() tries
each command refused on the flat chart once in every state (state_retry specs), so whichever
states let it run show its working code to the sampled sweep.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from dataclasses import replace

from .families import ScenarioSpec

_RECT = "[[60,60],[340,60],[340,240],[60,240]]"
_SELECT_TWO = (
    "var d=app.activeDocument;var b=d.activeLayer;"
    'var a=b.duplicate();a.name="observed-truth A";a.translate(30,20);'
    'var c=b.duplicate();c.name="observed-truth B";c.translate(-30,-20);'
    "d.activeLayer=a;var s=new ActionDescriptor();var r=new ActionReference();"
    'r.putName(charIDToTypeID("Lyr "),c.name);s.putReference(charIDToTypeID("null"),r);'
    's.putEnumerated(stringIDToTypeID("selectionModifier"),stringIDToTypeID("selectionModifierType"),'
    'stringIDToTypeID("addToSelection"));s.putBoolean(charIDToTypeID("MkVs"),false);'
    'executeAction(charIDToTypeID("slct"),s,DialogModes.NO);'
)
_WORK_PATH = f"var d=app.activeDocument;d.selection.select({_RECT});d.selection.makeWorkPath(1);"

STATES: dict[str, str] = {
    # The chart's layer converted to a smart object (Layer > Smart Objects > ...).
    "smart_object": 'executeAction(stringIDToTypeID("newPlacedLayer"),undefined,DialogModes.NO);"null";',
    # A text layer, active (Type > ...).
    "text": (
        'var d=app.activeDocument;var l=d.artLayers.add();l.kind=LayerKind.TEXT;l.name="observed-truth text";'
        'var t=l.textItem;t.contents="Observed truth 123";t.size=new UnitValue(24,"px");'
        't.position=[new UnitValue(20,"px"),new UnitValue(60,"px")];"null";'
    ),
    # A work path, no selection (Paths panel commands, Stroke/Fill Path).
    "path": _WORK_PATH + 'd.selection.deselect();"null";',
    # A solid colour layer masked by a vector path: a shape layer (vector mask commands).
    "shape": (
        _WORK_PATH
        + "var m=new ActionDescriptor();var r=new ActionReference();r.putClass(stringIDToTypeID(\"contentLayer\"));"
        'm.putReference(charIDToTypeID("null"),r);var u=new ActionDescriptor();var k=new ActionDescriptor();'
        'var c=new ActionDescriptor();c.putDouble(charIDToTypeID("Rd  "),200);c.putDouble(charIDToTypeID("Grn "),60);'
        'c.putDouble(charIDToTypeID("Bl  "),40);k.putObject(charIDToTypeID("Clr "),charIDToTypeID("RGBC"),c);'
        'u.putObject(charIDToTypeID("Type"),stringIDToTypeID("solidColorLayer"),k);'
        'm.putObject(charIDToTypeID("Usng"),stringIDToTypeID("contentLayer"),u);'
        'executeAction(charIDToTypeID("Mk  "),m,DialogModes.NO);"null";'
    ),
    # A copy of the chart with a revealing layer mask, active (Layer > Layer Mask > ...).
    "mask": (
        "var d=app.activeDocument;d.activeLayer=d.activeLayer.duplicate();"
        'var m=new ActionDescriptor();m.putClass(charIDToTypeID("Nw  "),charIDToTypeID("Chnl"));'
        'var r=new ActionReference();r.putEnumerated(charIDToTypeID("Chnl"),charIDToTypeID("Chnl"),charIDToTypeID("Msk "));'
        'm.putReference(charIDToTypeID("At  "),r);'
        'm.putEnumerated(charIDToTypeID("Usng"),charIDToTypeID("UsrM"),charIDToTypeID("RvlA"));'
        'executeAction(charIDToTypeID("Mk  "),m,DialogModes.NO);"null";'
    ),
    # A Curves adjustment layer above the chart, active (adjustment layer commands).
    "adjustment": (
        'var m=new ActionDescriptor();var r=new ActionReference();r.putClass(charIDToTypeID("AdjL"));'
        'm.putReference(charIDToTypeID("null"),r);var u=new ActionDescriptor();var k=new ActionDescriptor();'
        'k.putEnumerated(stringIDToTypeID("presetKind"),stringIDToTypeID("presetKindType"),'
        'stringIDToTypeID("presetKindDefault"));u.putObject(charIDToTypeID("Type"),charIDToTypeID("Crvs"),k);'
        'm.putObject(charIDToTypeID("Usng"),charIDToTypeID("AdjL"),u);'
        'executeAction(charIDToTypeID("Mk  "),m,DialogModes.NO);"null";'
    ),
    # Three layers, two of them selected (Merge, Align, Distribute, Link, Group).
    "layered": _SELECT_TWO + '"null";',
    # The two selected copies in a group (Ungroup, group blending).
    "group": (
        _SELECT_TWO
        + 'var g=new ActionDescriptor();var gr=new ActionReference();gr.putClass(stringIDToTypeID("layerSection"));'
        'g.putReference(charIDToTypeID("null"),gr);var f=new ActionReference();'
        'f.putEnumerated(charIDToTypeID("Lyr "),charIDToTypeID("Ordn"),charIDToTypeID("Trgt"));'
        'g.putReference(charIDToTypeID("From"),f);executeAction(charIDToTypeID("Mk  "),g,DialogModes.NO);"null";'
    ),
    # The chart flattened onto a Background layer (Layer from Background, Background commands).
    "background": 'app.activeDocument.flatten();"null";',
    # A copy clipped to the chart below it (Release Clipping Mask, clipped adjustments).
    "clipping": (
        "var d=app.activeDocument;d.activeLayer=d.activeLayer.duplicate();"
        'executeAction(stringIDToTypeID("groupEvent"),undefined,DialogModes.NO);"null";'
    ),
    # A drop shadow on the chart's layer (Layer Style commands: copy, clear, scale, rasterize).
    "layer_style": (
        'var m=new ActionDescriptor();var r=new ActionReference();r.putProperty(charIDToTypeID("Prpr"),charIDToTypeID("Lefx"));'
        'r.putEnumerated(charIDToTypeID("Lyr "),charIDToTypeID("Ordn"),charIDToTypeID("Trgt"));'
        'm.putReference(charIDToTypeID("null"),r);var fx=new ActionDescriptor();'
        'fx.putUnitDouble(charIDToTypeID("Scl "),charIDToTypeID("#Prc"),100);var s=new ActionDescriptor();'
        's.putBoolean(charIDToTypeID("enab"),true);s.putUnitDouble(charIDToTypeID("Dstn"),charIDToTypeID("#Pxl"),8);'
        's.putUnitDouble(charIDToTypeID("blur"),charIDToTypeID("#Pxl"),6);'
        'fx.putObject(charIDToTypeID("DrSh"),charIDToTypeID("DrSh"),s);'
        'm.putObject(charIDToTypeID("T   "),charIDToTypeID("Lefx"),fx);'
        'executeAction(charIDToTypeID("setd"),m,DialogModes.NO);"null";'
    ),
    # The chart's layer made an artboard (artboard commands). Event id checked live.
    # Made from the target layer, as Layer > New > Artboard from Layers records it: the event
    # artboardFromLayersEvent is refused by Photoshop 2026 (checked live 2026-11-24).
    "artboard": (
        "var d=new ActionDescriptor();var r=new ActionReference();"
        'r.putClass(stringIDToTypeID("artboardSection"));d.putReference(charIDToTypeID("null"),r);'
        'var l=new ActionReference();l.putEnumerated(charIDToTypeID("Lyr "),charIDToTypeID("Ordn"),charIDToTypeID("Trgt"));'
        'd.putReference(charIDToTypeID("From"),l);executeAction(charIDToTypeID("Mk  "),d,DialogModes.NO);"null";'
    ),
    # A blank video layer (Layer > Video Layers, Timeline). Event id checked live.
    "video": 'executeAction(stringIDToTypeID("addBlankVideoLayer"),undefined,DialogModes.NO);"null";',
    # A rectangular selection on the chart (Stroke, Select > Modify, Crop, Content-Aware).
    "selection": f'app.activeDocument.selection.select({_RECT});"null";',
    # An alpha channel holding that selection; the colour channels stay the ones edited.
    "alpha_channel": (
        f"var d=app.activeDocument;d.selection.select({_RECT});var c=d.channels.add();"
        'c.name="observed-truth alpha";d.selection.store(c);d.selection.deselect();'
        'd.activeChannels=d.componentChannels;"null";'
    ),
    # Quick Mask mode over that selection (Quick Mask editing, Select commands in it).
    "quick_mask": f'var d=app.activeDocument;d.selection.select({_RECT});d.quickMaskMode=true;"null";',
    # The chart in each image mode and depth: Photoshop offers and computes differently in each.
    "bits16": 'app.activeDocument.bitsPerChannel=BitsPerChannelType.SIXTEEN;"null";',
    "bits32": 'app.activeDocument.bitsPerChannel=BitsPerChannelType.THIRTYTWO;"null";',
    "cmyk": 'app.activeDocument.changeMode(ChangeMode.CMYK);"null";',
    "lab": 'app.activeDocument.changeMode(ChangeMode.LAB);"null";',
    "grayscale": 'app.activeDocument.changeMode(ChangeMode.GRAYSCALE);"null";',
    "indexed": (
        "var d=app.activeDocument;d.flatten();var o=new IndexedConversionOptions();"
        'o.palette=Palette.LOCALADAPTIVE;o.colors=256;d.changeMode(ChangeMode.INDEXEDCOLOR,o);"null";'
    ),
    "bitmap": (
        "var d=app.activeDocument;d.flatten();d.changeMode(ChangeMode.GRAYSCALE);var o=new BitmapConversionOptions();"
        'o.method=BitmapConversionType.DIFFUSIONDITHER;o.resolution=72;d.changeMode(ChangeMode.BITMAP,o);"null";'
    ),
    # A second open document, the chart active again (Apply Image, Calculations, Match Color).
    "second_document": (
        'var c=app.activeDocument;var n=app.documents.add(600,400,72,"observed-truth-second",NewDocumentMode.RGB);'
        'var s=new SolidColor();s.rgb.red=40;s.rgb.green=120;s.rgb.blue=200;n.selection.selectAll();'
        'n.selection.fill(s);n.selection.deselect();app.activeDocument=c;"null";'
    ),
}


def _in_states(spec: ScenarioSpec, states: Iterable[str] = STATES) -> list[ScenarioSpec]:
    return [
        replace(spec, item_id=f"{spec.item_id}@{state}", family="state_retry",
                steps=(spec.steps[0], ("build_state", state), *spec.steps[1:]))
        for state in states
    ]


def state_baselines() -> list[ScenarioSpec]:
    """Each state built on the chart with nothing run in it: what the state alone does to the
    chart, so a fact sheet can tell a feature's own effect in a state from the state's (a tool
    used in CMYK measured 78% changed against the chart, mostly the conversion)."""
    return [ScenarioSpec(f"state:{state}", "state_baseline", "run", False,
                         (("open_test_image", "chart"), ("build_state", state), ("record", "history", "pixels"),
                          ("close_throwaway_document",)))
            for state in STATES]


def _on_chart(spec: ScenarioSpec) -> bool:
    return (bool(spec.steps) and spec.steps[0] == ("open_test_image", "chart") and spec.safety == "run"
            and not _AI_OR_CLOUD.search(spec.item_id))


# Never used, in any state: Neural Filters, generative Remove, Prompt to Edit and the like were
# refused on the flat chart, and a state could let them run (caught before pass B, 2026-11-24).
_AI_OR_CLOUD = re.compile(r"neural|removeBrush|promptToEdit|generat|firefly|denoise", re.IGNORECASE)


def plan_states(results: Iterable[str], specs: list[ScenarioSpec]) -> list[ScenarioSpec]:
    """Pass B: every spec run on the chart, in every document state; first those Photoshop
    declined on the flat chart (retry_in_states), then the rest, which ran but may take other
    paths on other layers and modes. Tool selections are left to the tool pass."""
    retried = retry_in_states(results, specs)
    first = {s.item_id.rsplit("@", 1)[0] for s in retried}
    rest = [s for spec in specs if _on_chart(spec) and spec.family != "tool_shortcut" and spec.item_id not in first
            for s in _in_states(spec)]
    return retried + rest


# The trimmed pass B (2026-11-24): the goal is enough to rebuild each feature, so each filter,
# adjustment and fill runs once in the states that change what it does, not in all 24.
FEATURE_STATES = ("smart_object", "selection", "mask", "bits16", "bits32", "cmyk")
_FEATURE_PATHS = re.compile(r"^(Filter >|Image > Adjustments >|Edit > Fill|Layer > New Fill Layer >)")
_NOT_A_FEATURE = re.compile(r"Last Filter|NextGen|AI Denoise|AI Sharpen|Neural|Parametric")


def plan_feature_states(results: Iterable[str], specs: list[ScenarioSpec],
                        paths: dict[str, str]) -> list[ScenarioSpec]:
    """Pass B, trimmed: each filter, adjustment and fill command (menu `paths` by item id) run on
    the chart, once in each FEATURE_STATES state. A command with a dialog runs as its chart effect
    (the dialog accepted with its defaults), so the work is done, not cancelled. Its per-choice and
    control variants ran on the chart and are not repeated; refusals were retried in every state
    (retry_in_states); the previous-filter repeat and the AI and cloud filters are left out."""
    refused = {s.item_id.rsplit("@", 1)[0] for s in retry_in_states(results, specs)}
    applied = {spec.item_id: spec for spec in specs if spec.family == "image_effect"}
    return [
        s for spec in specs
        if spec.family == "menu_command" and _on_chart(spec) and spec.item_id not in refused
        and _FEATURE_PATHS.match(path := paths.get(spec.item_id, "")) and not _NOT_A_FEATURE.search(path)
        for s in _in_states(applied.get(f"{spec.item_id}@chart", spec), FEATURE_STATES)
    ]


def retry_in_states(results: Iterable[str], specs: list[ScenarioSpec]) -> list[ScenarioSpec]:
    """Each spec run on the chart whose latest result (results.jsonl lines) is Photoshop
    declining it, as one state_retry spec per document state: the state built right after the
    chart opens, then the spec's own steps."""
    latest: dict[str, dict] = {}
    for line in results:
        if line.strip():
            row = json.loads(line)
            latest[row["item_id"]] = row
    return [s for spec in specs
            if latest.get(spec.item_id, {}).get("status") == "refused" and _on_chart(spec)
            for s in _in_states(spec)]


def main() -> None:
    """python -m scripts.adobe_observed_truth.document_states --dataset <dir> --results <sweep>/results.jsonl

    Write state-families.jsonl (pass B) from the dataset's chart specs (scenario and dialog
    control families) and a sweep's results; run it with runner_photoshop --specs state-families.jsonl."""
    import argparse
    from dataclasses import asdict
    from pathlib import Path

    parser = argparse.ArgumentParser(description=main.__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--results", type=Path)
    parser.add_argument("--features", action="store_true",
                        help="the trimmed pass: filters, adjustments and fills in FEATURE_STATES only")
    parser.add_argument("--baselines", action="store_true",
                        help="each state built alone, to state-baseline-families.jsonl (no --results needed)")
    args = parser.parse_args()
    if args.baselines:
        with (args.dataset / "state-baseline-families.jsonl").open("w", encoding="utf-8", newline="\n") as out:
            out.writelines(json.dumps(asdict(s), sort_keys=True) + "\n" for s in state_baselines())
        print(f"{len(STATES)} state baselines written to state-baseline-families.jsonl")
        return
    if args.results is None:
        parser.error("--results is required")
    specs = []
    for name in ("scenario-families.jsonl", "control-families.jsonl"):
        for line in (args.dataset / name).read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            specs.append(ScenarioSpec(**{**row, "steps": tuple(map(tuple, row["steps"])),
                                         "never_press": tuple(row["never_press"])}))
    results = args.results.read_text(encoding="utf-8").splitlines()
    if args.features:
        inventory = (json.loads(line) for line in (args.dataset / "inventory.jsonl").read_text(encoding="utf-8").splitlines())
        planned = plan_feature_states(results, specs, {row["id"]: row.get("path", "") for row in inventory})
    else:
        planned = plan_states(results, specs)
    name = "feature-state-families.jsonl" if args.features else "state-families.jsonl"
    with (args.dataset / name).open("w", encoding="utf-8", newline="\n") as out:
        out.writelines(json.dumps(asdict(s), sort_keys=True) + "\n" for s in planned)
    print(f"{len(planned)} state specs written to {name}")


if __name__ == "__main__":
    main()
