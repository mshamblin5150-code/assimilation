"""A command's settings, read from the action descriptor Photoshop reports when it runs.

Built-in commands (Gaussian Blur, Hue/Saturation, Levels...) have no plug-in file describing
them. When one runs, Photoshop tells action listeners its event name and descriptor (batchPlay
JSON): every setting with the value used. Run with a dialog's defaults accepted, that is the
command's settings schema with defaults, and later the means to set each one directly.
"""

from __future__ import annotations

import json
import re
from typing import Any

# Where it ran and how it was called: never a setting of the command.
_HOUSEKEEPING = frozenset({"_obj", "_target", "_isCommand", "_options", "documentID", "layerID"})


# ExtendScript (ES3): an ActionDescriptor as batchPlay-style JSON. References, file aliases
# (private paths) and raw data are left out as null. q() comes from the harness prelude.
# Doubles always carry a decimal point, so a replay puts them back with the same type.
_DESCRIPTOR_JS = r"""
function k2s(id){var s='';try{s=typeIDToStringID(id);}catch(e){}
 if(!s){try{s=typeIDToCharID(id);}catch(e){}}return s;}
function num(n){return isFinite(n)?String(n):'null';}
function dbl(n){var s=num(n);return (s!='null'&&!/[.eE]/.test(s))?s+'.0':s;}
function v2j(d,k,t){
 if(t==DescValueType.UNITDOUBLE)return '{"_unit":'+q(k2s(d.getUnitDoubleType(k)))+',"_value":'+dbl(d.getUnitDoubleValue(k))+'}';
 if(t==DescValueType.ENUMERATEDTYPE)return '{"_enum":'+q(k2s(d.getEnumerationType(k)))+',"_value":'+q(k2s(d.getEnumerationValue(k)))+'}';
 if(t==DescValueType.BOOLEANTYPE)return d.getBoolean(k)?'true':'false';
 if(t==DescValueType.INTEGERTYPE)return String(d.getInteger(k));
 if(t==DescValueType.LARGEINTEGERTYPE)return String(d.getLargeInteger(k));
 if(t==DescValueType.DOUBLETYPE)return dbl(d.getDouble(k));
 if(t==DescValueType.STRINGTYPE)return q(d.getString(k));
 if(t==DescValueType.OBJECTTYPE)return o2j(d.getObjectValue(k),k2s(d.getObjectType(k)));
 if(t==DescValueType.LISTTYPE)return l2j(d.getList(k));
 if(t==DescValueType.CLASSTYPE)return '{"_class":'+q(k2s(d.getClass(k)))+'}';
 return 'null';}
function o2j(d,cls){var p=[];if(cls)p.push('"_obj":'+q(cls));
 for(var i=0;i<d.count;i++){var k=d.getKey(i);p.push(q(k2s(k))+':'+v2j(d,k,d.getType(k)));}
 return '{'+p.join(',')+'}';}
function l2j(l){var p=[];for(var i=0;i<l.count;i++)p.push(v2j(l,i,l.getType(i)));
 return '['+p.join(',')+']';}
"""


def event_script(event: str) -> str:
    """ExtendScript that runs `event` with its dialog shown (the harness accepts it at
    defaults) and returns {"descriptor": the settings used, "error": why not, if it failed}."""
    name = json.dumps(event)
    return _DESCRIPTOR_JS + (
        "var r=null,err='';"
        f"try{{r=executeAction(stringIDToTypeID({name}), undefined, DialogModes.ALL);}}"
        "catch(e){err=String(e);}"
        f"'{{\"descriptor\":'+(r?o2j(r,{name}):'null')+',\"error\":'+q(err)+'}}';"
    )


def event_for(menu_path: str, names: set[str]) -> str | None:
    """The scripting event a menu item runs, when its name is the item's name in camel case
    ("Hue/Saturation..." -> hueSaturation); None rather than a guess otherwise."""
    words = re.findall(r"[A-Za-z0-9]+", menu_path.rsplit(" > ", 1)[-1])
    if not words:
        return None
    candidate = words[0].lower() + "".join(w[:1].upper() + w[1:] for w in words[1:])
    return candidate if candidate in names else None


def settings_of(descriptor: dict[str, Any], prefix: str = "") -> list[dict[str, Any]]:
    """Every setting in a descriptor, nested ones named by path (adjustment[0].hue)."""
    found: list[dict[str, Any]] = []
    for key, value in descriptor.items():
        if key in _HOUSEKEEPING:
            continue
        found += _setting(f"{prefix}{key}", value)
    return found


def _setting(key: str, value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict) and "_unit" in value:
        return [{"key": key, "type": "unit", "unit": value["_unit"], "default": value.get("_value")}]
    if isinstance(value, dict) and "_enum" in value:
        return [{"key": key, "type": "choice", "choices": value["_enum"], "default": value.get("_value")}]
    if isinstance(value, dict):
        return settings_of(value, f"{key}.")
    if isinstance(value, list):
        return [s for index, item in enumerate(value) for s in _setting(f"{key}[{index}]", item)]
    kinds = {bool: "boolean", int: "integer", float: "double", str: "string"}
    return [{"key": key, "type": kinds.get(type(value), type(value).__name__), "default": value}]
