"""The pixel exporter's ExtendScript helpers."""

from __future__ import annotations

import re

from scripts.adobe_observed_truth.ps_pixels import _EXPORT_JS


def test_a_layers_visibility_is_only_set_when_it_changes() -> None:
    # Setting visible=true on the only, already visible, layer is a Show command Photoshop calls
    # unavailable, and it answered with an alert (a one-layer document, 2026-11-25).
    assignments = re.findall(r"[\w\[\]\.]+\.visible=[^=;]+", _EXPORT_JS)
    guarded = re.findall(r"if\(([\w\[\]\.]+)\.visible!=([^)]+)\)\1\.visible=\2", _EXPORT_JS)

    assert assignments and len(guarded) == len(assignments)
