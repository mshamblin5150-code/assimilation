"""Photoshop's panel flyout menus, read by command number and their own commands run.

Each panel group's flyout button (the bars at the right end of its tab strip) opens a native
popup menu (#32768); MN_GETHMENU gives its menu, and every item a Photoshop command number,
the same numbers the main menus use (the text is drawn by Photoshop, so it reads back empty).
A discovery spec per panel shows that panel and reads the flyout of every visible panel group;
new_flyout_commands() keeps the numbers no main-menu item has, and flyout_specs() runs each by
number on the test chart like a menu command, so the sampled sweep maps its code. Probed live
on 2026-11-23: Layers' flyout has 41 commands, 30 also in the main menus, 11 only there.
"""

from __future__ import annotations

import ctypes
import json
import time
from collections.abc import Callable, Iterable
from typing import Any

from .families import ScenarioSpec

Rect = tuple[int, int, int, int]
_BUTTON_FROM_RIGHT, _BUTTON_FROM_TOP = 10.4, 14.4  # at 100%, measured at 125% (13 and 18 pixels)


def flyout_button(group: Rect, scale: float) -> tuple[int, int]:
    """Where a panel group's flyout button is, from the group's window (physical pixels)."""
    _, top, right, _ = group
    return right - round(_BUTTON_FROM_RIGHT * scale), top + round(_BUTTON_FROM_TOP * scale)


MenuItem = tuple[int, bool, Any]  # (command number, 0 separator / -1 submenu; greyed; submenu handle)


def menu_entries(handle: Any, read: Callable[[Any], list[MenuItem]], at: tuple[int, ...] = ()) -> list[dict[str, Any]]:
    """Every command of a menu and its submenus, by position, separators left out."""
    entries = []
    for position, (command, greyed, submenu) in enumerate(read(handle)):
        if submenu is not None:
            entries += menu_entries(submenu, read, (*at, position))
        elif command > 0:
            entries.append({"command": command, "enabled": not greyed, "position": [*at, position]})
    return entries


def new_flyout_commands(results: Iterable[str], known: set[int]) -> list[dict[str, Any]]:
    """Command numbers seen in flyouts (discovery results) that no main-menu item has, with the
    panels shown when each was seen."""
    seen: dict[int, set[str]] = {}
    for line in results:
        if not line.strip():
            continue
        row = json.loads(line)
        if not row["item_id"].endswith("@flyout"):
            continue
        panel = row["item_id"].removeprefix("panel:").removesuffix("@flyout")
        for group in (row.get("observations") or {}).get("flyouts") or []:
            for entry in group["entries"]:
                seen.setdefault(entry["command"], set()).add(panel)
    return [{"command": c, "panels": sorted(p)} for c, p in sorted(seen.items()) if c not in known]


def flyout_specs(commands: list[dict[str, Any]]) -> list[ScenarioSpec]:
    """Each flyout-only command run by its number on the chart, its dialogs cancelled and
    any document it made closed."""
    return [
        ScenarioSpec(f"flyout:{c['command']}", "flyout_command", "run", False, (
            ("open_test_image", "chart"),
            ("snapshot_documents",),
            ("run_menu_command", c["command"]),
            ("record", "dialogs", "history", "document"),
            ("cancel_dialogs",),
            ("close_new_documents",),
            ("close_throwaway_document",),
        ))
        for c in commands
    ]


def discovery_specs(panel_ids: Iterable[str]) -> list[ScenarioSpec]:
    """Per panel: show it (on the chart, so items are enabled where they can be), read every
    visible group's flyout, then hide what was shown."""
    return [
        ScenarioSpec(f"panel:{p}@flyout", "flyout_discovery", "run", True, (
            ("open_test_image", "chart"),
            ("snapshot_panels",),
            ("show_panel", p),
            ("read_flyouts",),
            ("record", "flyouts", "panels"),
            ("restore_panels",),
            ("close_throwaway_document",),
        ))
        for p in panel_ids
    ]


# --- live: Windows only --------------------------------------------------------------------

_MN_GETHMENU, _MF_BYPOSITION = 0x01E1, 0x400


def _native_menu_items(menu: int) -> list[MenuItem]:
    user32 = ctypes.windll.user32
    user32.GetSubMenu.restype = ctypes.c_void_p
    items = []
    for i in range(user32.GetMenuItemCount(ctypes.c_void_p(menu))):
        submenu = user32.GetSubMenu(ctypes.c_void_p(menu), i)
        command = user32.GetMenuItemID(ctypes.c_void_p(menu), i)
        greyed = bool(user32.GetMenuState(ctypes.c_void_p(menu), i, _MF_BYPOSITION) & 0x3)
        items.append((-1 if submenu else ctypes.c_int(command).value, greyed, submenu))
    return items


def read_flyouts(pid: int, hwnd: int, click: Callable[[tuple[int, int]], None],
                 escape: Callable[[], None]) -> list[dict[str, Any]]:
    """Open each visible panel group's flyout in Photoshop's window `hwnd`, read its commands,
    close it. `click` and `escape` send input to Photoshop (the runner's guarded input)."""
    user32 = ctypes.windll.user32
    proc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    scale = user32.GetDpiForWindow(ctypes.c_void_p(hwnd)) / 96

    def windows(parent: int | None, cls: str) -> list[int]:
        found: list[int] = []
        name = ctypes.create_unicode_buffer(64)

        def each(h, _):
            user32.GetClassNameW(ctypes.c_void_p(h), name, 64)
            owner = ctypes.c_ulong()
            user32.GetWindowThreadProcessId(ctypes.c_void_p(h), ctypes.byref(owner))
            if name.value == cls and owner.value == pid and user32.IsWindowVisible(ctypes.c_void_p(h)):
                found.append(h)
            return True
        if parent is None:
            user32.EnumWindows(proc(each), 0)
        else:
            user32.EnumChildWindows(ctypes.c_void_p(parent), proc(each), 0)
        return found

    flyouts = []
    for group in windows(hwnd, "OWL.TabGroup"):
        rect = (ctypes.c_long * 4)()
        user32.GetWindowRect(ctypes.c_void_p(group), rect)
        before = set(windows(None, "#32768"))
        click(flyout_button(tuple(rect), scale))
        opened: list[int] = []
        for _ in range(20):
            if opened := [m for m in windows(None, "#32768") if m not in before]:
                break
            time.sleep(0.1)
        entries = []
        if opened:
            menu = user32.SendMessageW(ctypes.c_void_p(opened[0]), _MN_GETHMENU, 0, 0)
            entries = menu_entries(menu, _native_menu_items)
            escape()
        flyouts.append({"group": list(rect), "entries": entries})
    return flyouts


def main() -> None:
    """python -m scripts.adobe_observed_truth.panel_flyouts --dataset <dir> discover
    python -m scripts.adobe_observed_truth.panel_flyouts --dataset <dir> commands --results <sweep>/results.jsonl

    discover writes flyout-discovery.jsonl (a spec per panel that may run); commands writes
    flyout-families.jsonl from those specs' results: each flyout-only command run on the chart.
    Run either with runner_photoshop --specs <file>."""
    import argparse
    from dataclasses import asdict
    from pathlib import Path

    from .families import scenarios_for
    from .inventory import load_inventory

    parser = argparse.ArgumentParser(description=main.__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("mode", choices=("discover", "commands"))
    parser.add_argument("--results", type=Path)
    args = parser.parse_args()
    items = load_inventory(args.dataset / "inventory.jsonl")
    if args.mode == "discover":
        panels = [i.id.removeprefix("panel:") for i in items if i.kind == "panel" and scenarios_for(i).safety == "run"]
        specs, name = discovery_specs(panels), "flyout-discovery.jsonl"
    else:
        known = {i.facts["command"] for i in items if i.kind == "menu_command"}
        commands = new_flyout_commands(args.results.read_text(encoding="utf-8").splitlines(), known)
        specs, name = flyout_specs(commands), "flyout-families.jsonl"
    with (args.dataset / name).open("w", encoding="utf-8", newline="\n") as out:
        out.writelines(json.dumps(asdict(s), sort_keys=True) + "\n" for s in specs)
    print(f"{len(specs)} specs in {name}")


if __name__ == "__main__":
    main()
