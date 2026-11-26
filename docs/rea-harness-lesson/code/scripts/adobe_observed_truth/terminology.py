"""Photoshop's scripting dictionary, read out of the running app (read-only lookups).

Built-in names (events, settings, choices) have a four-letter code as their numeric id:
charIDToTypeID("GsnB") -> typeIDToStringID -> "gaussianBlur". Names added at runtime have small
sequential ids and no code. typeIDToStringID returns "" for an unregistered id, so every code
in the code space and every small id can simply be tried; about 100,000 lookups a second.
The dictionary is what the helper subscribes to (Photoshop refuses a listener for "all").

    python -m scripts.adobe_observed_truth.terminology --dataset <dir>
"""

from __future__ import annotations

import itertools
import json
from pathlib import Path
from typing import Any

# Characters seen in Photoshop's four-letter codes ("Rds ", "Zm  ", "#Pxl", "HStr").
CODE_ALPHABET = (
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 #"
)


def prefixes(alphabet: str = CODE_ALPHABET) -> list[str]:
    """Every two-character prefix: one lookup call each covers the codes that start with it."""
    return ["".join(pair) for pair in itertools.product(alphabet, repeat=2)]


def dictionary(built_in: dict[str, str], runtime: dict[int, str]) -> list[dict[str, Any]]:
    """One entry per name, sorted; a name known both ways is listed under its code."""
    entries: dict[str, dict[str, Any]] = {
        name: {"name": name, "code": None, "id": type_id} for type_id, name in runtime.items()
    }
    for code, name in built_in.items():
        entries[name] = {"name": name, "code": code, "id": int(code.encode("latin-1").hex(), 16)}
    return [entries[name] for name in sorted(entries)]


def _lookup_script(prefix: str, alphabet: str) -> str:
    return (
        f"var a={json.dumps(alphabet)},p={json.dumps(prefix)},out=[];"
        "for(var i=0;i<a.length;i++)for(var j=0;j<a.length;j++){"
        "var c=p+a.charAt(i)+a.charAt(j),s='';"
        "try{s=typeIDToStringID(charIDToTypeID(c));}catch(e){}"
        'if(s)out.push(q(c)+":"+q(s));}"{"+out.join(",")+"}";'
    )


def read_dictionary(ps: Any, runtime_ids: int = 40000) -> list[dict[str, Any]]:
    """Every built-in code and every runtime name the running Photoshop knows."""
    built_in: dict[str, str] = {}
    for prefix in prefixes():
        built_in.update(ps.js(_lookup_script(prefix, CODE_ALPHABET)))
    runtime_list = ps.js(
        f"var out=[];for(var i=0;i<{runtime_ids};i++){{var s='';"
        "try{s=typeIDToStringID(i);}catch(e){}"
        'if(s)out.push(q(i+":"+s));}"["+out.join(",")+"]";'
    )
    runtime = {int(entry.split(":", 1)[0]): entry.split(":", 1)[1] for entry in runtime_list}
    return dictionary(built_in, runtime)


def main() -> None:
    import argparse

    from .photoshop import Photoshop

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    args = parser.parse_args()
    entries = read_dictionary(Photoshop())
    with (args.dataset / "terminology.jsonl").open("w", encoding="utf-8", newline="\n") as out:
        for entry in entries:
            out.write(json.dumps(entry, sort_keys=True) + "\n")
    print(json.dumps({"names": len(entries), "with_code": sum(e["code"] is not None for e in entries)}))


if __name__ == "__main__":
    main()
