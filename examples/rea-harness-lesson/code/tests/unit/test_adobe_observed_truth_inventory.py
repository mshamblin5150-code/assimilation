from __future__ import annotations

from scripts.adobe_observed_truth.inventory import Item, build_inventory

# Shapes as Photoshop 27.11 reported them on 2026-11-09 (menuBarInfo, tools, panelList).
MENU_TREE = {
    "kind": "none",
    "submenu": [
        {
            "kind": "main",
            "name": "Edit",
            "command": 0,
            "submenu": [
                {"kind": "item", "name": "Undo", "command": 101},
                {
                    "kind": "main",
                    "name": "Paste Special",
                    "command": 1298,
                    "submenu": [{"kind": "item", "name": "Paste in Place", "command": 1297}],
                },
            ],
        }
    ],
}


def test_menu_tree_becomes_commands_and_submenus_with_their_menu_paths() -> None:
    items = build_inventory({"menus": MENU_TREE})

    assert items == [
        Item("submenu", "submenu:Edit", "Edit", "Edit", {"command": 0}),
        Item("menu_command", "menu:101", "Undo", "Edit > Undo", {"command": 101}),
        Item(
            "submenu",
            "submenu:Edit > Paste Special",
            "Paste Special",
            "Edit > Paste Special",
            {"command": 1298},
        ),
        Item(
            "menu_command",
            "menu:1297",
            "Paste in Place",
            "Edit > Paste Special > Paste in Place",
            {"command": 1297},
        ),
    ]


def test_separators_are_dropped_and_a_command_in_two_menus_is_one_item_listing_both() -> None:
    tree = {
        "kind": "none",
        "submenu": [
            {
                "kind": "main",
                "name": "Layer",
                "command": 0,
                "submenu": [
                    {"kind": "item", "name": "", "command": 0},
                    {"kind": "item", "name": "Merge Down", "command": 1210},
                ],
            },
            {
                "kind": "main",
                "name": "Layers Panel Menu",
                "command": 0,
                "submenu": [{"kind": "item", "name": "Merge Down", "command": 1210}],
            },
        ],
    }

    commands = [item for item in build_inventory({"menus": tree}) if item.kind == "menu_command"]

    assert commands == [
        Item(
            "menu_command",
            "menu:1210",
            "Merge Down",
            "Layer > Merge Down",
            {"command": 1210, "also_at": ["Layers Panel Menu > Merge Down"]},
        )
    ]


def test_tool_tooltips_give_the_name_and_shortcut_letter() -> None:
    items = build_inventory(
        {
            "tools": [
                {"toolID": "paintbrushTool", "toolTip": "Brush Tool (B)", "inToolBar": True},
                {
                    "toolID": "adjustmentBrushTool",
                    "toolTip": "Adjustment Brush Tool",
                    "inToolBar": True,
                },
            ]
        }
    )

    assert items == [
        Item(
            "tool",
            "tool:paintbrushTool",
            "Brush Tool",
            "Toolbar > Brush Tool",
            {"tool_id": "paintbrushTool", "shortcut": "B", "in_toolbar": True},
        ),
        Item(
            "tool",
            "tool:adjustmentBrushTool",
            "Adjustment Brush Tool",
            "Toolbar > Adjustment Brush Tool",
            {"tool_id": "adjustmentBrushTool", "shortcut": None, "in_toolbar": True},
        ),
    ]


def test_a_tool_with_an_empty_tooltip_is_named_by_its_tool_id() -> None:
    items = build_inventory(
        {"tools": [{"toolID": "targetedAdjustorTool", "toolTip": "", "inToolBar": False}]}
    )

    assert (items[0].name, items[0].path) == (
        "targetedAdjustorTool",
        "Toolbar > targetedAdjustorTool",
    )


def test_panels_are_listed_under_the_window_menu() -> None:
    items = build_inventory({"panels": [{"name": "Actions", "ID": "panelid.static.actions"}]})

    assert items == [
        Item("panel", "panel:panelid.static.actions", "Actions", "Window > Actions", {})
    ]


def test_each_preference_is_a_record_with_its_value() -> None:
    items = build_inventory(
        {"preferences": {"historyPreferences": {"maximumStates": 50, "nonLinear": False}}}
    )

    assert items == [
        Item(
            "preference",
            "pref:historyPreferences.maximumStates",
            "maximumStates",
            "Preferences > historyPreferences",
            {"value": 50},
        ),
        Item(
            "preference",
            "pref:historyPreferences.nonLinear",
            "nonLinear",
            "Preferences > historyPreferences",
            {"value": False},
        ),
    ]


KYS = """<?xml version ="1.0" encoding="UTF-8"?>
<photoshop-keyboard-shortcuts version="4" modified="0" multi-undo="1">
	<command kind="dynamic" name="Vanishing Point">
		<shortcut>Alt+Ctrl+V</shortcut>
	</command>
	<command kind="dynamic" name="Liquify">
		<shortcut>Shift+Ctrl+X</shortcut>
		<shortcut>F9</shortcut>
	</command>
</photoshop-keyboard-shortcuts>
"""


def test_a_shortcut_set_file_gives_one_record_per_key_binding() -> None:
    items = build_inventory({"shortcut_sets": {"Default Keyboard Shortcuts": KYS}})

    assert [(item.id, item.path, item.facts) for item in items] == [
        (
            "shortcut:Alt+Ctrl+V",
            "Keyboard Shortcuts > Vanishing Point",
            {
                "keys": "Alt+Ctrl+V",
                "command": "Vanishing Point",
                "set": "Default Keyboard Shortcuts",
            },
        ),
        (
            "shortcut:Shift+Ctrl+X",
            "Keyboard Shortcuts > Liquify",
            {"keys": "Shift+Ctrl+X", "command": "Liquify", "set": "Default Keyboard Shortcuts"},
        ),
        (
            "shortcut:F9",
            "Keyboard Shortcuts > Liquify",
            {"keys": "F9", "command": "Liquify", "set": "Default Keyboard Shortcuts"},
        ),
    ]


def test_licence_and_private_details_never_reach_the_inventory() -> None:
    items = build_inventory(
        {
            "preferences": {
                "serialString": {"serialString": "1234-5678"},
                "generalPreferences": {"recentFiles": ["C:/private.psd"], "beepWhenDone": False},
            }
        }
    )

    assert [item.id for item in items] == ["pref:generalPreferences.beepWhenDone"]
