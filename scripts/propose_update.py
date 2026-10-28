#!/usr/bin/env python3
"""Prepare a frozen source-update proposal without installing or publishing it."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile

import snapshot_sources
import skills


def propose(output: Path) -> int:
    installed = skills.read_lock()["sources"]
    if not installed:
        print(json.dumps({"status": "not-installed", "sources": {}}))
        return 3
    snapshot_sources.verify()
    changes = {name: {"from_sha": installed[name]["sha"], "to_sha": snapshot_sources.head(name)}
               for name in skills.SOURCES}
    if all(change["from_sha"] == change["to_sha"] for change in changes.values()):
        print(json.dumps({"status": "current", "sources": changes}, indent=2))
        return 0
    plan = {"schema": 1, "sources": changes}
    with tempfile.TemporaryDirectory(prefix="assimilation-plan-") as temporary:
        plan_path = Path(temporary) / "sources.update.json"
        serialized = json.dumps(plan, sort_keys=True, indent=2) + "\n"
        plan_path.write_text(serialized, encoding="utf-8")
        snapshot_sources.prepare(plan_path, output)
    (output / "sources.update.json").write_text(serialized, encoding="utf-8")
    (output / "PULL_REQUEST.md").write_text(review_body(changes), encoding="utf-8")
    digest = package_digest(proposal_files(output))
    print(json.dumps({"status": "updates-available", "sources": changes, "package_sha256": digest}, indent=2))
    return 2


def proposal_files(root: Path) -> dict:
    """Verified publishable bytes only; local files and the recomputed PR body stay out."""
    files = snapshot_sources.package_files(root)
    path = root / "sources.update.json"
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("Proposal must contain a regular sources.update.json")
    files["sources.update.json"] = {"mode": "100644", "content": snapshot_sources.file_bytes(path, "100644")}
    return files


def package_digest(files: dict) -> str:
    inventory = {path: {"mode": entry["mode"], "sha256": hashlib.sha256(entry["content"]).hexdigest(),
                        "size": len(entry["content"])} for path, entry in files.items()}
    return hashlib.sha256(json.dumps(inventory, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def review_body(changes: dict) -> str:
    lines = ["# Review upstream skill updates", "",
             "This draft contains the complete proposed source snapshots, pin lock, provenance, and frozen plan. "
             "A reviewed merge adopts them together; it does not install or execute upstream code.", ""]
    for name, change in changes.items():
        repository = skills.SOURCES[name]["url"].removesuffix(".git")
        lines.append(f"- {name}: [review source diff]({repository}/compare/{change['from_sha']}..{change['to_sha']})")
    lines.extend(["", "## Before merge", "",
                  "- Review source changes, licenses, compatibility, executable tools, and dormant upstream configuration.",
                  "- Confirm changes are limited to upstream/matt-pocock, upstream/pstack, sources.lock.json, sources.snapshot.json, and sources.update.json.",
                  "- In a clean, isolated checkout of this proposal branch, verify the complete snapshot offline:", "",
                  "```sh", "python3 scripts/snapshot_sources.py verify",
                  "python3 -m unittest discover -s tests -v", "```", "",
                  "- Confirm each lock and provenance commit equals the plan's to_sha, even if upstream main has moved.",
                  "- Preserve upstream licenses and source bytes. Never execute upstream scripts merely to review this PR.",
                  "- Record compatibility checks and obtain independent review and operator acceptance for this exact commit.",
                  "- Approve requested CI workflow runs only after review; an open draft is not proof checks ran.",
                  "- No separate post-merge snapshot step is needed. Host skill installation remains an explicit local choice.",
                  "- Do not enable automatic approval or merge. Passing tests do not approve upstream instructions.", ""])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True,
                        help="New directory for a complete frozen source package and draft PR body")
    args = parser.parse_args()
    try:
        return propose(args.output_dir)
    except (RuntimeError, OSError, ValueError, KeyError, TypeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
