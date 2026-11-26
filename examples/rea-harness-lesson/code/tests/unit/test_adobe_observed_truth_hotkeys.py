"""A shortcut another program owns system-wide must never be pressed: that program acts instead.

Seen live 2026-11-09: Alt+F9 (Photoshop: Actions panel) made the NVIDIA app offer to record the
desktop; Ctrl+Alt+G opened Google Drive's search. Windows refuses RegisterHotKey for a key
combination another program holds, so trying (and releasing at once) tells which are taken.
"""

from __future__ import annotations

from scripts.adobe_observed_truth.win_input import hotkey, owned_elsewhere


def test_a_shortcut_becomes_windows_modifier_flags_and_a_virtual_key() -> None:
    assert hotkey("alt+f9") == (0x1, 0x78)


def test_modifiers_combine_in_any_written_order() -> None:
    assert hotkey("shift+ctrl+z") == (0x6, 0x5A)


def test_ctrl_plus_is_ctrl_with_the_plus_key() -> None:
    assert hotkey("ctrl++") == (0x2, 0xBB)


def test_a_combination_windows_will_not_register_is_owned_by_another_program() -> None:
    assert owned_elsewhere("alt+f9", register=lambda modifiers, key: False)


def test_a_combination_windows_registers_is_free() -> None:
    assert not owned_elsewhere("ctrl+5", register=lambda modifiers, key: True)


def test_f12_alone_is_never_counted_as_owned_since_windows_reserves_it_for_debuggers() -> None:
    # RegisterHotKey always refuses bare F12, yet pressing it reached Photoshop (Revert, 2026-11-09).
    assert not owned_elsewhere("f12", register=lambda modifiers, key: False)