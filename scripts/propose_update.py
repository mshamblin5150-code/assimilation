#!/usr/bin/env python3
"""Prepare a frozen source-update proposal without installing or publishing it."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import skills


def propose(output: Path) -> int:
    installed = skills.read_lock()["sources"]
    if not installed:
        print(json.dumps({"status": "not-installed", "sources": {}}))
        return 3
    changes = {name: {"from_sha": installed[name]["sha"], "to_sha": skills.head(name)}
               for name in skills.SOURCES}
    if all(change["from_sha"] == change["to_sha"] for change in changes.values()):
        print(json.dumps({"status": "current", "sources": changes}, indent=2))
        return 0
    plan = {"schema": 1, "sources": changes}
    output.mkdir()
    (output / "sources.update.json").write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    lines = ["# Review upstream skill updates", "",
             "This proposal freezes source commits. It does not install, execute, approve, or merge upstream changes.", ""]
    for name, change in changes.items():
        repository = skills.SOURCES[name]["url"].removesuffix(".git")
        lines.append(f"- {name}: [review source diff]({repository}/compare/{change['from_sha']}..{change['to_sha']})")
    lines.extend(["", "## Before merge", "",
                  "- Review source changes, licenses, compatibility, and executable tools.",
                  "- Apply the frozen plan only in a clean, isolated checkout of this proposal's base commit:", "",
                  "```sh", "python3 scripts/skills.py install --locked",
                  "python3 scripts/skills.py install --approve-update --update-plan sources.update.json",
                  "python3 -m unittest discover -s tests -v", "```", "",
                  "- If --locked reports an existing or edited installation, stop and use a fresh checkout. Do not add approval flags to bypass that mismatch.",
                  "- Confirm each resulting lock SHA equals the plan's to_sha, even if main has moved.",
                  "- Commit the resulting sources.lock.json and retain the reviewed plan as evidence.",
                  "- Record test results and obtain independent review and operator acceptance.",
                  "- Do not enable automatic merge. Passing tests do not approve upstream instructions.", ""])
    (output / "PULL_REQUEST.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"status": "updates-available", "sources": changes}, indent=2))
    return 2


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True,
                        help="New directory for a frozen update plan and draft PR body")
    args = parser.parse_args()
    try:
        return propose(args.output_dir)
    except (RuntimeError, OSError, ValueError, KeyError, TypeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
