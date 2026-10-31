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
from pathlib import Path, PureWindowsPath
import re
import shutil
import stat
import sys
import tempfile
import git_runtime

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


def require_supported_runtime() -> None:
    """Eligibility only; actual mode, content, link and ownership checks still apply."""
    if os.name != "posix":
        raise RuntimeError(
            "Unsupported runtime: source operations require POSIX file modes and literal symlink preservation. "
            "Native Windows guarantees are not established; no source operation started.")


def git(*args: str, cwd: Path | None = None, capture: bool = True) -> str:
    return git_runtime.run(*args, cwd=cwd, capture=capture).decode("utf-8").strip()


def effective_source(name: str) -> str:
    if name not in SOURCES:
        raise RuntimeError("Unknown source")
    official = SOURCES[name]["url"]
    selected = os.environ.get(f"ASSIMILATION_{name.upper()}_SOURCE", official)
    if selected == official:
        return official
    if not selected or len(selected) > 4096 or any(ord(char) < 32 for char in selected):
        raise RuntimeError("Invalid source mirror")
    # Overrides are local filesystem mirrors, never credential-bearing URLs,
    # scp syntax, remote helpers or alternate network authorities.
    if "://" in selected or "::" in selected or (":" in selected and not (os.name == "nt" and PureWindowsPath(selected).drive)):
        raise RuntimeError("Source overrides support local filesystem mirrors only")
    return str(Path(selected).absolute())


def source_acquisition(name: str) -> dict[str, str]:
    selected = effective_source(name)
    kind = "official-https" if selected == SOURCES[name]["url"] else "operator-local-mirror"
    return {"kind": kind, "source_sha256": hashlib.sha256(selected.encode("utf-8")).hexdigest()}


def head(name: str) -> str:
    spec = SOURCES[name]
    # No source comparison runs in a caller-controlled repository context.
    with tempfile.TemporaryDirectory(prefix="assimilation-source-head-") as directory:
        repo = Path(directory)
        git("init", "--bare", "--quiet", cwd=repo)
        value = git("ls-remote", effective_source(name), f"refs/heads/{spec['branch']}", cwd=repo)
    if not value:
        raise RuntimeError(f"Could not locate {name} branch {spec['branch']}")
    sha = value.split()[0]
    if not SHA_RE.fullmatch(sha):
        raise RuntimeError(f"Unrecognized {name} commit SHA")
    return sha


def read_lock() -> dict:
    require_supported_runtime()
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
    # Build a fresh repository before any remote operation. Unlike clone from
    # the caller's cwd, fetch here cannot load that caller's local Git config.
    git("init", "--quiet", str(dest))
    git("remote", "add", "origin", effective_source(name), cwd=dest)
    git("sparse-checkout", "init", "--cone", cwd=dest)
    git("sparse-checkout", "set", *spec["sparse"], cwd=dest)
    git("fetch", "--quiet", "--depth", "1", "--filter=blob:none", "origin",
        revision if revision is not None else f"refs/heads/{spec['branch']}", cwd=dest)
    git("checkout", "--quiet", "--detach", "FETCH_HEAD", cwd=dest)
    sha = git("rev-parse", "HEAD", cwd=dest)
    if not SHA_RE.fullmatch(sha) or (revision is not None and sha != revision):
        raise RuntimeError("Could not verify exact checkout hash")
    return sha


def contained_link_file(link: Path, source_root: Path) -> Path:
    """Resolve relative file links without traversing outside a fetched collection."""
    seen = set()
    while link not in seen:
        seen.add(link)
        spelling = os.readlink(link)
        if (Path(spelling).is_absolute() or PureWindowsPath(spelling).drive
                or "\\" in spelling or spelling.endswith("/")):
            raise RuntimeError(f"Unsupported absolute or directory-form symlink: {link}")
        cursor = link.parent
        parts = spelling.split("/")
        for index, part in enumerate(parts):
            if part in ("", "."):
                continue
            if part == "..":
                if cursor == source_root:
                    raise RuntimeError(f"Escaping source symlink: {link}")
                cursor = cursor.parent
                continue
            cursor = cursor / part
            info = cursor.lstat()
            if is_reparse_point(info) and not stat.S_ISLNK(info.st_mode):
                raise RuntimeError("Unsupported source reparse point")
            if index != len(parts) - 1:
                if not stat.S_ISDIR(info.st_mode):
                    raise RuntimeError(f"Symlink target traverses a non-directory or directory link: {link}")
            elif stat.S_ISREG(info.st_mode):
                return cursor
            elif stat.S_ISLNK(info.st_mode):
                link = cursor
                break
            else:
                raise RuntimeError(f"Symlink target is not a regular file: {link}")
        else:
            raise RuntimeError(f"Symlink target is a directory: {link}")
    raise RuntimeError(f"Cyclic source symlink: {link}")


def fingerprint(path: Path, *, file_link_roots: tuple[Path, ...] = (),
                exclude_git: bool = False) -> str:
    """Hash complete trees; only explicitly scoped fetched collections permit file links."""
    digest = hashlib.sha256()

    def visit(item: Path, relative: str) -> None:
        info = item.lstat()
        mode = stat.S_IMODE(info.st_mode)
        if is_reparse_point(info) and not stat.S_ISLNK(info.st_mode):
            raise RuntimeError("Unsupported source reparse point")
        if stat.S_ISDIR(info.st_mode):
            digest.update(json.dumps([relative, "directory", mode]).encode() + b"\0")
            for child in sorted(item.iterdir()):
                if exclude_git and child.name == ".git":
                    continue
                visit(child, f"{relative}/{child.name}")
        elif stat.S_ISREG(info.st_mode):
            digest.update(json.dumps([relative, "file", mode]).encode() + b"\0")
            digest.update(hashlib.sha256(item.read_bytes()).digest())
        elif stat.S_ISLNK(info.st_mode):
            root = next((root for root in file_link_roots if item != root and item.is_relative_to(root)), None)
            if root is None:
                raise RuntimeError(f"Unsupported symlink or special file: {item}")
            target = contained_link_file(item, root)
            digest.update(json.dumps([relative, "symlink", mode, os.readlink(item),
                                      stat.S_IMODE(target.lstat().st_mode)]).encode() + b"\0")
            digest.update(hashlib.sha256(target.read_bytes()).digest())
        else:
            raise RuntimeError(f"Unsupported symlink or special file: {item}")

    visit(path, ".")
    return digest.hexdigest()


def is_reparse_point(info) -> bool:
    """Recognize Windows reparse metadata, including on the Python 3.10 floor."""
    return bool(getattr(info, "st_file_attributes", 0)
                & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))


def validate_path(path: Path) -> None:
    """Reject escapes and links/reparse points in project destinations."""
    if ".." in path.parts or not path.absolute().is_relative_to(ROOT):
        raise RuntimeError("Destination is outside the project")
    for part in (path, *path.parents):
        try:
            info = part.lstat()
        except FileNotFoundError:
            info = None
        if info is not None and (stat.S_ISLNK(info.st_mode) or is_reparse_point(info)):
            raise RuntimeError("Symlink or reparse destination/ancestor is not supported")
        if part == ROOT:
            break


def ownership(target: Path, *, allow_unowned: bool) -> dict[str, str]:
    validate_path(target)
    if not target.exists():
        return {}
    if not target.is_dir():
        raise RuntimeError(f"Expected a directory: {target}")
    source_roots = tuple(target / name for name in SOURCES) if not allow_unowned else ()
    fingerprint(target, file_link_roots=source_roots)
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
        if not item.exists() or fingerprint(item, file_link_roots=source_roots) != expected:
            raise RuntimeError(f"Owned content changed: {item}; preserve and reconcile it explicitly")
    if not allow_unowned and (set(owned) != set(SOURCES) or
                             any(item.name not in {*owned, MARKER} for item in target.iterdir())):
        raise RuntimeError(f"Unknown vendor content in {target}; move or merge it explicitly")
    return owned


def write_ownership(target: Path, names: list[str], *, fetched: bool = False) -> None:
    data = {"schema": 2, "owned": {
        name: fingerprint(target / name, file_link_roots=(target / name,) if fetched else ()) for name in names}}
    (target / MARKER).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def copy_source(source: Path, target: Path, *, fetched: bool = False) -> None:
    if source.is_symlink() or not source.is_dir():
        raise RuntimeError(f"Source root is not a regular directory: {source}")
    # Validate the source before copytree can follow a junction and erase its
    # reparse metadata. Exclude precisely the Git metadata copytree also ignores.
    fingerprint(source, file_link_roots=(source,) if fetched else (), exclude_git=fetched)
    # Preserve link spelling; validate scoped targets before reading their bytes.
    shutil.copytree(source, target, symlinks=True,
                    ignore=shutil.ignore_patterns(".git") if fetched else None)
    fingerprint(target, file_link_roots=(target,) if fetched else ())


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


def metadata_blocks(text: str) -> dict[str, tuple[str, list[str]]]:
    """Read a deliberately bounded YAML mapping; refuse ambiguous structures.

    This is not a general YAML loader. Nested blocks remain opaque until their
    owning field validates them. Quoted simple keys and comments are supported.
    """
    result = {}
    current = None
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if "\t" in line:
            raise RuntimeError("Unsupported tab in skill metadata")
        if line.startswith(" "):
            if current is None:
                raise RuntimeError("Detached skill metadata block")
            result[current][1].append(line)
            continue
        matched = re.fullmatch(r'''(?:([A-Za-z][\w-]*)|'([A-Za-z][\w-]*)'|"([A-Za-z][\w-]*)"):\s*(.*)''', line)
        if not matched:
            raise RuntimeError("Unsupported skill metadata mapping syntax")
        key = next(value for value in matched.groups()[:3] if value is not None)
        if key in result:
            raise RuntimeError(f"Duplicate skill metadata key: {key}")
        result[key] = (matched[4], [])
        current = key
    return result


def metadata_bool(value: tuple[str, list[str]]) -> bool:
    scalar, children = value
    matched = re.fullmatch(r"(true|false)\s*(?:#.*)?", scalar, re.I)
    if children or not matched:
        raise RuntimeError("Skill invocation policy must be an unambiguous boolean")
    return matched[1].lower() == "true"


def metadata_string(value: str) -> str:
    value = value.strip()
    if value.startswith('"'):
        try:
            parsed = json.loads(value)
        except ValueError:
            raise RuntimeError("Unsupported quoted skill metadata value") from None
        if isinstance(parsed, str):
            return parsed
    elif value.startswith("'") and value.endswith("'"):
        inner = value[1:-1]
        if "'" not in inner.replace("''", ""):
            return inner.replace("''", "'")
    elif (re.fullmatch(r"[A-Za-z_./][A-Za-z0-9_./() :*?=,~-]*", value)
          and value.lower() not in {"null", "true", "false", "yes", "no", "on", "off"}
          and not re.search(r":(?:\s|$)", value)):
        return value
    raise RuntimeError("Unsupported skill metadata string; review its syntax")


def metadata_scope(value: tuple[str, list[str]]) -> str | list[str]:
    scalar, children = value
    if not scalar or scalar.startswith("#"):
        if not children:
            raise RuntimeError("Empty skill scope declaration")
        items = []
        for line in children:
            matched = re.fullmatch(r"  - (.+)", line)
            if not matched:
                raise RuntimeError("Unsupported skill scope list")
            items.append(metadata_string(matched[1]))
        return items
    if children:
        raise RuntimeError("Ambiguous skill scope declaration")
    if scalar.startswith("[") and scalar.endswith("]"):
        try:
            parsed = json.loads(scalar)
        except ValueError:
            inner = scalar[1:-1].strip()
            return [metadata_string(part) for part in inner.split(",")] if inner else []
        if isinstance(parsed, list) and all(isinstance(item, str) for item in parsed):
            return parsed
        raise RuntimeError("Skill scope list must contain only strings")
    return metadata_string(scalar)


def bridge_policy(skill: Path) -> tuple[str, bool]:
    """Preserve supported host restrictions without activating source tooling."""
    lines = (skill / "SKILL.md").read_text(encoding="utf-8-sig").splitlines()
    if not lines or lines[0] != "---":
        fields = {}  # Legacy plain-text sources declare no frontmatter policy.
    else:
        if "---" not in lines[1:]:
            raise RuntimeError("Skill metadata delimiter is incomplete")
        fields = metadata_blocks("\n".join(lines[1:lines.index("---", 1)]))
    for key in ("name", "description", "icon", "color"):
        if key in fields:
            scalar, children = fields[key]
            if children and not (key == "description" and scalar in {">", ">-", ">+", "|", "|-", "|+"}):
                raise RuntimeError("Unsupported nested skill metadata scalar")
    supported = {"name", "description", "metadata", "icon", "color", "paths",
                 "disable-model-invocation", "user-invocable", "allowed-tools"}
    if set(fields) - supported:
        raise RuntimeError("Unsupported skill metadata key; review before bridge activation")
    disabled = metadata_bool(fields["disable-model-invocation"]) if "disable-model-invocation" in fields else None
    implicit = None
    sidecar = skill / "agents/openai.yaml"
    if sidecar.exists():
        host_fields = metadata_blocks(sidecar.read_text(encoding="utf-8-sig"))
        if set(host_fields) - {"interface", "policy"}:
            raise RuntimeError("Unsupported host metadata; no dependencies are activated by a bridge")
        if "policy" in host_fields:
            scalar, children = host_fields["policy"]
            if scalar and not scalar.startswith("#"):
                raise RuntimeError("Unsupported host policy mapping")
            if any(not line.startswith("  ") for line in children):
                raise RuntimeError("Unsupported host policy indentation")
            policy = metadata_blocks("\n".join(line[2:] for line in children))
            if set(policy) != {"allow_implicit_invocation"}:
                raise RuntimeError("Unsupported host invocation policy")
            implicit = metadata_bool(policy["allow_implicit_invocation"])
    if disabled is not None and implicit is not None and disabled == implicit:
        raise RuntimeError("Conflicting host invocation policies; reconcile the source")
    restricted = disabled is True or implicit is False
    declarations = []
    if disabled is not None or restricted:
        declarations.append(f"disable-model-invocation: {'true' if restricted else 'false'}\n")
    if "user-invocable" in fields:
        visible = metadata_bool(fields["user-invocable"])
        declarations.append(f"user-invocable: {'true' if visible else 'false'}\n")
    for key in ("allowed-tools", "paths"):
        if key in fields:
            value = metadata_scope(fields[key])
            if isinstance(value, list):
                declarations.append(key + ":\n" + "".join("  - " + json.dumps(item) + "\n" for item in value)
                                    if value else key + ": []\n")
            else:
                declarations.append(key + ": " + json.dumps(value) + "\n")
    return "".join(declarations), restricted


def install(approve_update: bool, update_plan: Path | None = None, locked: bool = False) -> None:
    require_supported_runtime()
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
    source_roots = tuple(VENDOR / name for name in SOURCES)
    originals = {path: fingerprint(path, file_link_roots=source_roots if path == VENDOR else ())
                 if path.exists() else None for path in (VENDOR, BRIDGES, LOCK)}

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
                if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", skill.name):
                    raise RuntimeError("Unsupported skill directory name")
                declarations, restricted = bridge_policy(skill)
                key = f"{spec['prefix']}-{skill.name}"
                folder = bridges / key
                folder.mkdir()
                source_path = (Path("vendor") / name / spec["skill_dir"] / skill.name / "SKILL.md").as_posix()
                folder.joinpath("SKILL.md").write_text(
                    "---\n" + f"name: {key}\n" + f"description: Entry point to the upstream {name} skill '{skill.name}'. Read full original source before use.\n" + declarations + "---\n\n" +
                    f"# {key}\n\nRead the complete original file at `{source_path}` and ALL its required references BEFORE doing the work. "
                    "Respect original invocation restrictions, prerequisites, tool capabilities and project authority. "
                    "This bridge is NOT an independent rewritten or automatically executed skill. "
                    "Read `AGENTS.md` for approval, safety, and reporting boundaries.\n",
                    encoding="utf-8")
                if restricted:
                    (folder / "agents").mkdir()
                    (folder / "agents/openai.yaml").write_text(
                        "policy:\n  allow_implicit_invocation: false\n", encoding="utf-8")
            total[name] = len(skills)
            locks[name] = {"repository": spec["url"], "branch": spec["branch"], "sha": sha,
                           "acquisition": source_acquisition(name),
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
        write_ownership(vendors, sorted(SOURCES), fetched=True)
        for path, original in originals.items():
            validate_path(path)
            current = (fingerprint(path, file_link_roots=source_roots if path == VENDOR else ())
                       if path.exists() else None)
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
