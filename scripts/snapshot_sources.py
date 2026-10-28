#!/usr/bin/env python3
"""Materialize and verify complete, inert upstream snapshots at exact locked commits."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path, PureWindowsPath
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import unicodedata

import skills

ROOT = skills.ROOT
MANIFEST = "sources.snapshot.json"
LAYOUT = {"matt": ("upstream/matt-pocock", "."), "pstack": ("upstream/pstack", "pstack")}
APPROVED_LICENSES = {
    "matt": "0e7ac423bf2c6e223b7c5b156f8cf72da49d748e56a1641402c31f22ad07dbb5",
    "pstack": "bc957ca6bee02792566a1a028d105e02e247c6e77cf057061674273da77b200e",
}
MODES = {"100644", "100755", "120000"}
STAGE = ".assimilation-snapshot-stage-"
MAX_FILES = 10_000
MAX_BLOB_BYTES = 16 * 1024 * 1024
MAX_TOTAL_BYTES = 128 * 1024 * 1024
MAX_MANIFEST_BYTES = 32 * 1024 * 1024


def serialized(value: dict) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2) + "\n").encode("utf-8")


def object_sha(kind: str, data: bytes) -> str:
    return hashlib.sha1(kind.encode() + b" " + str(len(data)).encode() + b"\0" + data).hexdigest()


def regular_path(path: Path) -> None:
    if ".." in path.parts:
        raise RuntimeError(f"Traversal path is not supported: {path}")
    for part in (path, *path.parents):
        if part.is_symlink():
            raise RuntimeError(f"Symlink destination or ancestor is not supported: {part}")


def read_pins(root: Path) -> dict:
    path = root / "sources.lock.json"
    regular_path(path)
    if not path.is_file() or stat.S_IMODE(path.stat().st_mode) != 0o644:
        raise RuntimeError("A complete regular non-executable sources.lock.json baseline is required")
    if path.stat().st_size > 2_000_000:
        raise RuntimeError("Source lock exceeds the supported metadata limit")
    data = json.loads(path.read_bytes())
    if (not isinstance(data, dict) or data.get("schema") != 1 or
            not isinstance(data.get("sources"), dict) or set(data["sources"]) != set(LAYOUT)):
        raise RuntimeError("Invalid source lock schema or source set")
    for name, entry in data["sources"].items():
        if (not isinstance(entry, dict) or entry.get("repository") != skills.SOURCES[name]["url"] or
                entry.get("branch") != "main" or not isinstance(entry.get("sha"), str) or
                not skills.SHA_RE.fullmatch(entry["sha"])):
            raise RuntimeError(f"Invalid source pin: {name}")
    return data["sources"]


def safe_path(value: str) -> tuple[str, ...]:
    if not isinstance(value, str) or not value or value.startswith("/") or "\\" in value or PureWindowsPath(value).drive:
        raise RuntimeError(f"Unsafe source path: {value!r}")
    parts = value.split("/")
    for part in parts:
        if (part in {"", ".", ".."} or part.endswith((".", " ")) or
                any(char in '<>:"|?*' or unicodedata.category(char).startswith("C") for char in part) or
                unicodedata.normalize("NFC", part) != part or
                re.fullmatch(r"(?i)(?:\.git|\.?git~[0-9]+)", part) or
                re.fullmatch(r"(?i)(?:con|prn|aux|nul|com[1-9¹²³]|lpt[1-9¹²³])(?:\..*)?", part)):
            raise RuntimeError(f"Unsafe source path component: {part!r}")
    return tuple(parts)


def tree_sha(files: dict) -> str:
    """Rebuild Git's exact tree objects from validated path/mode/blob tuples."""
    if not files or len(files) > MAX_FILES:
        raise RuntimeError("Source file count exceeds supported snapshot bounds")
    root = {}
    spellings = {}
    for path, entry in files.items():
        parts = safe_path(path)
        review_content("source path", path.encode("utf-8"))
        for index in range(1, len(parts) + 1):
            prefix = "/".join(parts[:index])
            previous = spellings.setdefault(prefix.casefold(), prefix)
            if previous != prefix:
                raise RuntimeError("Case-insensitive source path collision")
        if (not isinstance(entry, dict) or entry.get("mode") not in MODES or
                not isinstance(entry.get("git_blob_sha"), str) or not skills.SHA_RE.fullmatch(entry["git_blob_sha"])):
            raise RuntimeError(f"Unsupported source mode or blob: {path}")
        node = root
        for part in parts[:-1]:
            node = node.setdefault(part, {})
            if not isinstance(node, dict):
                raise RuntimeError("Source file/directory collision")
        if parts[-1] in node:
            raise RuntimeError("Duplicate or colliding source path")
        node[parts[-1]] = (entry["mode"], entry["git_blob_sha"])

    def encode(node):
        result = bytearray()
        for name, value in sorted(node.items(), key=lambda pair: pair[0].encode("utf-8") + (b"/" if isinstance(pair[1], dict) else b"")):
            mode, oid = ("40000", encode(value)) if isinstance(value, dict) else value
            result.extend(mode.encode() + b" " + name.encode("utf-8") + b"\0" + bytes.fromhex(oid))
        return object_sha("tree", bytes(result))

    return encode(root)


def root_tree_entries(raw: bytes) -> dict[bytes, tuple[bytes, str]]:
    entries = {}
    offset = 0
    while offset < len(raw):
        space, nul = raw.index(b" ", offset), raw.index(b"\0", offset)
        mode, name = raw[offset:space], raw[space + 1:nul]
        end = nul + 21
        if not name or name in entries or end > len(raw):
            raise RuntimeError("Invalid root tree proof")
        entries[name] = (mode, raw[nul + 1:end].hex())
        offset = end
    return entries


def proof_bytes(value: str) -> bytes:
    if not isinstance(value, str) or len(value) > 2_000_000:
        raise RuntimeError("Invalid or oversized Git object proof")
    return base64.b64decode(value, validate=True)


def validate_proof(name: str, source: dict, pin: dict | None = None) -> None:
    expected = {"directory", "repository", "commit_sha", "root_tree_sha", "scope", "scope_tree_sha", "commit_object", "root_tree_object", "files"}
    if not isinstance(source, dict) or set(source) != expected:
        raise RuntimeError(f"Invalid snapshot source schema: {name}")
    directory, scope = LAYOUT[name]
    if (source["directory"] != directory or source["scope"] != scope or
            source["repository"] != skills.SOURCES[name]["url"] or not isinstance(source["files"], dict)):
        raise RuntimeError(f"Snapshot source scope changed: {name}")
    for key in ("commit_sha", "root_tree_sha", "scope_tree_sha"):
        if not isinstance(source[key], str) or not skills.SHA_RE.fullmatch(source[key]):
            raise RuntimeError(f"Invalid snapshot Git object identity: {name}")
    commit = proof_bytes(source["commit_object"])
    raw_tree = proof_bytes(source["root_tree_object"])
    review_content(f"{name} commit provenance", commit)
    review_content(f"{name} root-tree provenance", raw_tree)
    if (object_sha("commit", commit) != source["commit_sha"] or
            commit.split(b"\n", 1)[0] != b"tree " + source["root_tree_sha"].encode() or
            object_sha("tree", raw_tree) != source["root_tree_sha"]):
        raise RuntimeError(f"Invalid commit/tree provenance proof: {name}")
    scoped = source["root_tree_sha"] if scope == "." else root_tree_entries(raw_tree).get(b"pstack", (None, None))[1]
    if (scope != "." and root_tree_entries(raw_tree).get(b"pstack", (None, None))[0] != b"40000"):
        raise RuntimeError("P-Stack scope is not a Git directory")
    if scoped != source["scope_tree_sha"] or tree_sha(source["files"]) != scoped:
        raise RuntimeError(f"Snapshot files do not reproduce the pinned Git tree: {name}")
    if pin is not None and source["commit_sha"] != pin["sha"]:
        raise RuntimeError(f"Source snapshot and lock mismatch: {name}")
    licenses = {path: entry.get("sha256") for path, entry in source["files"].items()
                if re.fullmatch(r"(?i)(?:licen[cs]e|copying|notice)(?:[._-].*)?", path.rsplit("/", 1)[-1])}
    if licenses != {"LICENSE": APPROVED_LICENSES[name]} or source["files"]["LICENSE"]["mode"] != "100644":
        raise RuntimeError(f"Unexpected license inventory or bytes: {name}; human review required")
    for path, entry in source["files"].items():
        if (set(entry) != {"mode", "git_blob_sha", "sha256", "size"} or
                not isinstance(entry["sha256"], str) or not re.fullmatch(r"[a-f0-9]{64}", entry["sha256"]) or
                type(entry["size"]) is not int or not 0 <= entry["size"] <= MAX_BLOB_BYTES):
            raise RuntimeError(f"Invalid source blob metadata: {path}")


def review_content(path: str, raw: bytes) -> None:
    patterns = (
        rb"-----BEGIN (?:[A-Z]+ )*PRIVATE KEY-----",
        rb"-----BEGIN PGP PRIVATE KEY BLOCK-----",
        rb"(?<![A-Za-z0-9_])gh[pousr]_[A-Za-z0-9]{36,255}(?![A-Za-z0-9_])",
        rb"(?<![A-Za-z0-9_])github_pat_[A-Za-z0-9_]{82,255}(?![A-Za-z0-9_])",
    )
    if any(re.search(pattern, raw) for pattern in patterns):
        raise RuntimeError(f"Potential credential/private-key material in {path}; "
                           f"SHA256 {hashlib.sha256(raw).hexdigest()}; human review required")


def file_bytes(path: Path, mode: str) -> bytes:
    info = path.lstat()
    if info.st_size > MAX_BLOB_BYTES:
        raise RuntimeError(f"Source blob exceeds the supported size limit: {path}")
    if mode == "120000":
        if not stat.S_ISLNK(info.st_mode):
            raise RuntimeError(f"Expected source symlink: {path}")
        return os.fsencode(os.readlink(path))
    if not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) != (0o755 if mode == "100755" else 0o644):
        raise RuntimeError(f"Changed source file type or mode: {path}")
    return path.read_bytes()


def verify_tree(root: Path, files: dict) -> None:
    regular_path(root)
    if not root.is_dir():
        raise RuntimeError(f"Missing source directory: {root}")
    expected_dirs = {"."}
    for path in files:
        expected_dirs.update(str(parent) for parent in Path(path).parents)
    actual_files, actual_dirs = set(), set()

    def walk(directory: Path):
        actual_dirs.add(directory.relative_to(root).as_posix())
        if stat.S_IMODE(directory.stat().st_mode) != 0o755:
            raise RuntimeError(f"Changed source directory mode: {directory}")
        for item in directory.iterdir():
            info = item.lstat()
            if stat.S_ISDIR(info.st_mode):
                walk(item)
            else:
                actual_files.add(item.relative_to(root).as_posix())

    walk(root)
    if actual_files != set(files) or actual_dirs != expected_dirs:
        raise RuntimeError(f"Unknown, missing, or edited source entries in {root}")
    # Validate link containment before reading any source payloads.
    for path, entry in files.items():
        item = root / path
        if entry["mode"] == "120000":
            if not item.is_symlink():
                raise RuntimeError(f"Expected source symlink: {item}")
            skills.contained_link_file(item, root)
        elif item.is_symlink():
            raise RuntimeError(f"Unexpected source symlink: {item}")
    for path, entry in files.items():
        raw = file_bytes(root / path, entry["mode"])
        review_content(path, raw)
        if (len(raw) != entry["size"] or hashlib.sha256(raw).hexdigest() != entry["sha256"] or
                object_sha("blob", raw) != entry["git_blob_sha"]):
            raise RuntimeError(f"Changed source content: {root / path}")


def verify(root: Path = ROOT) -> dict:
    root = root.absolute()
    path = root / MANIFEST
    regular_path(path)
    if not path.is_file() or stat.S_IMODE(path.stat().st_mode) != 0o644:
        raise RuntimeError("A regular non-executable source snapshot manifest is required")
    if path.stat().st_size > MAX_MANIFEST_BYTES:
        raise RuntimeError("Snapshot manifest exceeds the supported size limit")
    manifest = json.loads(path.read_bytes())
    if (not isinstance(manifest, dict) or set(manifest) != {"schema", "sources"} or manifest["schema"] != 1 or
            not isinstance(manifest["sources"], dict) or set(manifest["sources"]) != set(LAYOUT)):
        raise RuntimeError("Invalid snapshot manifest schema")
    pins = read_pins(root)
    for name, source in manifest["sources"].items():
        validate_proof(name, source, pins[name])
    if sum(entry["size"] for source in manifest["sources"].values() for entry in source["files"].values()) > MAX_TOTAL_BYTES:
        raise RuntimeError("Snapshot aggregate source size exceeds the supported limit")
    for source in manifest["sources"].values():
        verify_tree(root / source["directory"], source["files"])
    return manifest


def package_files(root: Path) -> dict:
    manifest = verify(root)
    files = {name: {"mode": "100644", "content": file_bytes(root / name, "100644")}
             for name in ("sources.lock.json", MANIFEST)}
    for source in manifest["sources"].values():
        for path, entry in source["files"].items():
            relative = source["directory"] + "/" + path
            files[relative] = {"mode": entry["mode"], "content": file_bytes(root / relative, entry["mode"])}
    return files


def git_bytes(repo: Path, *args: str, input_bytes: bytes | None = None) -> bytes:
    # Public exact objects need no credential helper, host config, repository-path
    # overrides, SSH command, template hook, or executable external transport.
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    protocols = {"https", "file"}
    if "GIT_ALLOW_PROTOCOL" in os.environ:
        protocols &= set(os.environ["GIT_ALLOW_PROTOCOL"].split(":"))
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_SYSTEM=os.devnull, GIT_CONFIG_GLOBAL=os.devnull,
               GIT_ATTR_NOSYSTEM="1", GIT_TERMINAL_PROMPT="0", GIT_ALLOW_PROTOCOL=":".join(sorted(protocols)))
    process = subprocess.run(["git", "-c", f"core.hooksPath={os.devnull}", "-c", "init.templateDir=",
                              "-c", "credential.helper=", *args], cwd=repo, env=env, input=input_bytes,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if process.returncode:
        raise RuntimeError(f"Snapshot Git {args[0]} failed; no source changes adopted")
    return process.stdout


def head(name: str) -> str:
    """Compare the official branch without loading the caller's repository config."""
    if name not in LAYOUT:
        raise RuntimeError("Unknown snapshot source")
    with tempfile.TemporaryDirectory(prefix="assimilation-source-head-") as directory:
        repo = Path(directory)
        git_bytes(repo, "init", "--bare", "--quiet")
        raw = git_bytes(repo, "ls-remote", skills.effective_source(name), "refs/heads/main")
    fields = raw.decode("ascii").strip().split()
    if len(fields) != 2 or not skills.SHA_RE.fullmatch(fields[0]) or fields[1] != "refs/heads/main":
        raise RuntimeError(f"Invalid source branch response: {name}")
    return fields[0]


def source_snapshot(name: str, pin: dict, repo: Path, destination: Path, remaining_bytes: int) -> dict:
    repo.mkdir()
    git_bytes(repo, "init", "--bare", "--quiet")
    git_bytes(repo, "remote", "add", "origin", skills.effective_source(name))
    git_bytes(repo, "fetch", "--quiet", "--no-tags", "--depth=1", "--filter=blob:none", "origin", pin["sha"])
    commit = git_bytes(repo, "cat-file", "commit", pin["sha"])
    root_tree = git_bytes(repo, "rev-parse", pin["sha"] + "^{tree}").decode().strip()
    directory, scope = LAYOUT[name]
    scoped = root_tree if scope == "." else git_bytes(repo, "rev-parse", pin["sha"] + ":" + scope).decode().strip()
    files = {}
    for record in git_bytes(repo, "ls-tree", "-r", "-z", scoped).split(b"\0"):
        if not record:
            continue
        header, raw_path = record.split(b"\t", 1)
        mode, kind, oid = header.decode("ascii").split()
        path = raw_path.decode("utf-8")
        if kind != "blob" or path in files:
            raise RuntimeError("Submodules or duplicate paths are not supported in source snapshots")
        files[path] = {"mode": mode, "git_blob_sha": oid}
    if tree_sha(files) != scoped:
        raise RuntimeError("Source listing does not reproduce the complete selected Git tree")
    # Fetch selected blobs in a single request rather than hundreds of lazy network fetches.
    wants = "".join(oid + "\n" for oid in sorted({entry["git_blob_sha"] for entry in files.values()})).encode()
    git_bytes(repo, "fetch", "--quiet", "--no-tags", "--no-write-fetch-head", "--recurse-submodules=no",
              "--filter=blob:none", "origin", "--stdin", input_bytes=wants)
    sizes = {}
    for line in git_bytes(repo, "cat-file", "--batch-check=%(objectname) %(objecttype) %(objectsize)", input_bytes=wants).splitlines():
        oid, kind, size = line.decode("ascii").split()
        if kind != "blob" or not size.isdecimal() or int(size) > MAX_BLOB_BYTES:
            raise RuntimeError("Fetched source object exceeds the supported blob size/type limit")
        sizes[oid] = int(size)
    if set(sizes) != {entry["git_blob_sha"] for entry in files.values()} or sum(sizes[entry["git_blob_sha"]] for entry in files.values()) > remaining_bytes:
        raise RuntimeError("Snapshot aggregate source size exceeds the supported limit")
    payloads = {}
    for path, entry in files.items():
        raw = git_bytes(repo, "cat-file", "blob", entry["git_blob_sha"])
        if object_sha("blob", raw) != entry["git_blob_sha"]:
            raise RuntimeError("Git source blob identity mismatch")
        review_content(path, raw)
        entry.update(sha256=hashlib.sha256(raw).hexdigest(), size=len(raw))
        payloads[path] = raw
    source = {"directory": directory, "repository": skills.SOURCES[name]["url"], "commit_sha": pin["sha"],
              "root_tree_sha": root_tree, "scope": scope, "scope_tree_sha": scoped,
              "commit_object": base64.b64encode(commit).decode(),
              "root_tree_object": base64.b64encode(git_bytes(repo, "cat-file", "tree", root_tree)).decode(), "files": files}
    validate_proof(name, source, pin)
    destination.mkdir(parents=True, mode=0o755)
    destination.chmod(0o755)
    for path, entry in files.items():
        target = destination / path
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
        if entry["mode"] == "120000":
            target.symlink_to(os.fsdecode(payloads[path]))
        else:
            target.write_bytes(payloads[path])
            target.chmod(0o755 if entry["mode"] == "100755" else 0o644)
    for parent in destination.rglob("*"):
        if not parent.is_symlink() and parent.is_dir():
            parent.chmod(0o755)
    verify_tree(destination, files)
    return source


def build_package(output: Path, pins: dict, fetch_root: Path) -> dict:
    manifest = {"schema": 1, "sources": {}}
    remaining = MAX_TOTAL_BYTES
    for name, pin in pins.items():
        source = source_snapshot(name, pin, fetch_root / name, output / LAYOUT[name][0], remaining)
        manifest["sources"][name] = source
        remaining -= sum(entry["size"] for entry in source["files"].values())
    (output / MANIFEST).write_bytes(serialized(manifest))
    (output / MANIFEST).chmod(0o644)
    return manifest


def refresh(approve_update: bool) -> dict:
    guard = ROOT / ".assimilation-install.lock"
    try:
        guard.mkdir(mode=0o700)
    except FileExistsError as error:
        raise RuntimeError("Another installer or snapshot operation owns the shared guard; inspect before recovery") from error
    stages, replacements = [], []
    committed = False
    created_upstream = not (ROOT / "upstream").exists()
    try:
        for parent in (ROOT, ROOT / "upstream"):
            regular_path(parent)
            if parent.exists() and any(parent.glob(STAGE + "*")):
                raise RuntimeError("Retained snapshot stages require recovery before retry")
        pins = read_pins(ROOT)
        lock_fingerprint = skills.fingerprint(ROOT / "sources.lock.json")
        manifest_path = ROOT / MANIFEST
        regular_path(manifest_path)
        targets = [ROOT / layout[0] for layout in LAYOUT.values()]
        if manifest_path.exists():
            verify(ROOT)
            if not approve_update:
                raise RuntimeError("Existing snapshots require --approve-update after source review")
        elif any(target.exists() or target.is_symlink() for target in targets):
            raise RuntimeError("Existing source directories have no ownership manifest")
        before = {target: skills.fingerprint(target, file_link_roots=(target,)) if target.exists() else None
                  for target in targets}
        old_manifest = skills.fingerprint(manifest_path) if manifest_path.exists() else None
        (ROOT / "upstream").mkdir(exist_ok=True)
        outer = Path(tempfile.mkdtemp(prefix=STAGE, dir=ROOT))
        stages.append(outer)
        source_stage = Path(tempfile.mkdtemp(prefix=STAGE, dir=ROOT / "upstream"))
        stages.append(source_stage)
        package = source_stage / "package"
        package.mkdir()
        fetch_root = outer / "fetch"
        fetch_root.mkdir()
        manifest = build_package(package, pins, fetch_root)
        candidate_manifest = outer / MANIFEST
        candidate_manifest.write_bytes((package / MANIFEST).read_bytes())
        candidate_manifest.chmod(0o644)
        for target, fingerprint in before.items():
            regular_path(target)
            current = skills.fingerprint(target, file_link_roots=(target,)) if target.exists() else None
            if current != fingerprint:
                raise RuntimeError("Snapshot destination changed during preparation")
        regular_path(ROOT / "sources.lock.json")
        regular_path(manifest_path)
        if (skills.fingerprint(ROOT / "sources.lock.json") != lock_fingerprint or
                (skills.fingerprint(manifest_path) if manifest_path.exists() else None) != old_manifest):
            raise RuntimeError("Snapshot manifest or lock changed during preparation")
        replacements = [skills.Replacement(target, package / layout[0], source_stage / ("backup-" + name))
                        for name, layout in LAYOUT.items() for target in [ROOT / layout[0]]]
        replacements.append(skills.Replacement(manifest_path, candidate_manifest, outer / "backup-manifest"))
        skills.replace_transaction(replacements)
        committed = True
        return manifest
    finally:
        for stage in stages:
            if committed or not any(item.backup.exists() and item.backup.is_relative_to(stage) for item in replacements):
                shutil.rmtree(stage)
        if created_upstream and (ROOT / "upstream").exists() and not any((ROOT / "upstream").iterdir()):
            (ROOT / "upstream").rmdir()
        guard.rmdir()


def prepare(plan_path: Path, output: Path) -> dict:
    baseline = verify(ROOT)
    pins = read_pins(ROOT)
    regular_path(plan_path)
    regular_path(output)
    if any(output.absolute().is_relative_to(ROOT / layout[0]) for layout in LAYOUT.values()) or ".git" in output.parts:
        raise RuntimeError("Proposal output cannot be inside owned sources or Git metadata")
    if not plan_path.is_file() or output.exists():
        raise RuntimeError("A regular update plan and a new output directory are required")
    plan = json.loads(plan_path.read_bytes())
    if (not isinstance(plan, dict) or set(plan) != {"schema", "sources"} or plan["schema"] != 1 or
            not isinstance(plan["sources"], dict) or set(plan["sources"]) != set(LAYOUT)):
        raise RuntimeError("Invalid complete update plan")
    proposed = {}
    for name, entry in plan["sources"].items():
        if (not isinstance(entry, dict) or set(entry) != {"from_sha", "to_sha"} or entry["from_sha"] != pins[name]["sha"] or
                not isinstance(entry["to_sha"], str) or not skills.SHA_RE.fullmatch(entry["to_sha"])):
            raise RuntimeError("Stale or invalid update plan")
        proposed[name] = {"repository": skills.SOURCES[name]["url"], "branch": "main", "sha": entry["to_sha"]}
    output.mkdir(mode=0o755)
    try:
        with tempfile.TemporaryDirectory(prefix=STAGE, dir=output.parent) as temporary:
            manifest = build_package(output, proposed, Path(temporary))
        (output / "sources.lock.json").write_bytes(serialized({"schema": 1, "sources": proposed}))
        (output / "sources.lock.json").chmod(0o644)
        if verify(ROOT) != baseline or read_pins(ROOT) != pins:
            raise RuntimeError("Baseline changed while preparing proposed snapshots")
        verify(output)
        return manifest
    except BaseException:
        shutil.rmtree(output)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    update = commands.add_parser("refresh", help="Snapshot exact current lock pins; never execute source files")
    update.add_argument("--approve-update", action="store_true")
    check = commands.add_parser("verify", help="Verify source bytes, modes, Git proofs and lock without network")
    check.add_argument("--root", type=Path, default=ROOT)
    proposal = commands.add_parser("prepare", help="Prepare exact proposed snapshots and pins without altering the baseline")
    proposal.add_argument("--update-plan", type=Path, required=True)
    proposal.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "verify":
            manifest = verify(args.root)
        elif args.command == "prepare":
            manifest = prepare(args.update_plan, args.output_dir)
        else:
            manifest = refresh(args.approve_update)
        print(json.dumps({"status": "verified" if args.command == "verify" else "prepared" if args.command == "prepare" else "refreshed",
                          "sources": {name: source["commit_sha"] for name, source in manifest["sources"].items()}}))
        return 0
    except (RuntimeError, OSError, ValueError, KeyError, TypeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
