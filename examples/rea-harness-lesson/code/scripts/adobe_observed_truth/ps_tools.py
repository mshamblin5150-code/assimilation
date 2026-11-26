"""Select Photoshop tools, set and read their options, and apply them by script.

Tool options and the foreground/background colours are the user's persistent state.
preserved_tool_state() snapshots them as ActionDescriptor streams and writes them
back byte for byte, then reports whether each one reads back identical.

Tools are applied the way their own recorded events do: brush and eraser by
stroking a work path with that tool (one anchor is a single dab), paint bucket by
the Fill event with a "From" point. None of this is mouse input.
"""

from __future__ import annotations

import json
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from typing import Any

from .photoshop import Photoshop


TOOL_CLASSES = {"brush": "paintbrushTool", "eraser": "eraserTool", "bucket": "bucketTool",
                "dodge": "dodgeTool", "burn": "burnInTool", "sponge": "saturationTool",
                "magnetic_lasso": "magneticLassoTool", "smudge": "smudgeTool",
                "spot_healing": "spotHealingBrushTool"}
STROKE_TOOL_TYPES = {"brush": "ToolType.BRUSH", "eraser": "ToolType.ERASER", "dodge": "ToolType.DODGE",
                     "burn": "ToolType.BURN", "sponge": "ToolType.SPONGE", "smudge": "ToolType.SMUDGE"}
# Brush-engine features that would make a scripted dab differ from a plain round tip.
_DYNAMICS_FLAGS = (
    "useTipDynamics",
    "useScatter",
    "useTexture",
    "useColorDynamics",
    "usePaintDynamics",
    "wetEdges",
    "noise",
    "repeat",
    "useBrushPose",
)

_JS = r"""
function sid(s){return stringIDToTypeID(s);}
function cid(s){return charIDToTypeID(s);}
function tn(t){var s=typeIDToStringID(t);return s?s:typeIDToCharID(t);}
function hex(s){var h=[];for(var i=0;i<s.length;i++){var c=s.charCodeAt(i).toString(16);
 h.push(c.length<2?"0"+c:c);}return h.join("");}
function unhex(h){var s="";for(var i=0;i<h.length;i+=2)s+=String.fromCharCode(parseInt(h.substr(i,2),16));return s;}
function appGet(key){var r=new ActionReference();r.putProperty(sid("property"),sid(key));
 r.putEnumerated(cid("capp"),cid("Ordn"),cid("Trgt"));return executeActionGet(r);}
function toolNow(){return tn(appGet("tool").getEnumerationType(sid("tool")));}
function selectTool(t){var d=new ActionDescriptor(),r=new ActionReference();r.putClass(sid(t));
 d.putReference(cid("null"),r);executeAction(cid("slct"),d,DialogModes.NO);}
function toolOptions(){return appGet("currentToolOptions").getObjectValue(sid("currentToolOptions"));}
function setToolOptions(t,o){var d=new ActionDescriptor(),r=new ActionReference();r.putClass(sid(t));
 d.putReference(cid("null"),r);d.putObject(cid("T   "),sid("currentToolOptions"),o);
 executeAction(cid("setd"),d,DialogModes.NO);}
function colourGet(code){var r=new ActionReference();r.putProperty(cid("Prpr"),cid(code));
 r.putEnumerated(cid("capp"),cid("Ordn"),cid("Trgt"));var d=executeActionGet(r);
 return {cls:d.getObjectType(cid(code)),value:d.getObjectValue(cid(code))};}
function colourSet(code,cls,value){var d=new ActionDescriptor(),r=new ActionReference();
 r.putProperty(cid("Clr "),cid(code));d.putReference(cid("null"),r);d.putObject(cid("T   "),cls,value);
 executeAction(cid("setd"),d,DialogModes.NO);}
function colourJson(code){var c=colourGet(code);return '{"class":'+q(tn(c.cls))+',"stream":'+q(hex(c.value.toStream()))+'}';}
"""


def snapshot_tool_state(ps: Photoshop, tools: Sequence[str]) -> dict[str, Any]:
    """Current tool, each named tool's options, and the two colour chips, as descriptor streams."""
    snapshot = ps.js(_JS + '"{\\"tool\\":"+q(toolNow())+",\\"foreground\\":"+colourJson("FrgC")'
                     '+",\\"background\\":"+colourJson("BckC")+"}";')
    snapshot["options"] = {}
    for tool in tools:
        snapshot["options"][tool] = ps.js(
            _JS + f'selectTool({json.dumps(TOOL_CLASSES[tool])});q(hex(toolOptions().toStream()));'
        )
    ps.js(_JS + f'selectTool({json.dumps(snapshot["tool"])});"null";')
    return snapshot


def restore_tool_state(ps: Photoshop, snapshot: dict[str, Any]) -> dict[str, Any]:
    """Write the snapshot back and report, per item, whether it now reads back identical."""
    restored: dict[str, Any] = {"options": {}}
    for tool, stream in snapshot["options"].items():
        cls = json.dumps(TOOL_CLASSES[tool])
        restored["options"][tool] = ps.js(
            _JS + f'selectTool({cls});var o=new ActionDescriptor();o.fromStream(unhex({json.dumps(stream)}));'
            f'setToolOptions({cls},o);String(hex(toolOptions().toStream())=={json.dumps(stream)});'
        )
    for name, code in (("foreground", "FrgC"), ("background", "BckC")):
        colour = snapshot[name]
        restored[name] = ps.js(
            _JS + f'var v=new ActionDescriptor();v.fromStream(unhex({json.dumps(colour["stream"])}));'
            f'colourSet({json.dumps(code)},sid({json.dumps(colour["class"])}),v);'
            f'String(colourJson({json.dumps(code)})=={json.dumps(json.dumps(colour, separators=(",", ":")))});'
        )
    tool = json.dumps(snapshot["tool"])
    restored["tool"] = ps.js(_JS + f'selectTool({tool});String(toolNow()=={tool});')
    return restored


@contextmanager
def preserved_tool_state(ps: Photoshop, tools: Sequence[str]) -> Iterator[dict[str, Any]]:
    """Yield a dict that holds {'restored': ...} once the user's tool state is written back."""
    report: dict[str, Any] = {}
    snapshot = snapshot_tool_state(ps, tools)
    try:
        yield report
    finally:
        report["restored"] = restore_tool_state(ps, snapshot)


def all_restored(restored: dict[str, Any]) -> bool:
    return (
        all(restored["options"].values())
        and restored["foreground"]
        and restored["background"]
        and restored["tool"]
    )


def set_colours(ps: Photoshop, foreground: Sequence[int], background: Sequence[int] = (255, 255, 255)) -> None:
    def colour(rgb: Sequence[int]) -> str:
        return f"(function(){{var c=new SolidColor();c.rgb.red={rgb[0]};c.rgb.green={rgb[1]};c.rgb.blue={rgb[2]};return c;}})()"

    ps.js(f'app.foregroundColor={colour(foreground)};app.backgroundColor={colour(background)};"null";')


def set_brush_options(
    ps: Photoshop,
    tool: str,
    *,
    size_px: int,
    hardness: int,
    opacity: int,
    flow: int,
    spacing: int,
    angle: int = 0,
    roundness: int = 100,
    eraser_mode: int | None = None,
    pressure_size: bool = False,
    pressure_opacity: bool = False,
    dynamics: dict[str, Any] | None = None,
    sampled: bool = False,
) -> dict[str, Any]:
    """Select brush or eraser, give it a fresh round computed tip with dynamics off; return what it reads back.

    The options bar's pressure switches (pen pressure sets size, sets opacity) are always set,
    off unless asked: one left on by an earlier run faded the next run's stroke (2026-11-25).
    `dynamics` (batchPlay-style JSON, see descriptor_puts_js) is put over the options after
    the dynamics are switched off, so a probe turns on exactly what it names. With `sampled`,
    the brush keeps its current sampled tip (a defined preset) and only its size, angle,
    roundness and spacing are set; hardness does not apply."""
    cls = json.dumps(TOOL_CLASSES[tool])
    flags = json.dumps(list(_DYNAMICS_FLAGS))
    eraser = "" if eraser_mode is None else f'o.putInteger(cid("ErsB"),{int(eraser_mode)});'
    switches = (f'if(o.hasKey(sid("usePressureOverridesSize")))'
                f'o.putBoolean(sid("usePressureOverridesSize"),{json.dumps(pressure_size)});'
                f'if(o.hasKey(sid("usePressureOverridesOpacity")))'
                f'o.putBoolean(sid("usePressureOverridesOpacity"),{json.dumps(pressure_opacity)});')
    tip = ('var b=o.getObjectValue(sid("brush"));if(tn(o.getObjectType(sid("brush")))!="sampledBrush")'
           'throw new Error("the brush has no sampled tip");' if sampled else
           f'var b=new ActionDescriptor();b.putUnitDouble(sid("hardness"),cid("#Prc"),{int(hardness)});')
    ps.js(
        _JS + f"selectTool({cls});var o=toolOptions();" + tip +
        f'b.putUnitDouble(sid("diameter"),cid("#Pxl"),{int(size_px)});'
        f'b.putUnitDouble(sid("angle"),cid("#Ang"),{int(angle)});b.putUnitDouble(sid("roundness"),cid("#Prc"),{int(roundness)});'
        f'b.putUnitDouble(sid("spacing"),cid("#Prc"),{int(spacing)});'
        'b.putBoolean(sid("interfaceIconFrameDimmed"),true);'
        'b.putBoolean(sid("flipX"),false);b.putBoolean(sid("flipY"),false);'
        f'o.putObject(sid("brush"),sid({json.dumps("sampledBrush" if sampled else "computedBrush")}),b);'
        f'o.putInteger(sid("opacity"),{int(opacity)});o.putInteger(sid("flow"),{int(flow)});'
        f"var f={flags};for(var i=0;i<f.length;i++)if(o.hasKey(sid(f[i])))o.putBoolean(sid(f[i]),false);"
        'if(o.hasKey(sid("dualBrush"))){var db=new ActionDescriptor();db.putBoolean(sid("useDualBrush"),false);'
        'o.putObject(sid("dualBrush"),sid("dualBrush"),db);}'
        f'{eraser}{switches}{descriptor_puts_js("o", dynamics or {})}setToolOptions({cls},o);"null";'
    )
    return read_brush_options(ps, tool)


# A name as the descriptor dump writes it back to its id: a 4-character name with no string ID
# is a char code (szVr, brVr, bVTy), anything else a string ID.
_KID_JS = ("function kid(s){if(s.length==4){var c=charIDToTypeID(s),n='';try{n=typeIDToStringID(c);}catch(e){}"
           "if(!n)return c;}return stringIDToTypeID(s);}")


def descriptor_puts_js(var: str, values: dict[str, Any]) -> str:
    """ExtendScript putting batchPlay-style JSON values on the ActionDescriptor `var`: a bool,
    int or float as itself; {"_unit", "_value"} a unit double; {"_enum", "_value"} an
    enumeration; {"_obj": class, ...} a nested descriptor (built in its own variable). Names
    resolve as the dump wrote them (kid): a bare char code is put as that code, since putting
    it by string ID silently makes a new, unrelated key."""
    lines: list[str] = []

    def put(target: str, key: str, value: Any, depth: int) -> None:
        k = f"kid({json.dumps(key)})"
        if isinstance(value, bool):
            lines.append(f"{target}.putBoolean({k},{json.dumps(value)});")
        elif isinstance(value, int):
            lines.append(f"{target}.putInteger({k},{value});")
        elif isinstance(value, str):
            lines.append(f"{target}.putString({k},{json.dumps(value)});")
        elif isinstance(value, float):
            lines.append(f"{target}.putDouble({k},{json.dumps(value)});")
        elif "_unit" in value:
            lines.append(f"{target}.putUnitDouble({k},kid({json.dumps(value['_unit'])}),{json.dumps(float(value['_value']))});")
        elif "_enum" in value:
            lines.append(f"{target}.putEnumerated({k},kid({json.dumps(value['_enum'])}),kid({json.dumps(value['_value'])}));")
        else:
            inner = f"{var}_{depth}_{len(lines)}"
            lines.append(f"var {inner}=new ActionDescriptor();")
            for sub_key, sub_value in value.items():
                if sub_key != "_obj":
                    put(inner, sub_key, sub_value, depth + 1)
            lines.append(f"{target}.putObject({k},kid({json.dumps(value['_obj'])}),{inner});")

    for key, value in values.items():
        put(var, key, value, 0)
    return (_KID_JS if lines else "") + "".join(lines)


def dump_tool_options(ps: Photoshop, tool: str) -> dict[str, Any]:
    """The tool's current options as batchPlay-style JSON (every key, with its type)."""
    from .action_settings import _DESCRIPTOR_JS

    return ps.js(_JS + _DESCRIPTOR_JS + f"selectTool({json.dumps(TOOL_CLASSES[tool])});o2j(toolOptions(),null);")


def set_retouch_options(ps: Photoshop, tool: str, *, size_px: int, mode: str, strength: int, legacy: bool) -> dict[str, Any]:
    """Select Dodge, Burn or Sponge with a hard round tip and dynamics off; set its range or mode
    (a blendMode value: dodgeS/M/H, burnInS/M/H, saturate, desaturate), its strength (exposure,
    or the sponge's flow) and its legacy switch (off: protect tones / vibrance on). Returns what
    it reads back."""
    cls = json.dumps(TOOL_CLASSES[tool])
    key = "flow" if tool == "sponge" else "exposure"
    flags = json.dumps(list(_DYNAMICS_FLAGS))
    return ps.js(
        _JS + f"selectTool({cls});var o=toolOptions();var b=new ActionDescriptor();"
        f'b.putUnitDouble(sid("diameter"),cid("#Pxl"),{int(size_px)});b.putUnitDouble(sid("hardness"),cid("#Prc"),100);'
        'b.putUnitDouble(sid("angle"),cid("#Ang"),0);b.putUnitDouble(sid("roundness"),cid("#Prc"),100);'
        'b.putUnitDouble(sid("spacing"),cid("#Prc"),25);b.putBoolean(sid("interfaceIconFrameDimmed"),true);'
        'b.putBoolean(sid("flipX"),false);b.putBoolean(sid("flipY"),false);o.putObject(sid("brush"),sid("computedBrush"),b);'
        f'o.putEnumerated(sid("mode"),sid("blendMode"),sid({json.dumps(mode)}));o.putInteger(sid({json.dumps(key)}),{int(strength)});'
        f'o.putBoolean(sid("useLegacy"),{json.dumps(legacy)});o.putBoolean(sid("usePaintDynamics"),false);'
        f"var f={flags};for(var i=0;i<f.length;i++)if(o.hasKey(sid(f[i])))o.putBoolean(sid(f[i]),false);"
        f"setToolOptions({cls},o);o=toolOptions();"
        f"'{{\"mode\":'+q(tn(o.getEnumerationValue(sid(\"mode\"))))+',\"strength\":'+o.getInteger(sid({json.dumps(key)}))"
        "+',\"legacy\":'+o.getBoolean(sid(\"useLegacy\"))+',\"size_px\":'+Math.round(o.getObjectValue(sid(\"brush\")).getUnitDoubleValue(sid(\"diameter\")))+'}';"
    )


def read_brush_options(ps: Photoshop, tool: str) -> dict[str, Any]:
    """Options as Photoshop reports them. Unit values are rounded to integers and kept exact as strings."""
    flags = json.dumps(list(_DYNAMICS_FLAGS))
    return ps.js(
        _JS + f"selectTool({json.dumps(TOOL_CLASSES[tool])});var o=toolOptions();"
        'var b=o.getObjectValue(sid("brush"));var cls=tn(o.getObjectType(sid("brush")));'
        'function u(k){return b.hasKey(sid(k))?b.getUnitDoubleValue(sid(k)):null;}'
        'function n(k){var v=u(k);return v===null?"null":String(Math.round(v));}'
        'function s(k){var v=u(k);return v===null?"null":q(String(v));}'
        f"var f={flags},on=[];for(var i=0;i<f.length;i++)if(o.hasKey(sid(f[i]))&&o.getBoolean(sid(f[i])))on.push(q(f[i]));"
        'if(o.hasKey(sid("dualBrush"))&&o.getObjectValue(sid("dualBrush")).getBoolean(sid("useDualBrush")))on.push(q("dualBrush"));'
        "'{\"tip_class\":'+q(cls)+',\"size_px\":'+n(\"diameter\")+',\"hardness\":'+n(\"hardness\")"
        "+',\"spacing\":'+n(\"spacing\")+',\"exact\":{\"size_px\":'+s(\"diameter\")+',\"hardness\":'+s(\"hardness\")"
        "+',\"spacing\":'+s(\"spacing\")+'},\"opacity\":'+o.getInteger(sid(\"opacity\"))"
        "+',\"flow\":'+o.getInteger(sid(\"flow\"))"
        "+',\"eraser_mode\":'+(o.hasKey(cid(\"ErsB\"))?o.getInteger(cid(\"ErsB\")):'null')"
        "+',\"dynamics_on\":['+on.join(',')+']}';"
    )


def set_bucket_options(
    ps: Photoshop, *, tolerance: int, anti_alias: bool, contiguous: bool, all_layers: bool
) -> dict[str, Any]:
    """Select the paint bucket and set its options-bar values; return what it reads back."""
    ps.js(
        _JS + 'selectTool("bucketTool");var o=toolOptions();'
        f'o.putInteger(cid("BckT"),{int(tolerance)});o.putBoolean(cid("BckA"),{json.dumps(anti_alias)});'
        f'o.putBoolean(sid("contiguous"),{json.dumps(contiguous)});o.putBoolean(cid("BckS"),{json.dumps(all_layers)});'
        'o.putInteger(sid("opacity"),100);o.putEnumerated(sid("mode"),sid("blendMode"),sid("normal"));'
        'setToolOptions("bucketTool",o);"null";'
    )
    return read_bucket_options(ps)


def read_bucket_options(ps: Photoshop) -> dict[str, Any]:
    return ps.js(
        _JS + 'selectTool("bucketTool");var o=toolOptions();'
        "'{\"tolerance\":'+o.getInteger(cid(\"BckT\"))+',\"anti_alias\":'+o.getBoolean(cid(\"BckA\"))"
        "+',\"contiguous\":'+o.getBoolean(sid(\"contiguous\"))+',\"all_layers\":'+o.getBoolean(cid(\"BckS\"))"
        "+',\"opacity\":'+o.getInteger(sid(\"opacity\"))+',\"mode\":'+q(tn(o.getEnumerationValue(sid(\"mode\"))))"
        "+',\"fill_pattern\":'+o.getBoolean(cid(\"BckF\"))+'}';"
    )


def stroke(ps: Photoshop, tool: str, points: Sequence[tuple[int, int]], *, simulate_pressure: bool = False) -> None:
    """Stroke an open work path through the centres of the given pixels with brush or eraser.

    One point is a single dab. The path is removed afterwards; it leaves Set Path,
    Save Path, Stroke Path and Delete Path in History. Needs a 72 ppi document so
    path points (in points) equal pixels.
    """
    anchors = ",".join(f"[{x}+0.5,{y}+0.5]" for x, y in points)
    ps.js(
        "var doc=app.activeDocument;"
        'if(doc.resolution!=72)throw new Error("stroke() needs a 72 ppi document");'
        f"var a=[{anchors}],pts=[];for(var i=0;i<a.length;i++){{var p=new PathPointInfo();"
        "p.kind=PointKind.CORNERPOINT;p.anchor=a[i];p.leftDirection=a[i];p.rightDirection=a[i];pts.push(p);}"
        "var sp=new SubPathInfo();sp.operation=ShapeOperation.SHAPEADD;sp.closed=false;sp.entireSubPath=pts;"
        'var wp=doc.pathItems.add("observed-truth-stroke",[sp]);'
        f"try{{wp.strokePath({STROKE_TOOL_TYPES[tool]},{json.dumps(simulate_pressure)});}}finally{{wp.remove();}}\"null\";"
    )


def stroke_with(ps: Photoshop, tool: str, points: Sequence[tuple[int, int]]) -> None:
    """Stroke an open work path through the centres of the given pixels with any tool, by the
    stroke-path event naming the tool's class: for tools Photoshop's ToolType lacks (the Spot
    Healing Brush). Needs a 72 ppi document; the path is removed afterwards."""
    anchors = ",".join(f"[{x}+0.5,{y}+0.5]" for x, y in points)
    ps.js(
        "var doc=app.activeDocument;"
        'if(doc.resolution!=72)throw new Error("stroke_with() needs a 72 ppi document");'
        f"var a=[{anchors}],pts=[];for(var i=0;i<a.length;i++){{var p=new PathPointInfo();"
        "p.kind=PointKind.CORNERPOINT;p.anchor=a[i];p.leftDirection=a[i];p.rightDirection=a[i];pts.push(p);}"
        "var sp=new SubPathInfo();sp.operation=ShapeOperation.SHAPEADD;sp.closed=false;sp.entireSubPath=pts;"
        'var wp=doc.pathItems.add("observed-truth-stroke",[sp]);'
        "try{var d=new ActionDescriptor(),r=new ActionReference();r.putName(charIDToTypeID('Path'),'observed-truth-stroke');"
        "d.putReference(charIDToTypeID('null'),r);"
        f"d.putClass(charIDToTypeID('Usng'),stringIDToTypeID({json.dumps(TOOL_CLASSES[tool])}));"
        "executeAction(charIDToTypeID('Strk'),d,DialogModes.NO);}finally{wp.remove();}\"null\";"
    )


def wand_select(ps: Photoshop, x: int, y: int, *, tolerance: int, anti_alias: bool, contiguous: bool) -> None:
    """A Magic Wand click at pixel (x, y) by the tool's recorded event (set the selection to a
    point), so the tool need not be selected. Replaces any selection."""
    ps.js(
        _JS + "var d=new ActionDescriptor(),r=new ActionReference(),p=new ActionDescriptor();"
        'r.putProperty(cid("Chnl"),sid("selection"));d.putReference(cid("null"),r);'
        f'p.putUnitDouble(cid("Hrzn"),cid("#Pxl"),{int(x)});p.putUnitDouble(cid("Vrtc"),cid("#Pxl"),{int(y)});'
        'd.putObject(cid("T   "),cid("Pnt "),p);'
        f'd.putInteger(cid("Tlrn"),{int(tolerance)});d.putBoolean(cid("AntA"),{json.dumps(anti_alias)});'
        f'd.putBoolean(cid("Cntg"),{json.dumps(contiguous)});'
        'executeAction(cid("setd"),d,DialogModes.NO);"null";'
    )


def bucket_fill(ps: Photoshop, x: int, y: int, options: dict[str, Any]) -> None:
    """The paint bucket's own Fill event at pixel (x, y), with the options the tool reads back.

    ScriptListener omits Cntg and Mrgd at their defaults; they are always sent here. The point is
    the pixel's own coordinate: sent as x + 0.5 it took the pixel to the right and below.
    """
    ps.js(
        _JS + "var d=new ActionDescriptor(),p=new ActionDescriptor();"
        f'p.putUnitDouble(cid("Hrzn"),cid("#Pxl"),{int(x)});p.putUnitDouble(cid("Vrtc"),cid("#Pxl"),{int(y)});'
        'd.putObject(cid("From"),cid("Pnt "),p);'
        f'd.putInteger(cid("Tlrn"),{int(options["tolerance"])});'
        f'd.putBoolean(cid("AntA"),{json.dumps(options["anti_alias"])});'
        'd.putEnumerated(cid("Usng"),cid("FlCn"),cid("FrgC"));'
        f'd.putBoolean(cid("Cntg"),{json.dumps(options["contiguous"])});'
        f'd.putBoolean(cid("Mrgd"),{json.dumps(options["all_layers"])});'
        'executeAction(cid("Fl  "),d,DialogModes.NO);"null";'
    )


_SELECTION_TYPES = {"replace": "SelectionType.REPLACE", "extend": "SelectionType.EXTEND",
                    "diminish": "SelectionType.DIMINISH", "intersect": "SelectionType.INTERSECT"}


def selection_ops_js(ops: Sequence[Sequence[Any]]) -> str:
    """ExtendScript running selection operations on the active document, in order:
    ["rect" | "ellipse", left, top, right, bottom, anti_alias, mode], ["feather", px],
    ["store", channel] (to a new alpha channel), ["load", channel, mode], ["deselect"],
    ["expand" | "contract" | "border", px], ["smooth", px], ["grow", tolerance, anti_alias],
    ["color_range", fuzziness, [L, a, b] low, [L, a, b] high, colour model],
    ["refine_edge", radius px, smart radius, contrast %, smooth, feather px, shift edge %].
    Modes: replace, extend, diminish, intersect. The composite channels stay the active ones."""
    lines = ["var doc=app.activeDocument;function comp(){doc.activeChannels=doc.componentChannels;}"]
    for op in ops:
        kind = op[0]
        if kind == "rect":
            l, t, r, b, aa, mode = op[1:]
            lines.append(f"doc.selection.select([[{l},{t}],[{r},{t}],[{r},{b}],[{l},{b}]],{_SELECTION_TYPES[mode]},0,{json.dumps(aa)});")
        elif kind == "ellipse":
            l, t, r, b, aa, mode = op[1:]
            if mode != "replace":
                raise ValueError("ellipses replace the selection")
            lines.append(
                "var d=new ActionDescriptor(),r=new ActionReference();r.putProperty(charIDToTypeID('Chnl'),charIDToTypeID('fsel'));"
                "d.putReference(charIDToTypeID('null'),r);var e=new ActionDescriptor();"
                f"e.putUnitDouble(charIDToTypeID('Top '),charIDToTypeID('#Pxl'),{t});e.putUnitDouble(charIDToTypeID('Left'),charIDToTypeID('#Pxl'),{l});"
                f"e.putUnitDouble(charIDToTypeID('Btom'),charIDToTypeID('#Pxl'),{b});e.putUnitDouble(charIDToTypeID('Rght'),charIDToTypeID('#Pxl'),{r});"
                f"d.putObject(charIDToTypeID('T   '),charIDToTypeID('Elps'),e);d.putBoolean(charIDToTypeID('AntA'),{json.dumps(aa)});"
                "executeAction(charIDToTypeID('setd'),d,DialogModes.NO);")
        elif kind == "feather":
            lines.append(f"doc.selection.feather({float(op[1])});")
        elif kind == "store":
            lines.append(f"var ch=doc.channels.add();ch.name={json.dumps(op[1])};comp();doc.selection.store(ch,SelectionType.REPLACE);comp();")
        elif kind == "load":
            lines.append(f"doc.selection.load(doc.channels.getByName({json.dumps(op[1])}),{_SELECTION_TYPES[op[2]]});comp();")
        elif kind == "deselect":
            lines.append("doc.selection.deselect();")
        elif kind in ("expand", "contract"):
            lines.append(f"doc.selection.{kind}(UnitValue({float(op[1])},'px'));")
        elif kind == "border":
            lines.append(f"doc.selection.selectBorder(UnitValue({float(op[1])},'px'));")
        elif kind == "smooth":
            lines.append(f"doc.selection.smooth({int(op[1])});")
        elif kind == "grow":
            lines.append(f"doc.selection.grow({int(op[1])},{json.dumps(op[2])});")
        elif kind == "refine_edge":
            radius, smart, contrast, smooth, feather, shift = op[1:]
            lines.append(
                "var d=new ActionDescriptor();"
                f"d.putUnitDouble(stringIDToTypeID('refineEdgeBorderRadius'),charIDToTypeID('#Pxl'),{float(radius)});"
                f"d.putUnitDouble(stringIDToTypeID('refineEdgeBorderContrast'),charIDToTypeID('#Prc'),{float(contrast)});"
                f"d.putInteger(stringIDToTypeID('refineEdgeSmooth'),{int(smooth)});"
                f"d.putUnitDouble(stringIDToTypeID('refineEdgeFeatherRadius'),charIDToTypeID('#Pxl'),{float(feather)});"
                f"d.putUnitDouble(stringIDToTypeID('refineEdgeChoke'),charIDToTypeID('#Prc'),{float(shift)});"
                f"d.putBoolean(stringIDToTypeID('refineEdgeAutoRadius'),{json.dumps(smart)});"
                "d.putBoolean(stringIDToTypeID('refineEdgeDecontaminate'),false);"
                "d.putEnumerated(stringIDToTypeID('refineEdgeOutput'),stringIDToTypeID('refineEdgeOutput'),stringIDToTypeID('selectionOutputToSelection'));"
                "executeAction(stringIDToTypeID('refineSelectionEdge'),d,DialogModes.NO);")
        elif kind == "color_range":
            fuzziness, low, high, model = op[1:]
            lab = lambda name, v: (f"var {name}=new ActionDescriptor();{name}.putDouble(stringIDToTypeID('luminance'),{float(v[0])});"
                                   f"{name}.putDouble(stringIDToTypeID('a'),{float(v[1])});{name}.putDouble(stringIDToTypeID('b'),{float(v[2])});")
            lines.append(
                "var d=new ActionDescriptor();" + lab("lo", low) + lab("hi", high)
                + f"d.putInteger(stringIDToTypeID('fuzziness'),{int(fuzziness)});"
                "d.putObject(stringIDToTypeID('minimum'),stringIDToTypeID('labColor'),lo);"
                "d.putObject(stringIDToTypeID('maximum'),stringIDToTypeID('labColor'),hi);"
                f"d.putInteger(stringIDToTypeID('colorModel'),{int(model)});"
                "executeAction(stringIDToTypeID('colorRange'),d,DialogModes.NO);")
        else:
            raise ValueError(f"unknown selection operation {kind!r}")
    return "".join(lines) + '"null";'


def selection_pixel_count(ps: Photoshop) -> int | None:
    """Photoshop's histogram pixel count for the active selection (None with no selection)."""
    return ps.js("var doc=app.activeDocument,has=true;try{doc.selection.bounds;}catch(e){has=false;}"
                 "if(!has){'null';}else{var h=doc.histogram,n=0;for(var i=0;i<h.length;i++)n+=h[i];String(n);}")


def set_tool_options(ps: Photoshop, tool: str, values: dict[str, Any]) -> dict[str, Any]:
    """Select `tool` and put batchPlay-style `values` over its options; return them as read back."""
    from .action_settings import _DESCRIPTOR_JS

    cls = json.dumps(TOOL_CLASSES[tool])
    return ps.js(_JS + _DESCRIPTOR_JS + f"selectTool({cls});var o=toolOptions();"
                 + descriptor_puts_js("o", values) + f"setToolOptions({cls},o);o2j(toolOptions(),null);")
