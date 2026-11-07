#!/usr/bin/env python3
"""Offline evidence integrity checks; does not rerun remote recovery drills."""
import hashlib
import json
from pathlib import Path


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    root = Path(__file__).resolve().parent
    manifest = json.loads((root / "SHA256.json").read_text())
    for name, expected in manifest.items():
        path = root / name
        if path.parent != root or not path.is_file():
            raise ValueError(f"Missing or invalid bundle member: {name}")
        if digest(path.read_bytes()) != expected:
            raise ValueError(f"Bundle hash mismatch: {name}")
    fixture = json.loads((root / "fixture.json").read_text())
    expected = fixture["artifact"]
    good = (root / "synthetic-report.txt").read_bytes()
    bad = (root / "synthetic-report-corrupt-control.txt").read_bytes()
    if len(good) != expected["expected_byte_size"] or digest(good) != expected["expected_sha256"]:
        raise ValueError("Valid payload did not match its recorded acceptance boundary")
    if len(bad) != len(good) or digest(bad) == expected["expected_sha256"]:
        raise ValueError("Same-size corruption control did not fail the expected hash")
    if good != expected["content"].encode(expected["encoding"]):
        raise ValueError("Retained payload differs from the embedded checkpoint source")
    print(f"PASS: {len(manifest)} retained file hashes; valid payload accepted; same-size corruption rejected.")
    print("Offline integrity only. Remote service and worker experiments were not rerun.")


if __name__ == "__main__":
    main()
