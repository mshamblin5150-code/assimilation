from __future__ import annotations

from typing import Any

from scripts.adobe_observed_truth.claim_map import Disposition, map_claims
from scripts.adobe_observed_truth.inventory import Item

INVENTORY = [
    Item("tool", "tool:moveTool", "Move Tool", "Toolbar > Move Tool", {"shortcut": "V"}),
    Item("panel", "panel:panelid.static.layers", "Layers", "Window > Layers", {}),
    Item("menu_command", "menu:1960", "Timeline", "Window > Timeline", {"command": 1960}),
    Item("menu_command", "menu:2207", "Free Transform", "Edit > Free Transform", {}),
]


def claim(
    claim_id: str, text: str, url: str = "/photoshop/desktop/x.html", **features: Any
) -> dict:
    return {"claim_id": claim_id, "text": text, "url": url, "features": features}


def test_a_claim_naming_a_tool_is_matched_to_that_tool() -> None:
    claims = [
        claim(
            "c1",
            "Drag with the Move tool to reposition the layer.",
            named=[{"kind": "tool", "name": "Move", "text": "Move tool"}],
            behaviour_verbs=["drag"],
        )
    ]

    assert map_claims(claims, INVENTORY) == [Disposition("c1", "matched", ("tool:moveTool",))]


def test_panels_and_menu_paths_are_matched_and_a_claim_naming_nothing_known_is_unmatched() -> None:
    claims = [
        claim(
            "c2",
            "In the Layers panel, choose Window > Timeline.",
            named=[{"kind": "panel", "name": "Layers", "text": "Layers panel"}],
            menu_paths=["Window > Timeline"],
        ),
        claim("c3", "Choose Edit > Free Transform…", menu_paths=["Edit > Free Transform…"]),
        claim(
            "c4",
            "Drag the Puppet pins to bend the image.",
            named=[{"kind": "tool", "name": "Puppet", "text": "Puppet pins"}],
            behaviour_verbs=["drag"],
        ),
    ]

    assert map_claims(claims, INVENTORY) == [
        Disposition("c2", "matched", ("panel:panelid.static.layers", "menu:1960")),
        Disposition("c3", "matched", ("menu:2207",)),
        Disposition("c4", "unmatched"),
    ]


def test_claims_that_cannot_be_tested_here_say_why() -> None:
    move = [{"kind": "tool", "name": "Move", "text": "Move tool"}]
    claims = [
        claim("r1", "Faster startup.", url="/photoshop/desktop/whats-new/release-notes.html"),
        claim(
            "r2", "8 GB of RAM.", url="/photoshop/desktop/get-started/technical-requirements.html"
        ),
        claim("r3", "Generative Fill creates content from a prompt.", named=move),
        claim("r4", "Press Command+Option and drag (macOS).", named=move),
    ]

    assert [(d.claim_id, d.status, d.reason) for d in map_claims(claims, INVENTORY)] == [
        ("r1", "not_behaviour", "release notes"),
        ("r2", "not_behaviour", "system requirements"),
        ("r3", "untestable_here", "cloud or generative AI service"),
        ("r4", "untestable_here", "macOS only"),
    ]


def test_a_sentence_naming_nothing_takes_its_subject_from_its_section_marked_as_weaker() -> None:
    claims = [
        claim("x1", "Drag to reposition it.", context={"named": ["Move tool"]}),
        claim("x2", "Click the eye icon.", context={"named": ["Layers panel"]}),
        claim(
            "x3",
            "Drag with the Move tool.",
            named=[{"kind": "tool", "name": "Move", "text": "Move tool"}],
            context={"named": ["Layers panel"]},
        ),
    ]

    assert map_claims(claims, INVENTORY) == [
        Disposition("x1", "matched_by_context", ("tool:moveTool",)),
        Disposition("x2", "matched_by_context", ("panel:panelid.static.layers",)),
        Disposition("x3", "matched", ("tool:moveTool",)),
    ]


def test_ordinary_words_command_and_option_do_not_make_a_claim_macos_only() -> None:
    move = [{"kind": "tool", "name": "Move", "text": "Move tool"}]
    claims = [claim("o1", "Set the Auto-Select option, then run the command again.", named=move)]

    assert map_claims(claims, INVENTORY)[0].status == "matched"


def test_claims_that_also_work_on_windows_are_not_called_macos_only() -> None:
    move = [{"kind": "tool", "name": "Move", "text": "Move tool"}]
    claims = [
        claim("m1", "Press Enter (or Return on macOS) to commit.", named=move),
        claim("m2", "Press Control+T (Win) / Command+T (Mac) to transform.", named=move),
        claim("m3", "Choose Photoshop > Settings > File Handling on macOS.", named=move),
    ]

    assert [d.status for d in map_claims(claims, INVENTORY)] == ["matched"] * 3


def test_a_short_tool_name_matches_every_tool_it_is_the_family_name_of() -> None:
    tools = [
        Item("tool", "tool:typeCreateOrEditTool", "Horizontal Type Tool", "Toolbar > x", {}),
        Item("tool", "tool:typeVerticalCreateOrEditTool", "Vertical Type Tool", "Toolbar > x", {}),
        Item("tool", "tool:moveTool", "Move Tool", "Toolbar > Move Tool", {}),
    ]
    claims = [
        claim(
            "t1", "Click with the Type tool.", named=[{"kind": "tool", "name": "Type", "text": ""}]
        )
    ]

    assert map_claims(claims, tools)[0].item_ids == (
        "tool:typeCreateOrEditTool",
        "tool:typeVerticalCreateOrEditTool",
    )


def test_a_sentence_repeated_on_another_page_points_at_its_first_appearance() -> None:
    move = [{"kind": "tool", "name": "Move", "text": "Move tool"}]
    claims = [
        claim("d1", "Drag with the Move tool.", named=move),
        claim("d2", "Drag with the  move tool. ", url="/photoshop/desktop/y.html", named=move),
    ]

    assert map_claims(claims, INVENTORY)[1] == Disposition(
        "d2", "matched", ("tool:moveTool",), duplicate_of="d1"
    )
