from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.adobe_observed_truth import rea_evidence


# Exported by rea-agents 6.8.0 export_evidence_bundle: one shipped-artifact
# record (inspect_pe_imports) and one controlled-replay record REA imported.
REFERENCE = Path(__file__).parent / "fixtures" / "rea_evidence_bundle_reference.json"


def reference_bundle() -> dict:
    return json.loads(REFERENCE.read_text(encoding="utf-8"))


def test_evidence_id_matches_the_id_rea_computed_for_each_record() -> None:
    for record in reference_bundle()["records"]:
        assert rea_evidence.evidence_id(record) == record["evidence_id"]


def test_bundle_reproduces_rea_canonical_manifests_regardless_of_record_order() -> None:
    reference = reference_bundle()

    bundle = rea_evidence.evidence_bundle(list(reversed(reference["records"])))

    assert bundle == reference


# Live harness records that REA 6.8.0 import_evidence_bundle authenticated on
# 2026-11-08; one cites four captures as artifact-path locations.
ACCEPTED = Path(__file__).parent / "fixtures" / "rea_accepted_harness_bundle.json"


def test_observation_record_rebuilds_every_record_rea_accepted_from_its_inputs() -> None:
    accepted = json.loads(ACCEPTED.read_text(encoding="utf-8"))["records"]

    for record in accepted:
        rebuilt = rea_evidence.observation_record(
            subject={"path": record["subject"]["local_path"], "sha256": record["subject"]["digest"]["sha256"]},
            environment=record["environment"],
            operation=record["operation"],
            parameters=record["parameters"],
            observed=record["normalized_result"],
            limitations=record["limitations"],
            artifact_paths=[location["path"] for location in record["locations"]],
        )
        assert rebuilt == record


def test_observation_record_rejects_floats_whose_text_differs_between_python_and_js() -> None:
    with pytest.raises(TypeError, match=r"observed\.opacity"):
        rea_evidence.observation_record(
            subject={"path": r"C:\Photoshop.exe", "sha256": "a" * 64},
            environment={"id": "host", "platform": "win32", "architecture": "x86_64", "isolation": "none"},
            operation="observe_eraser_opacity",
            parameters={},
            observed={"opacity": 1e-07},
            limitations=[],
        )
