"""The controls seen in Photoshop's dialogs, one line per captured dialog, by control type.

Built from a reading of every distinct captured dialog (228 on 2026-11-09). Control types are
normalised so one thing has one name; window chrome from captures that were not dialogs is
left out (the main window's menus and tools are probed separately). The test suite requires a
driver (or, for passive types, a reader) for every type this catalogue contains.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

# One name per thing (readers named the same control differently).
ALIASES = {
    "other:accordion_section": "collapsible_section",
    "other:collapsible_section": "collapsible_section",
    "other:disclosure_section": "collapsible_section",
    "other:resize_grip": "resize_grip",
    "other:scrollbar_thumb": "scrollbar_thumb",
    "other:eyedropper_tool": "eyedropper",
    "other:eyedropper_set_black": "eyedropper",
    "other:eyedropper_set_gray": "eyedropper",
    "other:eyedropper_set_white": "eyedropper",
    "other:on_image_adjust_tool": "on_image_adjust_tool",
    "other:on_image_hand_tool": "on_image_adjust_tool",
    "other:curve_tool_mode": "mode_toggle",
    "other:curve_edit_tool": "mode_toggle",
    "other:curve_draw_tool": "mode_toggle",
    "other:grid_size_toggle": "mode_toggle",
    "other:layout_orientation_toggle": "mode_toggle",
    "other:view_toggle": "mode_toggle",
    "other:preview_pane_toggle": "mode_toggle",
    "other:panel_visibility_toggle": "mode_toggle",
    "other:zoom_tool": "tool_palette",
    "other:hand_tool": "tool_palette",
    "other:star_rating": "star_rating",
    "other:breadcrumb_address_bar": "address_bar",
    "other:column_headers": "column_headers",
    "other:gradient_ramp_strip": "static_image",
    "other:xmp_logo": "static_image",
    "other:sync_icon": "static_image",
    "other:warning_icon": "static_image",
    "other:error_icon": "static_image",
    "other:banner_image": "static_image",
    "other:unlabeled_focused_control": "unknown",
}
# Window chrome of the main Photoshop window, in captures that were not dialogs.
NOT_DIALOG = frozenset(
    {"other:menu_bar", "other:tool_options_bar", "other:document_tab", "other:window_chrome_toolbar"}
)
# Shown, not operated: read (OCR / pixels), never driven.
PASSIVE = frozenset({"static_text", "group_box", "progress_bar", "static_image", "help_link"})


def normalise(kind: str) -> str | None:
    if kind in NOT_DIALOG:
        return None
    return ALIASES.get(kind, kind)


def build(parts: list[Path]) -> list[dict[str, Any]]:
    rows = []
    for part in parts:
        for line in part.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            controls = []
            for control in row.get("controls", []):
                kind = normalise(control["type"])
                if kind is not None:
                    controls.append({**control, "type": kind})
            rows.append({**row, "controls": controls})
    return sorted(rows, key=lambda r: (str(r.get("command")), str(r.get("image"))))


def load(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def types_seen(rows: list[dict[str, Any]]) -> Counter[str]:
    return Counter(c["type"] for row in rows for c in row["controls"])


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Merge dialog control readings into the dataset.")
    parser.add_argument("parts", nargs="+", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    rows = build(args.parts)
    with args.out.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    print(json.dumps({"dialogs": len(rows), "types": dict(types_seen(rows).most_common())}))


if __name__ == "__main__":
    main()
