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
import snapshot_sources
from propose_update import review_body, proposal_files, package_digest


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
            # Only allowlisted numeric diagnostics: never echo service/account data or tokens.
            status = re.search(r"\(HTTP ([1-5][0-9]{2})\)", result.stderr)
            diagnostic = "HTTP " + status.group(1) if status else "HTTP status unavailable"
            if route == "/git/trees" and payload is not None:
                diagnostic += f"; tree entries={len(payload.get('tree', []))}"
            raise RuntimeError(f"GitHub API {method} {route.split('?')[0]} failed ({diagnostic}); inspect the workflow's permissions and repository state")
        return json.loads(result.stdout)

    def branch(self, name: str):
        entries = self.request("GET", "/git/matching-refs/heads/" + quote(name, safe="/"))
        matches = [entry for entry in entries if entry.get("ref") == "refs/heads/" + name]
        if len(matches) > 1:
            raise RuntimeError("Ambiguous existing proposal branch")
        return matches[0]["object"]["sha"] if matches else None


def checked_plan(files: dict, installed: dict) -> dict:
    raw = files["sources.update.json"]["content"]
    plan = json.loads(raw)
    if (not isinstance(plan, dict) or set(plan) != {"schema", "sources"} or plan["schema"] != 1
            or not isinstance(plan["sources"], dict) or set(plan["sources"]) != set(skills.SOURCES)):
        raise RuntimeError("Invalid complete source-update plan")
    for name, entry in plan["sources"].items():
        if (not isinstance(entry, dict) or set(entry) != {"from_sha", "to_sha"}
                or entry["from_sha"] != installed[name]["sha"]
                or not isinstance(entry["to_sha"], str) or not skills.SHA_RE.fullmatch(entry["to_sha"])):
            raise RuntimeError("Stale or invalid source-update plan: " + name)
    return plan


def publish(proposal_dir: Path, expected_digest: str | None) -> int:
    installed = skills.read_lock()["sources"]
    if not installed:
        print(json.dumps({"status": "not-installed"}))
        return 3
    baseline = snapshot_sources.verify()
    files = proposal_files(proposal_dir)
    digest = package_digest(files)
    if not expected_digest or digest != expected_digest:
        raise RuntimeError("Complete proposal bytes do not match the trusted generation step; prepare a fresh proposal")
    plan = checked_plan(files, installed)
    proposed = json.loads(files["sources.snapshot.json"]["content"])
    for name, entry in plan["sources"].items():
        if proposed["sources"][name]["commit_sha"] != entry["to_sha"]:
            raise RuntimeError("Proposed source snapshot differs from the frozen plan: " + name)
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
    targets = ["sources.lock.json", "sources.snapshot.json", "sources.update.json"]
    targets.extend(source["directory"] for source in baseline["sources"].values())
    if skills.git("status", "--porcelain", "--untracked-files=all", "--", *targets, cwd=skills.ROOT):
        raise RuntimeError("Snapshot publication targets have local changes; use an unchanged committed checkout")
    baseline_roots = {name: ("100644", "blob", git_blob_sha((skills.ROOT / name).read_bytes()))
                      for name in ("sources.lock.json", "sources.snapshot.json")}
    for name, expected in baseline_roots.items():
        if skills.git("ls-tree", "HEAD", "--", name, cwd=skills.ROOT) != " ".join(expected) + "\t" + name:
            raise RuntimeError("The baseline must contain unchanged regular committed lock and snapshot files")
    for source in baseline["sources"].values():
        expected = "040000 tree " + source["scope_tree_sha"] + "\t" + source["directory"]
        if skills.git("ls-tree", "HEAD", "--", source["directory"], cwd=skills.ROOT) != expected:
            raise RuntimeError("The visible source trees must match their committed provenance")
    api = GitHub(repository)
    metadata = api.request("GET")
    default = metadata["default_branch"]
    if metadata["full_name"].lower() != repository.lower() or os.environ.get("GITHUB_REF") != "refs/heads/" + default:
        raise RuntimeError("Publishing is allowed only on this repository's default branch")
    default_route = "/git/ref/heads/" + quote(default, safe="/")

    def root_entries(tree_sha):
        tree = api.request("GET", "/git/trees/" + tree_sha)
        if tree.get("truncated") is not False:
            raise RuntimeError("Cannot verify a truncated or unspecified Git tree")
        entries = {entry["path"]: (entry["mode"], entry["type"], entry["sha"]) for entry in tree["tree"]}
        if len(entries) != len(tree["tree"]):
            raise RuntimeError("Duplicate Git tree entries")
        return entries

    def upstream_entries(root):
        entry = root.get("upstream")
        if not entry or entry[:2] != ("040000", "tree"):
            raise RuntimeError("Expected a committed upstream directory")
        return root_entries(entry[2])

    def check_baseline(root):
        if any(root.get(name) != expected for name, expected in baseline_roots.items()):
            raise RuntimeError("Committed snapshot baseline changed; run a fresh workflow")
        upstream = upstream_entries(root)
        for source in baseline["sources"].values():
            if upstream.get(source["directory"].split("/")[1]) != ("040000", "tree", source["scope_tree_sha"]):
                raise RuntimeError("Committed source trees differ from the baseline")
        return upstream

    def verify_base():
        current = api.request("GET", default_route)["object"]["sha"]
        if current != expected_sha:
            raise RuntimeError("Default branch changed; run a fresh workflow")
        root = root_entries(api.request("GET", "/git/commits/" + current)["tree"]["sha"])
        check_baseline(root)
        return root

    base_root = verify_base()
    identity = digest
    branch = "automation/skill-update-" + identity
    message = "Assimilation complete source update " + identity
    title = "Review upstream skill source updates"
    body = review_body(plan["sources"])
    proposed_roots = {name: ("100644", "blob", git_blob_sha(files[name]["content"]))
                      for name in ("sources.lock.json", "sources.snapshot.json", "sources.update.json")}

    def expected_upstream(original):
        expected = dict(original)
        for source in proposed["sources"].values():
            expected[source["directory"].split("/")[1]] = ("040000", "tree", source["scope_tree_sha"])
        return expected

    def inspect_branch(sha):
        commit = api.request("GET", "/git/commits/" + sha)
        if commit["message"] != message or len(commit["parents"]) != 1:
            raise RuntimeError("Proposal branch was changed; leaving it untouched")
        parent = commit["parents"][0]["sha"]
        parent_commit = api.request("GET", "/git/commits/" + parent)
        original = root_entries(parent_commit["tree"]["sha"])
        original_upstream = check_baseline(original)
        actual = root_entries(commit["tree"]["sha"])
        actual_upstream = upstream_entries(actual)
        expected = {**original, **proposed_roots, "upstream": actual["upstream"]}
        if (actual != expected or actual == original
                or actual_upstream != expected_upstream(original_upstream)):
            raise RuntimeError("Existing branch is not the unchanged complete source proposal; leaving it untouched")
        if parent != expected_sha:
            ancestry = api.request("GET", "/compare/" + parent + "..." + expected_sha)
            if ancestry["status"] not in {"ahead", "identical"}:
                raise RuntimeError("Proposal base is no longer on the default branch")

    def create_source_trees():
        known_blobs = {entry["git_blob_sha"] for source in baseline["sources"].values() for entry in source["files"].values()}
        for name, source in proposed["sources"].items():
            if source["scope_tree_sha"] == baseline["sources"][name]["scope_tree_sha"]:
                continue
            entries = []
            for path, entry in source["files"].items():
                item = {"path": path, "mode": entry["mode"], "type": "blob"}
                if entry["git_blob_sha"] in known_blobs:
                    item["sha"] = entry["git_blob_sha"]
                else:
                    raw = files[source["directory"] + "/" + path]["content"]
                    try:
                        item["content"] = raw.decode("utf-8")
                    except UnicodeDecodeError:
                        blob = api.request("POST", "/git/blobs", {"content": base64.b64encode(raw).decode(), "encoding": "base64"})
                        if blob["sha"] != entry["git_blob_sha"]:
                            raise RuntimeError("Uploaded binary blob identity mismatch")
                        item["sha"] = blob["sha"]
                        known_blobs.add(blob["sha"])
                entries.append(item)
            # No base_tree: exact replacement drops all removed upstream paths.
            tree = api.request("POST", "/git/trees", {"tree": entries})
            if tree["sha"] != source["scope_tree_sha"]:
                raise RuntimeError("Uploaded source tree differs from its verified provenance")

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
        create_source_trees()
        original_upstream = upstream_entries(base_root)
        changes = [{"path": name, "mode": entry[0], "type": entry[1], "sha": entry[2]}
                   for name, entry in expected_upstream(original_upstream).items()
                   if original_upstream.get(name) != entry]
        upstream_sha = base_root["upstream"][2]
        if changes:
            upstream_sha = api.request("POST", "/git/trees", {"base_tree": upstream_sha, "tree": changes})["sha"]
        if root_entries(upstream_sha) != expected_upstream(original_upstream):
            raise RuntimeError("Uploaded upstream tree changed unrelated source index content")
        base_commit = api.request("GET", "/git/commits/" + expected_sha)
        tree = api.request("POST", "/git/trees", {"base_tree": base_commit["tree"]["sha"], "tree": [
            {"path": name, "mode": "100644", "type": "blob", "content": files[name]["content"].decode("utf-8")}
            for name in proposed_roots] + [{"path": "upstream", "mode": "040000", "type": "tree", "sha": upstream_sha}]})
        if root_entries(tree["sha"]) != {**base_root, **proposed_roots, "upstream": ("040000", "tree", upstream_sha)}:
            raise RuntimeError("Uploaded proposal tree changed unrelated repository content")
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
    parser.add_argument("--expected-package-sha256", help="Complete package digest from the same trusted generation job")
    args = parser.parse_args()
    try:
        return publish(args.proposal_dir, args.expected_package_sha256)
    except (RuntimeError, OSError, ValueError, KeyError, TypeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
