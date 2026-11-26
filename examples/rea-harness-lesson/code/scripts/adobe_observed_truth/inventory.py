"""Everything an Adobe app reports it can do, as flat records: the denominator for "test it all".

Built from what the app enumerates about itself (menus, tools, panels, preferences, shortcut
sets), not from its help, which is incomplete and sometimes wrong. Help claims, decompile
findings and observations attach to these records by `id`.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from xml.etree import ElementTree  # the shortcut sets are the app's own install files


@dataclass(frozen=True)
class Item:
    kind: str  # menu_command, submenu, tool, panel, preference, shortcut
    id: str
    name: str
    path: str  # where a person finds it in the UI
    facts: dict[str, Any]


# Never recorded, wherever they appear: the licence, file and machine identity.
PRIVATE_KEYS = frozenset(
    {
        "serialString",
        "recentFiles",
        "recentFilesAsStrings",
        "hostName",
        "systemInfo",
        "systemInfoSections",
        "preferencesFolder",
        "path",
        "executablePath",
        "MRUColorList",
        "fontList",
    }
)
_TOOL_SHORTCUT = re.compile(r"^(?P<name>.*?)\s*\((?P<key>[^()]+)\)$")


def build_inventory(raw: dict[str, Any]) -> list[Item]:
    items: list[Item] = []
    if "menus" in raw:
        items.extend(_merge_repeated_commands(_menu_items(raw["menus"], "")))
    items.extend(_tool(tool) for tool in raw.get("tools", []))
    items.extend(
        Item("panel", f"panel:{panel['ID']}", panel["name"], f"Window > {panel['name']}", {})
        for panel in raw.get("panels", [])
    )
    for section, values in raw.get("preferences", {}).items():
        if section in PRIVATE_KEYS:
            continue
        items.extend(
            Item(
                "preference",
                f"pref:{section}.{key}",
                key,
                f"Preferences > {section}",
                {"value": value},
            )
            for key, value in values.items()
            if key not in PRIVATE_KEYS
        )
    for set_name, xml_text in raw.get("shortcut_sets", {}).items():
        items.extend(_shortcuts(set_name, xml_text))
    return items


# ExtendScript (ES3) that turns a descriptor into JSON, skipping PRIVATE_KEYS at any depth.
_DESCRIPTOR_JSON = r"""
var PRIVATE=%(private)s;
function qq(s){return '"'+String(s).replace(/\\/g,'\\\\').replace(/"/g,'\\"').replace(/[\x00-\x1f]/g,
 function(c){return "\\u"+("000"+c.charCodeAt(0).toString(16)).slice(-4);})+'"';}
function isPrivate(n){for(var i=0;i<PRIVATE.length;i++)if(PRIVATE[i]==n)return true;return false;}
function keyName(id){return typeIDToStringID(id)||typeIDToCharID(id);}
function value(get,t,depth){
 if(t==DescValueType.STRINGTYPE)return qq(get("String"));
 if(t==DescValueType.INTEGERTYPE)return String(get("Integer"));
 if(t==DescValueType.LARGEINTEGERTYPE)return String(get("LargeInteger"));
 if(t==DescValueType.DOUBLETYPE)return String(get("Double"));
 if(t==DescValueType.BOOLEANTYPE)return String(get("Boolean"));
 if(t==DescValueType.UNITDOUBLE)return String(get("UnitDoubleValue"));
 if(t==DescValueType.ENUMERATEDTYPE)return qq(typeIDToStringID(get("EnumerationValue")));
 if(t==DescValueType.OBJECTTYPE)return depth>64?"null":obj(get("ObjectValue"),depth+1);
 if(t==DescValueType.LISTTYPE)return depth>64?"null":list(get("List"),depth+1);
 return "null";}
function obj(d,depth){var o=[];for(var i=0;i<d.count;i++){var id=d.getKey(i),n=keyName(id);
 if(isPrivate(n))continue;
 o.push(qq(n)+":"+value(function(m){return d["get"+m](id);},d.getType(id),depth));}
 return "{"+o.join(",")+"}";}
function list(l,depth){var o=[];for(var i=0;i<l.count;i++)
 o.push(value(function(m){return l["get"+m](i);},l.getType(i),depth));return "["+o.join(",")+"]";}
function prop(name){var r=new ActionReference();
 r.putProperty(stringIDToTypeID("property"),stringIDToTypeID(name));
 r.putEnumerated(charIDToTypeID("capp"),charIDToTypeID("Ordn"),charIDToTypeID("Trgt"));
 return executeActionGet(r);}
"""
PREFERENCE_SECTIONS = re.compile(r"(Prefs|Preferences|preferences)$")


def read_photoshop(ps: Any, install_dir: Path) -> dict[str, Any]:
    """The app's self-description, as build_inventory's raw input (live adapter)."""
    script = _DESCRIPTOR_JSON % {"private": json.dumps(sorted(PRIVATE_KEYS))}
    names = ps.js(
        script + "var d=executeActionGet(appRef()),out=[];"
        "for(var i=0;i<d.count;i++)out.push(q(keyName(d.getKey(i))));"
        '"["+out.join(",")+"]";'
    )

    def read(name: str) -> Any:
        return ps.js(
            script + f'var d=prop("{name}"),id=stringIDToTypeID("{name}");'
            'value(function(m){return d["get"+m](id);},d.getType(id),0);'
        )

    sections = [n for n in names if PREFERENCE_SECTIONS.search(n) and n not in PRIVATE_KEYS]
    shortcut_dir = install_dir / "Locales" / "en_US" / "Support Files" / "Shortcuts" / "Win"
    return {
        "menus": read("menuBarInfo"),
        "tools": read("tools"),
        "panels": read("panelList"),
        "preferences": {
            section: values
            for section in sections
            if isinstance(values := read(section), dict)  # some *Prefs keys are single values
        },
        "shortcut_sets": {
            path.stem: path.read_text(encoding="utf-8")
            for path in sorted(shortcut_dir.glob("*.kys"))
        },
    }


def _shortcuts(set_name: str, xml_text: str) -> list[Item]:
    root = ElementTree.fromstring(xml_text)
    return [
        Item(
            "shortcut",
            f"shortcut:{keys.text}",
            keys.text,
            f"Keyboard Shortcuts > {command.get('name')}",
            {"keys": keys.text, "command": command.get("name"), "set": set_name},
        )
        for command in root.iter("command")
        for keys in command.iter("shortcut")
        if keys.text
    ]


def _tool(tool: dict[str, Any]) -> Item:
    tip = tool["toolTip"] or tool["toolID"]  # a few tools have no tooltip
    match = _TOOL_SHORTCUT.match(tip)
    name, shortcut = (match["name"], match["key"]) if match else (tip, None)
    facts = {"tool_id": tool["toolID"], "shortcut": shortcut, "in_toolbar": tool["inToolBar"]}
    return Item("tool", f"tool:{tool['toolID']}", name, f"Toolbar > {name}", facts)


def _merge_repeated_commands(items: list[Item]) -> list[Item]:
    """One record per command id; its other menu locations are kept in `also_at`."""
    merged: dict[str, Item] = {}
    for item in items:
        first = merged.get(item.id)
        if first is None:
            merged[item.id] = item
        else:
            first.facts.setdefault("also_at", []).append(item.path)
    return list(merged.values())


def load_inventory(path: Path) -> list[Item]:
    with path.open(encoding="utf-8") as handle:
        return [Item(**json.loads(line)) for line in handle]


def _menu_items(node: dict[str, Any], parent: str) -> list[Item]:
    items: list[Item] = []
    for child in node.get("submenu", []):
        if not child.get("name"):
            continue  # a separator line
        path = f"{parent} > {child['name']}" if parent else child["name"]
        facts = {"command": child.get("command")}
        if child["kind"] == "main":
            items.append(Item("submenu", f"submenu:{path}", child["name"], path, facts))
            items.extend(_menu_items(child, path))
        else:
            items.append(
                Item("menu_command", f"menu:{child['command']}", child["name"], path, facts)
            )
    return items


def main() -> None:
    """python -m scripts.adobe_observed_truth.inventory --out <dir>   (Photoshop must be running)"""
    import argparse
    from collections import Counter
    from dataclasses import asdict

    from .photoshop import Photoshop

    parser = argparse.ArgumentParser(description=main.__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    ps = Photoshop()
    identity = ps.identity()
    items = build_inventory(read_photoshop(ps, Path(identity.executable_path).parent))
    args.out.mkdir(parents=True, exist_ok=True)
    with (args.out / "inventory.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for item in items:
            handle.write(json.dumps(asdict(item), ensure_ascii=False, sort_keys=True) + "\n")
    summary = {
        "app": "Photoshop",
        "version": identity.version,
        "build": identity.build,
        "executable_sha256": identity.executable_sha256,
        "preferences": "factory defaults (settings folder recreated 2026-11-09)",
        "counts": dict(Counter(item.kind for item in items)),
    }
    (args.out / "inventory-summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary["counts"]))


if __name__ == "__main__":
    main()
