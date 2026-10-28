#!/usr/bin/env python3
"""Assimilation: download upstream skill trees, expose namespaced bridges, and audit updates.

Standard-library only. Git and Python >= 3.10 required. No upstream code is executed.
"""
from __future__ import annotations

import argparse
import datetime as dt
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "sources.lock.json"
BRIDGES = ROOT / ".agents" / "skills"
MARKER = ".assimilation-managed.json"
VENDOR = ROOT / "vendor"
SOURCES = {
    "matt": {
        "url": "https://github.com/mattpocock/skills.git",
        "branch": "main",
        "sparse": ["skills", "docs"],
        "path": ".",
        "skill_dir": "skills/engineering",
        "prefix": "matt",
    },
    "pstack": {
        "url": "https://github.com/cursor/plugins.git",
        "branch": "main",
        "sparse": ["pstack"],
        "path": "pstack",
        "skill_dir": "skills",
        "prefix": "pstack",
    },
}
SHA_RE = re.compile(r"^[a-f0-9]{40}$")


def git(*args: str, cwd: Path | None = None, capture: bool = True) -> str:
    cmd = ["git", *args]
    proc = subprocess.run(cmd, cwd=cwd, text=True, stdout=subprocess.PIPE if capture else None,
                          stderr=subprocess.PIPE, check=False)
    if proc.returncode:
        detail = (proc.stderr or "").strip()
        raise RuntimeError(f"git {' '.join(args[:3])} failed: {detail[:600]}")
    return (proc.stdout or "").strip()


def effective_source(name: str) -> str:
    # Override is for local mirrors and deterministic offline tests; never persisted as a credential.
    return os.environ.get(f"ASSIMILATION_{name.upper()}_SOURCE", SOURCES[name]["url"])


def head(name: str) -> str:
    spec = SOURCES[name]
    value = git("ls-remote", effective_source(name), f"refs/heads/{spec['branch']}")
    if not value:
        raise RuntimeError(f"Could not locate {name} branch {spec['branch']}")
    sha = value.split()[0]
    if not SHA_RE.fullmatch(sha):
        raise RuntimeError(f"Unrecognized {name} commit SHA")
    return sha


def read_lock() -> dict:
    validate_path(LOCK)
    if not LOCK.exists():
        return {"schema": 1, "sources": {}}
    if not LOCK.is_file():
        raise RuntimeError("Invalid sources.lock.json: expected a regular file")
    data = json.loads(LOCK.read_text(encoding="utf-8"))
    if (not isinstance(data, dict) or data.get("schema") != 1 or
            not isinstance(data.get("sources"), dict) or set(data["sources"]) != set(SOURCES)):
        raise RuntimeError("Invalid sources.lock.json: expected the complete schema 1 source baseline")
    for name, entry in data["sources"].items():
        if (not isinstance(entry, dict) or not isinstance(entry.get("sha"), str)
                or not SHA_RE.fullmatch(entry["sha"])
                or entry.get("repository") != SOURCES[name]["url"]
                or entry.get("branch") != SOURCES[name]["branch"]):
            raise RuntimeError(f"Invalid sources.lock.json entry: {name}")
    return data


def check() -> int:
    old = read_lock()["sources"]
    if not old:
        print(json.dumps({"status": "not-installed", "sources": {}}, indent=2))
        return 3
    delta = {}
    for name in SOURCES:
        sha = head(name)
        prior = old.get(name, {}).get("sha")
        delta[name] = {"recorded": prior, "upstream": sha, "changed": prior != sha}
    result = {"status": "updates-available" if any(d["changed"] for d in delta.values()) else "current", "sources": delta}
    print(json.dumps(result, indent=2))
    return 2 if result["status"] == "updates-available" else 0


def clone_sparse(name: str, dest: Path, revision: str | None = None) -> str:
    spec = SOURCES[name]
    if revision is None:
        git("clone", "--quiet", "--depth", "1", "--filter=blob:none", "--sparse", "--branch", spec["branch"],
            effective_source(name), str(dest))
        git("sparse-checkout", "set", *spec["sparse"], cwd=dest)
    else:
        git("init", "--quiet", str(dest))
        git("remote", "add", "origin", effective_source(name), cwd=dest)
        git("sparse-checkout", "init", "--cone", cwd=dest)
        git("sparse-checkout", "set", *spec["sparse"], cwd=dest)
        git("fetch", "--quiet", "--depth", "1", "--filter=blob:none", "origin", revision, cwd=dest)
        git("checkout", "--quiet", "--detach", "FETCH_HEAD", cwd=dest)
    sha = git("rev-parse", "HEAD", cwd=dest)
    if not SHA_RE.fullmatch(sha) or (revision is not None and sha != revision):
        raise RuntimeError("Could not verify exact checkout hash")
    return sha


def fingerprint(path: Path) -> str:
    """Hash all names, entry types, modes and bytes; never follow links."""
    digest = hashlib.sha256()

    def visit(item: Path, relative: str) -> None:
        info = item.lstat()
        mode = stat.S_IMODE(info.st_mode)
        if stat.S_ISDIR(info.st_mode):
            digest.update(json.dumps([relative, "directory", mode]).encode() + b"\0")
            for child in sorted(item.iterdir()):
                visit(child, f"{relative}/{child.name}")
        elif stat.S_ISREG(info.st_mode):
            digest.update(json.dumps([relative, "file", mode]).encode() + b"\0")
            digest.update(hashlib.sha256(item.read_bytes()).digest())
        else:
            raise RuntimeError(f"Unsupported symlink or special file: {item}")

    visit(path, ".")
    return digest.hexdigest()


def validate_path(path: Path) -> None:
    """Reject links in destinations and their project-local ancestors."""
    for part in [path, *path.parents]:
        if part == ROOT:
            break
        if part.is_symlink():
            raise RuntimeError(f"Symlink destination or ancestor is not supported: {part}")


def ownership(target: Path, *, allow_unowned: bool) -> dict[str, str]:
    validate_path(target)
    if not target.exists():
        return {}
    if not target.is_dir():
        raise RuntimeError(f"Expected a directory: {target}")
    fingerprint(target)
    marker = target / MARKER
    if not marker.exists():
        if any(target.iterdir()):
            raise RuntimeError(f"Existing {target.name} has no Assimilation ownership marker")
        return {}
    data = json.loads(marker.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema") != 2 or not isinstance(data.get("owned"), dict):
        raise RuntimeError(f"Legacy or invalid ownership marker in {target}; explicit recovery required")
    owned = data["owned"]
    for name, expected in owned.items():
        if (not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", name)
                or name == MARKER or not isinstance(expected, str)
                or not re.fullmatch(r"[a-f0-9]{64}", expected)):
            raise RuntimeError(f"Invalid ownership fingerprint in {marker}")
        item = target / name
        if not item.exists() or fingerprint(item) != expected:
            raise RuntimeError(f"Owned content changed: {item}; preserve and reconcile it explicitly")
    if not allow_unowned and (set(owned) != set(SOURCES) or
                             any(item.name not in {*owned, MARKER} for item in target.iterdir())):
        raise RuntimeError(f"Unknown vendor content in {target}; move or merge it explicitly")
    return owned


def write_ownership(target: Path, names: list[str]) -> None:
    data = {"schema": 2, "owned": {name: fingerprint(target / name) for name in names}}
    (target / MARKER).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def copy_source(source: Path, target: Path, *, fetched: bool = False) -> None:
    if source.is_symlink() or not source.is_dir():
        raise RuntimeError(f"Source root is not a regular directory: {source}")
    # Copy links as links so validation rejects them without reading their targets.
    shutil.copytree(source, target, symlinks=True,
                    ignore=shutil.ignore_patterns(".git") if fetched else None)
    fingerprint(target)


@dataclass
class Replacement:
    target: Path
    candidate: Path
    backup: Path
    backup_attempted: bool = False
    install_attempted: bool = False


def replace_transaction(replacements: list[Replacement]) -> None:
    """Record intent before each move and reconcile actual paths after any error."""
    try:
        for item in replacements:
            if item.target.exists():
                item.backup_attempted = True
                item.target.rename(item.backup)
        for item in replacements:
            item.install_attempted = True
            item.candidate.replace(item.target)
    except BaseException as error:
        failures = []
        for item in reversed(replacements):
            try:
                if item.install_attempted and item.target.exists():
                    if item.candidate.exists():
                        raise RuntimeError("Uncertain installation outcome: target and candidate both exist")
                    item.target.rename(item.candidate)
                if item.backup_attempted and item.backup.exists():
                    if item.target.exists():
                        raise RuntimeError("Cannot restore into an occupied destination")
                    item.backup.rename(item.target)
            except BaseException as restore_error:
                failures.append(f"{item.target}: {restore_error}; backup: {item.backup}")
        if failures:
            raise RuntimeError(f"Installation failed ({error}); rollback incomplete. "
                               "Keep and recover retained backups: " + "; ".join(failures)) from error
        raise


def install(approve_update: bool, update_plan: Path | None = None, locked: bool = False) -> None:
    guard = ROOT / ".assimilation-install.lock"
    try:
        guard.mkdir(mode=0o700)
    except FileExistsError as error:
        raise RuntimeError(f"Another installer or interrupted install owns {guard}; inspect before recovery") from error
    try:
        for parent in (ROOT, BRIDGES.parent):
            validate_path(parent)
            if parent.exists() and any(parent.glob(".assimilation-stage-*")):
                raise RuntimeError(f"Unrecovered installer staging under {parent}; inspect retained backups first")
        _install(approve_update, update_plan, locked)
    finally:
        guard.rmdir()


def _install(approve_update: bool, update_plan: Path | None, locked: bool) -> None:
    existing = read_lock().get("sources", {})
    revisions = {}
    if locked or update_plan is not None:
        if not existing:
            raise RuntimeError("A complete sources.lock.json baseline is required")
        revisions = {name: entry["sha"] for name, entry in existing.items()}
    if update_plan is not None:
        if not approve_update:
            raise RuntimeError("Applying an update plan requires --approve-update")
        if locked:
            raise RuntimeError("--locked and --update-plan are mutually exclusive")
        if update_plan.is_symlink() or not update_plan.is_file():
            raise RuntimeError("Update plan must be a regular, non-symlink file")
        plan = json.loads(update_plan.read_text(encoding="utf-8"))
        if (not isinstance(plan, dict) or plan.get("schema") != 1 or
                not isinstance(plan.get("sources"), dict) or set(plan["sources"]) != set(SOURCES)):
            raise RuntimeError("Invalid update plan: expected complete schema 1 sources")
        for name, entry in plan["sources"].items():
            if (not isinstance(entry, dict) or entry.get("from_sha") != existing[name]["sha"]
                    or not isinstance(entry.get("to_sha"), str) or not SHA_RE.fullmatch(entry["to_sha"])):
                raise RuntimeError(f"Stale or invalid update plan for {name}")
            revisions[name] = entry["to_sha"]
    materializing = locked and not VENDOR.exists() and not BRIDGES.exists()
    if existing and not approve_update and not materializing:
        raise RuntimeError("Already installed/locked. Run check, review changes, then rerun install --approve-update")

    ownership(VENDOR, allow_unowned=False)
    prior_owned = ownership(BRIDGES, allow_unowned=True)
    validate_path(LOCK)
    if LOCK.exists() and not LOCK.is_file():
        raise RuntimeError("Expected a regular sources.lock.json")
    originals = {path: fingerprint(path) if path.exists() else None for path in (VENDOR, BRIDGES, LOCK)}

    created_agents = not BRIDGES.parent.exists()
    BRIDGES.parent.mkdir(parents=True, exist_ok=True)
    stages = []
    replacements = []
    committed = False
    try:
        stage = Path(tempfile.mkdtemp(prefix=".assimilation-stage-", dir=ROOT))
        stages.append(stage)
        bridge_stage = Path(tempfile.mkdtemp(prefix=".assimilation-stage-", dir=BRIDGES.parent))
        stages.append(bridge_stage)
        vendors = stage / "vendor"
        bridges = bridge_stage / "skills"
        vendors.mkdir()
        bridges.mkdir()
        locks = {}
        total = {}
        for name, spec in SOURCES.items():
            clone = stage / f"fetch-{name}"
            sha = clone_sparse(name, clone, revisions.get(name))
            src = clone if spec["path"] == "." else clone / spec["path"]
            if not (src / spec["skill_dir"]).is_dir():
                raise RuntimeError(f"{name} missing source skill path: {spec['skill_dir']}")
            target = vendors / name
            copy_source(src, target, fetched=True)
            if name == "matt":
                # Entire engineering collection plus original productivity/reference material.
                pass
            skill_root = target / spec["skill_dir"]
            skills = sorted(p for p in skill_root.iterdir() if p.is_dir() and (p / "SKILL.md").is_file())
            if not skills:
                raise RuntimeError(f"{name} has no discoverable SKILL.md directories")
            for skill in skills:
                key = f"{spec['prefix']}-{skill.name}"
                folder = bridges / key
                folder.mkdir()
                source_path = (Path("vendor") / name / spec["skill_dir"] / skill.name / "SKILL.md").as_posix()
                folder.joinpath("SKILL.md").write_text(
                    "---\n" + f"name: {key}\n" + f"description: Entry point to the upstream {name} skill '{skill.name}'. Read full original source before use.\n" + "---\n\n" +
                    f"# {key}\n\nRead the complete original file at `{source_path}` and ALL its required references BEFORE doing the work. "
                    "Respect original invocation restrictions, prerequisites, tool capabilities and project authority. "
                    "This bridge is NOT an independent rewritten or automatically executed skill. "
                    "Read `AGENTS.md` for approval, safety, and reporting boundaries.\n",
                    encoding="utf-8")
            total[name] = len(skills)
            locks[name] = {"repository": spec["url"], "branch": spec["branch"], "sha": sha,
                           "skills_exposed": len(skills), "installed_at_utc": dt.datetime.now(dt.timezone.utc).isoformat()}

        # Make locally authored skills discoverable in the same namespaced directory.
        fingerprint(ROOT / "skills")
        for source in (ROOT / "skills").iterdir():
            if source.is_dir() and (source / "SKILL.md").is_file():
                if (bridges / source.name).exists():
                    raise RuntimeError(f"Custom skill collision: {source.name}")
                copy_source(source, bridges / source.name)

        # Preserve existing agent skills that Assimilation does not own. Never silently
        # replace an agent's unrelated tools or manually edited wrappers.
        owned = sorted(p.name for p in bridges.iterdir() if p.is_dir())
        if BRIDGES.exists():
            for item in BRIDGES.iterdir():
                if item.name == MARKER or item.name in prior_owned:
                    continue
                if (bridges / item.name).exists():
                    raise RuntimeError(f"Unmanaged .agents/skills entry conflicts with generated skill: {item.name}")
                if item.is_dir():
                    copy_source(item, bridges / item.name)
                else:
                    shutil.copy2(item, bridges / item.name, follow_symlinks=False)
        write_ownership(bridges, owned)
        write_ownership(vendors, sorted(SOURCES))
        for path, original in originals.items():
            validate_path(path)
            current = fingerprint(path) if path.exists() else None
            if current != original:
                raise RuntimeError(f"Destination changed during preparation: {path}; retry after reconciling edits")

        lock_tmp = stage / "sources.lock.json"
        if locked:
            lock_tmp.write_bytes(LOCK.read_bytes())
        else:
            lock_tmp.write_text(json.dumps({"schema": 1, "sources": locks}, indent=2) + "\n", encoding="utf-8")
        replacements = [
            Replacement(VENDOR, vendors, stage / "backup-vendor"),
            Replacement(BRIDGES, bridges, bridge_stage / "backup-skills"),
            Replacement(LOCK, lock_tmp, stage / "backup-lock"),
        ]
        replace_transaction(replacements)
        committed = True
    finally:
        # A failed restore owns its stage until a human recovers it. Never let
        # automatic temporary-directory cleanup discard the only original copy.
        for folder in stages:
            if committed or not any(item.backup.exists() and item.backup.is_relative_to(folder)
                                    for item in replacements):
                shutil.rmtree(folder)
        if created_agents and BRIDGES.parent.exists() and not any(BRIDGES.parent.iterdir()):
            BRIDGES.parent.rmdir()
    print(f"Installed {total['matt']} Matt engineering and {total['pstack']} P-Stack skill bridges.")
    print("Original source trees are in vendor/. SHA provenance is in sources.lock.json.")
    print("No upstream setup or execution script was run.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    sub = commands.add_parser("install", help="Fetch latest main and install intact source trees")
    sub.add_argument("--approve-update", action="store_true", help="Authorize replacing an existing reviewed local installation")
    sub.add_argument("--update-plan", type=Path, help="Apply exact reviewed revisions from a source update plan")
    sub.add_argument("--locked", action="store_true", help="Materialize exact revisions from sources.lock.json")
    commands.add_parser("check", help="Read-only SHA comparison; exit 2 on updates, 3 without a baseline")
    args = parser.parse_args()
    try:
        if args.command == "check":
            return check()
        install(args.approve_update, args.update_plan, args.locked)
        return 0
    except (RuntimeError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
