"""Panel flyout menus: native popup menus whose items carry Photoshop command numbers (Layers,
2026-11-23: 41 commands, 30 also in the main menus, 11 only there, two submenus)."""

from __future__ import annotations

import json

from scripts.adobe_observed_truth.panel_flyouts import (
    flyout_button,
    flyout_specs,
    menu_entries,
    new_flyout_commands,
)


def test_the_flyout_button_is_at_the_right_end_of_a_panel_groups_tab_strip() -> None:
    # Layers, Channels, Paths at 125% scaling: group 1734..2168 x 1093..1381, button at 2155, 1111.
    assert flyout_button((1734, 1093, 2168, 1381), scale=1.25) == (2155, 1111)
    assert flyout_button((1000, 100, 1400, 900), scale=1.0) == (1390, 114)


def test_a_menu_is_read_with_its_submenus_separators_left_out() -> None:
    menus = {
        "top": [(2941, True, None), (0, True, None), (1099, False, None), (-1, False, "options")],
        "options": [(7962, False, None), (7963, True, None)],
    }

    entries = menu_entries("top", lambda handle: menus[handle])

    assert entries == [
        {"command": 2941, "enabled": False, "position": [0]},
        {"command": 1099, "enabled": True, "position": [2]},
        {"command": 7962, "enabled": True, "position": [3, 0]},
        {"command": 7963, "enabled": False, "position": [3, 1]},
    ]


def _row(panel: str, commands: list[int]) -> str:
    flyouts = [{"group": [0, 0, 1, 1], "entries": [{"command": c, "enabled": True, "position": [i]}
                                                   for i, c in enumerate(commands)]}]
    return json.dumps({"item_id": f"panel:{panel}@flyout", "status": "ok", "observations": {"flyouts": flyouts}})


def test_commands_only_in_flyouts_are_new_each_with_the_panels_it_was_seen_in() -> None:
    rows = [_row("layers", [1099, 2941, 9256]), _row("channels", [2941, 1083])]

    found = new_flyout_commands(rows, known={1099})

    assert found == [
        {"command": 1083, "panels": ["channels"]},
        {"command": 2941, "panels": ["channels", "layers"]},
        {"command": 9256, "panels": ["layers"]},
    ]


def test_each_new_flyout_command_runs_by_its_number_on_the_chart() -> None:
    (spec,) = flyout_specs([{"command": 2941, "panels": ["layers"]}])

    assert (spec.item_id, spec.family, spec.safety) == ("flyout:2941", "flyout_command", "run")
    # A document the command makes is closed: two left open blocked the next run (2026-11-24).
    assert spec.steps == (
        ("open_test_image", "chart"),
        ("snapshot_documents",),
        ("run_menu_command", 2941),
        ("record", "dialogs", "history", "document"),
        ("cancel_dialogs",),
        ("close_new_documents",),
        ("close_throwaway_document",),
    )
