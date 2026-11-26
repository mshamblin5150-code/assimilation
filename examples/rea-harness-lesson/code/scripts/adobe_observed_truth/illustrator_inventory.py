"""Illustrator 2026's inventory, read from its installed shortcut set (no running app needed).

"Illustrator Defaults.kys" names every menu command (the names executeMenuCommand takes) and
every tool by its internal name, with its key. Those names are also the string literals the
code links search the decompiled binaries for. Display names are not in the file; panels open
through Window menu commands, so they appear as menu commands.
"""

from __future__ import annotations

import re
from pathlib import Path

from .inventory import Item

ILLUSTRATOR_2026 = Path(r"C:\Program Files\Adobe\Adobe Illustrator 2026")
SHORTCUT_DIR = Path("Presets") / "en_US" / "Keyboard Shortcuts"

_SECTION = re.compile(r"^/(Menus|Tools) \{$")
_ENTRY = re.compile(r"^\t/(?P<name>(?:\\.|[^{])+?) \{$")
_FIELD = re.compile(r"^\t\t/(?P<key>\w+) (?P<value>-?\d+)$")
_MODIFIERS = ((128, "Alt"), (32, "Shift"), (64, "Ctrl"))  # Windows order: Alt+Shift+Ctrl+key


def build_inventory(shortcut_sets: dict[str, str]) -> list[Item]:
    """Items from each shortcut set's text, by set name: commands and tools, then their keys."""
    items: list[Item] = []
    shortcuts: list[Item] = []
    for set_name, text in shortcut_sets.items():
        for section, name, fields in _entries(text):
            if section == "Menus":
                items.append(Item("menu_command", f"menu:{name}", name, f"Menu command {name}", {"command_name": name}))
            elif name.endswith(" Tool"):
                facts = {"tool_id": name, "shortcut": _keys(fields)}
                items.append(Item("tool", f"tool:{name}", name, f"Toolbar > {name}", facts))
            else:
                items.append(
                    Item("tool_command", f"tool_command:{name}", name, f"Tool command {name}", {"command_name": name})
                )
            if keys := _keys(fields):
                facts = {"keys": keys, "command": name, "set": set_name}
                shortcuts.append(Item("shortcut", f"shortcut:{name}", keys, f"Keyboard Shortcuts > {name}", facts))
    return items + shortcuts


def read_illustrator(install_dir: Path = ILLUSTRATOR_2026) -> dict[str, str]:
    """The installed shortcut sets, by name: build_inventory's input."""
    return {path.stem: path.read_text(encoding="utf-8") for path in sorted((install_dir / SHORTCUT_DIR).glob("*.kys"))}


def _entries(text: str):
    section = None
    name = None
    fields: dict[str, int] = {}
    for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if match := _SECTION.match(line):
            section = match[1]
        elif section and (match := _ENTRY.match(line)):
            name, fields = re.sub(r"\\(.)", r"\1", match["name"]), {}
        elif name and (match := _FIELD.match(line)):
            fields[match["key"]] = int(match["value"])
        elif name and line == "\t}":
            yield section, name, fields
            name = None


def _keys(fields: dict[str, int]) -> str | None:
    modifiers, key = fields.get("Modifiers", 0), fields.get("Key", 0)
    if not modifiers and not key:
        return None
    parts = [label for bit, label in _MODIFIERS if modifiers & bit]
    parts.append(_SPECIAL_KEYS.get(key) or (chr(key) if key >= 32 else f"special key {key}"))
    return "+".join(parts)


# Below 32 the file uses its own codes: verified against the documented defaults
# (Ctrl+F9 Gradient, Ctrl+F6 next document, F2-F4 cut/copy/paste).
_SPECIAL_KEYS = {9: "Tab", **{14 + n: f"F{n + 1}" for n in range(12)}}


def main() -> None:
    """python -m scripts.adobe_observed_truth.illustrator_inventory --out <dir>"""
    import argparse
    import hashlib
    import json
    from collections import Counter
    from dataclasses import asdict

    parser = argparse.ArgumentParser(description=main.__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--install", type=Path, default=ILLUSTRATOR_2026)
    args = parser.parse_args()
    items = build_inventory(read_illustrator(args.install))
    args.out.mkdir(parents=True, exist_ok=True)
    with (args.out / "inventory.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for item in items:
            handle.write(json.dumps(asdict(item), ensure_ascii=False, sort_keys=True) + "\n")
    executable = args.install / "Support Files" / "Contents" / "Windows" / "Illustrator.exe"
    summary = {
        "app": "Illustrator",
        "executable_sha256": hashlib.sha256(executable.read_bytes()).hexdigest(),
        "source": "installed shortcut sets (Presets/en_US/Keyboard Shortcuts)",
        "counts": dict(Counter(item.kind for item in items)),
    }
    (args.out / "inventory-summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary["counts"]))


if __name__ == "__main__":
    main()
