from __future__ import annotations

from scripts.adobe_observed_truth.code_links import anchors_for
from scripts.adobe_observed_truth.illustrator_inventory import build_inventory
from scripts.adobe_observed_truth.inventory import Item

# The shape of Illustrator 2026's installed "Illustrator Defaults.kys" (2026-11-16): two
# sections keyed by internal name. Modifiers are bits (32 Shift, 64 Ctrl, 128 Alt); Key is the
# character code, except 9 Tab and 14-25 F1-F12; all zeros means no shortcut. Verified against
# the documented defaults: Ctrl+F9 Gradient, Ctrl+F6 next document, F2-F4 cut/copy/paste.
KYS = """/Menus {
\t/closeAll {
\t\t/Context 0
\t\t/Modifiers 192
\t\t/Represent 87
\t\t/Key 87
\t}
\t/Adobe\\ New\\ Swatch\\ Shortcut\\ Menu {
\t\t/Context 0
\t\t/Modifiers 0
\t\t/Represent 0
\t\t/Key 0
\t}
\t/navigateToPreviousDocument {
\t\t/Context 0
\t\t/Modifiers 96
\t\t/Represent 19
\t\t/Key 19
\t}
}
/Tools {
\t/Adobe\\ Eraser\\ Tool {
\t\t/Context 0
\t\t/Modifiers 32
\t\t/Represent 69
\t\t/Key 69
\t}
\t/Adobe\\ Opacity\\ 40 {
\t\t/Context 0
\t\t/Modifiers 0
\t\t/Represent 52
\t\t/Key 52
\t}
\t/Adobe\\ Hide\\ Palettes {
\t\t/Context 0
\t\t/Modifiers 32
\t\t/Represent 9
\t\t/Key 9
\t}
}
"""

SET = "Illustrator Defaults"


def test_menu_commands_tools_and_their_keys_become_inventory_items() -> None:
    items = build_inventory({SET: KYS})

    assert items == [
        Item("menu_command", "menu:closeAll", "closeAll", "Menu command closeAll", {"command_name": "closeAll"}),
        Item(
            "menu_command",
            "menu:Adobe New Swatch Shortcut Menu",
            "Adobe New Swatch Shortcut Menu",
            "Menu command Adobe New Swatch Shortcut Menu",
            {"command_name": "Adobe New Swatch Shortcut Menu"},
        ),
        Item(
            "menu_command",
            "menu:navigateToPreviousDocument",
            "navigateToPreviousDocument",
            "Menu command navigateToPreviousDocument",
            {"command_name": "navigateToPreviousDocument"},
        ),
        Item(
            "tool",
            "tool:Adobe Eraser Tool",
            "Adobe Eraser Tool",
            "Toolbar > Adobe Eraser Tool",
            {"tool_id": "Adobe Eraser Tool", "shortcut": "Shift+E"},
        ),
        Item(
            "tool_command",
            "tool_command:Adobe Opacity 40",
            "Adobe Opacity 40",
            "Tool command Adobe Opacity 40",
            {"command_name": "Adobe Opacity 40"},
        ),
        Item(
            "tool_command",
            "tool_command:Adobe Hide Palettes",
            "Adobe Hide Palettes",
            "Tool command Adobe Hide Palettes",
            {"command_name": "Adobe Hide Palettes"},
        ),
        Item(
            "shortcut",
            "shortcut:closeAll",
            "Alt+Ctrl+W",
            "Keyboard Shortcuts > closeAll",
            {"keys": "Alt+Ctrl+W", "command": "closeAll", "set": SET},
        ),
        Item(
            "shortcut",
            "shortcut:navigateToPreviousDocument",
            "Shift+Ctrl+F6",
            "Keyboard Shortcuts > navigateToPreviousDocument",
            {"keys": "Shift+Ctrl+F6", "command": "navigateToPreviousDocument", "set": SET},
        ),
        Item(
            "shortcut",
            "shortcut:Adobe Eraser Tool",
            "Shift+E",
            "Keyboard Shortcuts > Adobe Eraser Tool",
            {"keys": "Shift+E", "command": "Adobe Eraser Tool", "set": SET},
        ),
        Item(
            "shortcut",
            "shortcut:Adobe Opacity 40",
            "4",
            "Keyboard Shortcuts > Adobe Opacity 40",
            {"keys": "4", "command": "Adobe Opacity 40", "set": SET},
        ),
        Item(
            "shortcut",
            "shortcut:Adobe Hide Palettes",
            "Shift+Tab",
            "Keyboard Shortcuts > Adobe Hide Palettes",
            {"keys": "Shift+Tab", "command": "Adobe Hide Palettes", "set": SET},
        ),
    ]


def test_illustrator_command_names_are_code_anchors_when_distinctive() -> None:
    def command(name: str) -> Item:
        return Item("menu_command", f"menu:{name}", name, "", {"command_name": name})

    assert anchors_for(command("closeAll")) == ["closeAll"]
    assert anchors_for(command("new2")) == []  # too short to be distinctive
    photoshop_menu = Item("menu_command", "menu:101", "Undo", "Edit > Undo", {"command": 101})
    assert anchors_for(photoshop_menu) == []
