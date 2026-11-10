#!/usr/bin/env python3
"""Offline advisory check of an agent's declared publication context.

This does not read, scan, approve, publish, or attest to the underlying content.
Input contains status codes only; do not put private source or transcripts in it.
"""
import argparse
import json
from pathlib import Path

MAX_BYTES = 32768
REQUIRED = {
    "schema_version",
    "destination",
    "authority",
    "content",
    "evaluation",
}
SECTIONS = {
    "destination": {"visibility", "audience"},
    "authority": {"publication", "scope"},
    "content": {"review", "redistribution", "sensitive_material"},
    "evaluation": {"context", "undisclosed_material", "release_clearance"},
}
OPTIONS = {
    "visibility": {"public", "restricted", "unknown"},
    "audience": {"public", "restricted", "unknown"},
    "publication": {"confirmed", "unconfirmed", "unknown"},
    "scope": {"confirmed", "mismatch", "unknown"},
    "review": {"completed", "incomplete", "unknown"},
    "redistribution": {"confirmed", "unconfirmed", "unknown"},
    "sensitive_material": {"none", "present", "unknown"},
    "context": {"none", "active", "unknown"},
    "undisclosed_material": {"none", "present", "unknown"},
    "release_clearance": {"confirmed", "unconfirmed", "not_applicable", "unknown"},
}


def unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate key")
        result[key] = value
    return result


def invalid_constant(_value):
    raise ValueError("non-JSON constant")


def inspect(record):
    """Return fixed, value-free findings; no claim of actual safety is possible."""
    if not isinstance(record, dict) or set(record) != REQUIRED:
        return ["record: v1 fields missing or unexpected"]
    findings = []
    if type(record["schema_version"]) is not int or record["schema_version"] != 1:
        findings.append("schema_version: expected 1")
    for name, keys in SECTIONS.items():
        section = record[name]
        if not isinstance(section, dict) or set(section) != keys:
            findings.append(name + ": fields missing or unexpected")
            continue
        for key in keys:
            if type(section[key]) is not str or section[key] not in OPTIONS[key]:
                findings.append(name + "." + key + ": invalid choice")
    if findings:
        return sorted(findings)

    dest, auth, content, exam = (record[name] for name in
                                 ("destination", "authority", "content", "evaluation"))
    if dest["visibility"] == "unknown" or dest["audience"] == "unknown":
        findings.append("destination: audience or visibility unverified")
    if (dest["visibility"] != "unknown" and dest["audience"] != "unknown"
            and dest["visibility"] != dest["audience"]):
        findings.append("destination: visibility and intended audience differ")
    if auth["publication"] != "confirmed":
        findings.append("authority: publication permission not verified")
    if auth["scope"] != "confirmed":
        findings.append("authority: destination and disclosure scope not verified")
    if content["review"] != "completed":
        findings.append("content: actual material not reviewed for publication")
    if content["redistribution"] != "confirmed":
        findings.append("content: sharing rights not verified")
    if content["sensitive_material"] == "unknown":
        findings.append("content: restricted material status unknown")
    if dest["visibility"] == "public" and content["sensitive_material"] != "none":
        findings.append("content: restricted material cannot be publicly posted")
    if exam["context"] == "unknown" or exam["undisclosed_material"] == "unknown":
        findings.append("evaluation: impact on an existing assessment unknown")
    if exam["context"] == "active" and exam["release_clearance"] != "confirmed":
        findings.append("evaluation: release clearance not verified")
    if exam["undisclosed_material"] == "present" and exam["release_clearance"] != "confirmed":
        findings.append("evaluation: nonpublic evaluation material not cleared")
    if exam["context"] == "none" and exam["undisclosed_material"] == "present":
        findings.append("evaluation: inconsistent nonpublic-material classification")
    return sorted(set(findings))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("record", type=Path, help="locally held, status-only JSON record")
    args = parser.parse_args()
    try:
        if not args.record.is_file():
            raise ValueError("not a regular file")
        with args.record.open("rb") as stream:
            payload = stream.read(MAX_BYTES + 1)
        if len(payload) > MAX_BYTES:
            raise ValueError("input too large")
        record = json.loads(payload.decode("utf-8"), object_pairs_hook=unique_keys,
                            parse_constant=invalid_constant)
    except (OSError, UnicodeError, ValueError, RecursionError):
        print("preflight: INVALID_INPUT")
        return 2
    findings = inspect(record)
    if findings:
        print("preflight: REVIEW_REQUIRED")
        for finding in findings:
            print("preflight: " + finding)
        return 1
    print("preflight: DECLARATIONS_CONSISTENT; actual material, authority, "
          "audience and delivery not verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
