"""Small complete upstream repositories, assembled with Git rather than production helpers."""
import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess

REPOSITORIES = {"matt": "https://github.com/mattpocock/skills.git", "pstack": "https://github.com/cursor/plugins.git"}
DIRECTORIES = {"matt": "upstream/matt-pocock", "pstack": "upstream/pstack"}


def git(path, *args, env=None, raw=False):
    output = subprocess.run(["git", *args], cwd=path, env=env, capture_output=True, check=True).stdout
    return output if raw else output.decode().strip()


def make_sources(work, env):
    repos = {}
    license_text = (Path(__file__).resolve().parents[1] / "LICENSE").read_bytes()
    for name in REPOSITORIES:
        repo = work / ("source-" + name)
        repo.mkdir()
        git(repo, "init", "--initial-branch=main", env=env)
        git(repo, "config", "user.name", "Source Fixture", env=env)
        git(repo, "config", "user.email", "source@example.invalid", env=env)
        scope = repo if name == "matt" else repo / "pstack"
        scope.mkdir(exist_ok=True)
        (scope / "LICENSE").write_bytes(license_text.replace(b"Matt Shamblin", b"Matt Pocock" if name == "matt" else b"Lauren Tan"))
        (scope / "README.md").write_text("Synthetic source version one\n")
        (scope / "obsolete.txt").write_text("Removed in the next source version\n")
        (scope / "skills/example").mkdir(parents=True)
        (scope / "skills/example/SKILL.md").write_text("---\nname: example\ndescription: Synthetic fixture\n---\nDo not execute.\n")
        if name == "pstack":
            (repo / "outside-scope.txt").write_text("Not part of P-Stack\n")
        git(repo, "add", ".", env=env)
        git(repo, "commit", "-m", "source baseline", env=env)
        repos[name] = repo
        env["ASSIMILATION_" + name.upper() + "_SOURCE"] = str(repo)
    return repos


def snapshot_at(root, repos, env):
    """Write independent Git-backed fixture evidence for each source's current HEAD."""
    records, sources = {}, {}
    for name, repo in repos.items():
        sha = git(repo, "rev-parse", "HEAD", env=env)
        tree = git(repo, "rev-parse", "HEAD^{tree}", env=env)
        scope = "." if name == "matt" else "pstack"
        scope_tree = tree if name == "matt" else git(repo, "rev-parse", "HEAD:pstack", env=env)
        directory = DIRECTORIES[name]
        records[name] = {"repository": REPOSITORIES[name], "branch": "main", "sha": sha}
        files = {}
        for row in git(repo, "ls-tree", "-r", "-z", scope_tree, env=env, raw=True).split(b"\0"):
            if not row:
                continue
            meta, filename = row.split(b"\t", 1)
            mode, kind, blob = meta.decode().split()
            assert kind == "blob"
            filename = filename.decode()
            content = git(repo, "cat-file", "blob", blob, env=env, raw=True)
            path = root / directory / filename
            path.parent.mkdir(parents=True, exist_ok=True)
            if mode == "120000":
                path.symlink_to(content.decode())
            else:
                path.write_bytes(content)
                path.chmod(0o755 if mode == "100755" else 0o644)
            files[filename] = {"mode": mode, "git_blob_sha": blob, "sha256": hashlib.sha256(content).hexdigest(), "size": len(content)}
        sources[name] = {"directory": directory, "repository": REPOSITORIES[name], "commit_sha": sha,
                         "root_tree_sha": tree, "scope": scope, "scope_tree_sha": scope_tree,
                         "commit_object": base64.b64encode(git(repo, "cat-file", "commit", sha, env=env, raw=True)).decode(),
                         "root_tree_object": base64.b64encode(git(repo, "cat-file", "tree", tree, env=env, raw=True)).decode(),
                         "files": files}
    for name, data in (("sources.lock.json", {"schema": 1, "sources": records}),
                       ("sources.snapshot.json", {"schema": 1, "sources": sources})):
        (root / name).write_text(json.dumps(data, sort_keys=True, indent=2) + "\n")
    return records


def advance_matt(repo, env):
    (repo / "README.md").write_text("Synthetic source version two\n")
    (repo / "obsolete.txt").unlink()
    (repo / "binary.dat").write_bytes(b"\x00\xff\xfe\x01source-binary\n")
    (repo / "run.sh").write_text("#!/bin/sh\nexit 99 # Fixture: must never run\n")
    (repo / "run.sh").chmod(0o755)
    (repo / "README-link").symlink_to("README.md")
    (repo / ".github/workflows").mkdir(parents=True)
    (repo / ".github/workflows/dormant.yml").write_text("name: Dormant upstream metadata\n")
    git(repo, "add", "-A", env=env)
    git(repo, "commit", "-m", "source update", env=env)
    return git(repo, "rev-parse", "HEAD", env=env)
