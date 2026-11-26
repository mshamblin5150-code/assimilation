"""REA Evidence records and bundles that rea-agents 6.8.0 import_evidence_bundle accepts.

Mirrors rea-agents dist/domain/evidence.js (semantic identity) and
dist/domain/evidenceBundle.js (canonical bundle manifests).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import PureWindowsPath
from collections.abc import Sequence
from typing import Any


HARNESS_PROVIDER = {
    "id": "adobe-observed-truth",
    "name": "Adobe observed-truth harness",
    "version": "0.2.0",
}
SCENARIO_PREDICATE = "adobe-observed-truth.windows-ui-scenario"

SEMANTIC_FIELDS = (
    "provider",
    "analysis_profile",
    "predicate_type",
    "operation",
    "parameters",
    "raw_result",
    "normalized_result",
    "confidence",
    "authority",
    "environment",
    "limitations",
    "relationship_coverage",
    "locations",
    "evidence_links",
)


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def evidence_id(record: dict[str, Any]) -> str:
    subject = record["subject"]
    semantic = {field: record[field] for field in SEMANTIC_FIELDS}
    semantic["subject"] = (
        None
        if subject is None
        else {
            "digest": subject["digest"],
            "format": subject["format"],
            "architecture": subject["architecture"],
        }
    )
    digest = hashlib.sha256(canonical_json(semantic).encode("utf-8")).hexdigest()
    return f"ev_{digest}"


def observation_record(
    *,
    subject: dict[str, str],
    environment: dict[str, str],
    operation: str,
    parameters: dict[str, Any],
    observed: dict[str, Any],
    limitations: list[str],
    artifact_paths: Sequence[str] = (),
) -> dict[str, Any]:
    """One harness run observed against the exact binary named by subject."""
    _reject_floats(parameters, "parameters")
    _reject_floats(observed, "observed")
    record = {
        "subject": {
            "name": PureWindowsPath(subject["path"]).name,
            "digest": {"sha256": subject["sha256"]},
            "local_path": subject["path"],
            "format": "pe",
            "architecture": "x86_64",
        },
        "provider": HARNESS_PROVIDER,
        "analysis_profile": None,
        "predicate_type": SCENARIO_PREDICATE,
        "operation": operation,
        "parameters": parameters,
        "raw_result": None,
        "normalized_result": observed,
        "confidence": "observed",
        "authority": "controlled-replay",
        "environment": environment,
        "limitations": limitations,
        "relationship_coverage": None,
        "locations": [
            {"kind": "artifact-path", "path": path} for path in artifact_paths
        ],
        "evidence_links": [],
    }
    return {"evidence_id": evidence_id(record), **record}


def _reject_floats(value: Any, path: str) -> None:
    # Python and JavaScript print some floats differently, which breaks REA's ID check.
    if isinstance(value, float):
        raise TypeError(f"{path} is a float; record it as an integer or string")
    if isinstance(value, dict):
        for key, item in value.items():
            _reject_floats(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _reject_floats(item, f"{path}[{index}]")


def evidence_bundle(records: list[dict[str, Any]]) -> dict[str, Any]:
    ordered = sorted(records, key=lambda record: record["evidence_id"])
    return {
        "artifacts": _unique_sorted(
            {
                "digest": record["subject"]["digest"],
                "format": record["subject"]["format"],
                "architecture": record["subject"]["architecture"],
            }
            for record in ordered
            if record["subject"] is not None
        ),
        "providers": _unique_sorted(
            _schema_ordered(record["provider"], ("id", "name", "version"))
            for record in ordered
        ),
        "environments": _unique_sorted(
            _schema_ordered(
                record["environment"], ("id", "platform", "architecture", "isolation")
            )
            for record in ordered
            if record["environment"] is not None
        ),
        "scenarios": [
            {
                "evidence_id": record["evidence_id"],
                "operation": record["operation"],
                "authority": record["authority"],
            }
            for record in ordered
            if record["authority"] == "controlled-replay"
        ],
        "captures": [
            {
                "evidence_id": record["evidence_id"],
                "predicate_type": record["predicate_type"],
            }
            for record in ordered
            if record["predicate_type"] == "rea.process-capture"
        ],
        "unknowns": [],
        "records": ordered,
    }


def _schema_ordered(value: dict[str, Any], keys: tuple[str, ...]) -> dict[str, Any]:
    # REA sorts manifests by JSON.stringify text, which follows zod schema key order.
    return {key: value[key] for key in keys}


def _unique_sorted(values) -> list[dict[str, Any]]:
    unique = {
        json.dumps(value, separators=(",", ":"), ensure_ascii=False): value
        for value in values
    }
    return [unique[text] for text in sorted(unique)]
