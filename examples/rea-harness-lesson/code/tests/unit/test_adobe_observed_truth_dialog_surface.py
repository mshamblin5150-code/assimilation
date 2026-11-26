"""Answering a Windows file dialog: which box the File name goes into."""

from __future__ import annotations

from scripts.adobe_observed_truth.dialog_surface import EditBox, pick_file_name_box


def test_a_save_dialogs_file_name_box_is_found_inside_its_combo_box() -> None:
    # Photoshop's Save As, 2026-11-24: the File name Edit (1001) sits in a combo box below the
    # dialog's own children, so a lookup of the dialog's children found nothing and every save
    # was cancelled. A hidden box beside it is never the one typed into.
    edits = [EditBox(hwnd=97980634, control_id=1001, parent_id=0, visible=True),
             EditBox(hwnd=98440846, control_id=41477, parent_id=41477, visible=False)]

    assert pick_file_name_box(edits) == 97980634


def test_an_open_dialogs_file_name_box_is_the_edit_inside_its_file_name_combo() -> None:
    edits = [EditBox(hwnd=5, control_id=1001, parent_id=1148, visible=True)]

    assert pick_file_name_box(edits) == 5


def test_a_dialog_with_no_visible_file_name_box_has_none() -> None:
    edits = [EditBox(hwnd=7, control_id=1001, parent_id=0, visible=False),
             EditBox(hwnd=8, control_id=1152, parent_id=0, visible=True)]

    assert pick_file_name_box(edits) == 0
