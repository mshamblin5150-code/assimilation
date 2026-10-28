#!/usr/bin/env python3
"""Publish a frozen source-update proposal as a draft PR; never install or merge it."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import quote, urlencode

import skills
from propose_update import review_body


def git_blob_sha(content: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(content)).encode() + b"\0" + content).hexdigest()


class GitHub:
    def __init__(self, repository: str):
        self.repository = repository
        self.root = "/repos/" + repository

    def request(self, method: str, route: str = "", payload: dict | None = None):
        command = ["gh", "api", "--hostname", "github.com", "--method", method, self.root + route,
                   "--header", "Accept: application/vnd.github+json", "--header", "X-GitHub-Api-Version: 2022-11-28"]
        if payload is not None:
            command.extend(["--input", "-"])
        result = subprocess.run(command, input=json.dumps(payload) if payload is not None else None,
                                text=True, capture_output=True, check=False)
        if result.returncode:
            # Do not echo gh output: service errors can contain sensitive account data.
            raise RuntimeError(f"GitHub API {method} {route.split('?')[0]} failed; inspect the workflow's permissions and repository state")
        return json.loads(result.stdout)

    def file(self, name: str, revision: str) -> bytes:
        entry = self.request("GET", "/contents/" + name + "?" + urlencode({"ref": revision}))
        if entry.get("type") != "file" or entry.get("encoding") != "base64" or entry.get("path") != name:
            raise RuntimeError("Expected a regular GitHub file: " + name)
        return base64.b64decode("".join(entry["content"].split()), validate=True)

    def branch(self, name: str):
        entries = self.request("GET", "/git/matching-refs/heads/" + quote(name, safe="/"))
        matches = [entry for entry in entries if entry.get("ref") == "refs/heads/" + name]
        if len(matches) > 1:
            raise RuntimeError("Ambiguous existing proposal branch")
        return matches[0]["object"]["sha"] if matches else None


def checked_plan(proposal_dir: Path, installed: dict, expected_digest: str | None) -> tuple[dict, str]:
    path = proposal_dir / "sources.update.json"
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("Proposal must contain a regular sources.update.json")
    raw = path.read_bytes()
    if not expected_digest or hashlib.sha256(raw).hexdigest() != expected_digest:
        raise RuntimeError("Proposal bytes do not match the trusted generation step; prepare a fresh proposal")
    plan = json.loads(raw)
    if (not isinstance(plan, dict) or set(plan) != {"schema", "sources"} or plan["schema"] != 1
            or not isinstance(plan["sources"], dict) or set(plan["sources"]) != set(skills.SOURCES)):
        raise RuntimeError("Invalid complete source-update plan")
    for name, entry in plan["sources"].items():
        if (not isinstance(entry, dict) or set(entry) != {"from_sha", "to_sha"}
                or entry["from_sha"] != installed[name]["sha"]
                or not isinstance(entry["to_sha"], str) or not skills.SHA_RE.fullmatch(entry["to_sha"])):
            raise RuntimeError("Stale or invalid source-update plan: " + name)
    return plan, json.dumps(plan, sort_keys=True, indent=2) + "\n"


def publish(proposal_dir: Path, expected_digest: str | None) -> int:
    installed = skills.read_lock()["sources"]
    if not installed:
        print(json.dumps({"status": "not-installed"}))
        return 3
    plan, content = checked_plan(proposal_dir, installed, expected_digest)
    if all(entry["from_sha"] == entry["to_sha"] for entry in plan["sources"].values()):
        print(json.dumps({"status": "current"}))
        return 0
    repository = os.environ.get("GITHUB_REPOSITORY", "")
    expected_sha = os.environ.get("GITHUB_SHA", "")
    if (os.environ.get("GITHUB_ACTIONS") != "true" or os.environ.get("GITHUB_EVENT_NAME") not in {"schedule", "workflow_dispatch"}
            or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository)
            or not skills.SHA_RE.fullmatch(expected_sha) or not os.environ.get("GH_TOKEN")):
        raise RuntimeError("Publishing requires a trusted scheduled or manual Actions run with its repository token")
    if skills.git("rev-parse", "HEAD", cwd=skills.ROOT) != expected_sha:
        raise RuntimeError("Checkout HEAD differs from the workflow commit")
    committed_lock = skills.git("ls-tree", "HEAD", "--", "sources.lock.json", cwd=skills.ROOT)
    expected_lock = "100644 blob " + git_blob_sha(skills.LOCK.read_bytes()) + "\tsources.lock.json"
    if committed_lock != expected_lock:
        raise RuntimeError("The baseline must be an unchanged regular sources.lock.json committed in HEAD")
    api = GitHub(repository)
    metadata = api.request("GET")
    default = metadata["default_branch"]
    if metadata["full_name"].lower() != repository.lower() or os.environ.get("GITHUB_REF") != "refs/heads/" + default:
        raise RuntimeError("Publishing is allowed only on this repository's default branch")
    default_route = "/git/ref/heads/" + quote(default, safe="/")

    def verify_base():
        current = api.request("GET", default_route)["object"]["sha"]
        if current != expected_sha or api.file("sources.lock.json", current) != skills.LOCK.read_bytes():
            raise RuntimeError("Default branch or installed baseline changed; run a fresh workflow")

    verify_base()
    identity = hashlib.sha256(content.encode()).hexdigest()
    branch = "automation/skill-update-" + identity
    message = "Assimilation source update " + identity
    title = "Review upstream skill source updates"
    body = review_body(plan["sources"])

    def inspect_branch(sha):
        commit = api.request("GET", "/git/commits/" + sha)
        if commit["message"] != message or len(commit["parents"]) != 1:
            raise RuntimeError("Proposal branch was changed; leaving it untouched")
        parent = commit["parents"][0]["sha"]
        parent_commit = api.request("GET", "/git/commits/" + parent)

        def root_entries(tree_sha):
            tree = api.request("GET", "/git/trees/" + tree_sha)
            if tree.get("truncated") is not False:
                raise RuntimeError("Cannot verify a truncated or unspecified Git tree")
            entries = {entry["path"]: (entry["mode"], entry["type"], entry["sha"]) for entry in tree["tree"]}
            if len(entries) != len(tree["tree"]):
                raise RuntimeError("Duplicate Git tree entries")
            return entries

        original = root_entries(parent_commit["tree"]["sha"])
        actual = root_entries(commit["tree"]["sha"])
        expected_blob = git_blob_sha(content.encode())
        expected = {**original, "sources.update.json": ("100644", "blob", expected_blob)}
        if (actual != expected or actual == original
                or api.file("sources.lock.json", parent) != skills.LOCK.read_bytes()):
            raise RuntimeError("Existing branch is not the unchanged one-file proposal; leaving it untouched")
        if parent != expected_sha:
            ancestry = api.request("GET", "/compare/" + parent + "..." + expected_sha)
            if ancestry["status"] not in {"ahead", "identical"}:
                raise RuntimeError("Proposal base is no longer on the default branch")

    def find_pull():
        query = urlencode({"state": "all", "head": repository.split("/")[0] + ":" + branch,
                           "base": default, "per_page": 100})
        pulls = api.request("GET", "/pulls?" + query)
        if len(pulls) > 1:
            raise RuntimeError("Multiple matching PRs need human review")
        return pulls[0] if pulls else None

    def validate_pull(pull, sha):
        if (pull.get("state") != "open" or pull.get("draft") is not True
                or pull.get("title") != title or pull.get("body") != body
                or pull.get("user", {}).get("login") != "github-actions[bot]"
                or pull["head"]["ref"] != branch or pull["head"]["sha"] != sha
                or pull["base"]["ref"] != default
                or pull["head"]["repo"]["full_name"].lower() != repository.lower()
                or pull["base"]["repo"]["full_name"].lower() != repository.lower()):
            raise RuntimeError("Existing PR is closed, promoted, human-owned, or changed; leaving it untouched")

    pull = find_pull()
    sha = api.branch(branch)
    if pull is not None and sha is None:
        raise RuntimeError("Existing PR has no matching proposal branch; inspect manually")
    if sha is None:
        base_commit = api.request("GET", "/git/commits/" + expected_sha)
        tree = api.request("POST", "/git/trees", {"base_tree": base_commit["tree"]["sha"], "tree": [
            {"path": "sources.update.json", "mode": "100644", "type": "blob", "content": content}]})
        commit = api.request("POST", "/git/commits", {"message": message, "tree": tree["sha"], "parents": [expected_sha]})
        verify_base()
        api.request("POST", "/git/refs", {"ref": "refs/heads/" + branch, "sha": commit["sha"]})
        sha = commit["sha"]
    inspect_branch(sha)
    if pull is not None:
        validate_pull(pull, sha)
        status = "draft-reused"
    else:
        verify_base()
        if api.branch(branch) != sha:
            raise RuntimeError("Proposal branch changed before PR creation; inspect manually")
        pull = api.request("POST", "/pulls", {"title": title, "head": branch,
                                              "base": default, "draft": True, "body": body})
        validate_pull(pull, sha)
        status = "draft-created"
    verify_base()
    if api.branch(branch) != sha:
        raise RuntimeError("Proposal branch changed after PR publication; retained draft needs human review")
    print(json.dumps({"status": status, "url": pull["html_url"], "branch": branch}))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proposal-dir", type=Path, required=True)
    parser.add_argument("--expected-plan-sha256", help="Raw plan digest from the same trusted generation job")
    args = parser.parse_args()
    try:
        return publish(args.proposal_dir, args.expected_plan_sha256)
    except (RuntimeError, OSError, ValueError, KeyError, TypeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
