"""Small, local Windows practice organizer. No dependencies; no recursive scanning."""
import argparse
import hashlib
import json
import os
from pathlib import Path

CATEGORIES = {".txt": "Text", ".md": "Text", ".pdf": "PDF"}

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def root_path(folder):
    raw = Path(folder).absolute()
    if any(p.is_symlink() or p.is_junction() for p in (raw, *raw.parents)):
        raise ValueError("Use a local folder without links or junctions")
    root = raw.resolve(strict=True)
    if not root.is_dir():
        raise ValueError("Choose a folder")
    return root

def safe(root, relative):
    p = Path(relative)
    if p.is_absolute() or any(x in ("..", ".") for x in p.parts) or ":" in relative:
        raise ValueError("Invalid relative path")
    target = root / p
    if target == root or not target.is_relative_to(root):
        raise ValueError("Path escapes folder")
    for part in (target, *target.parents):
        if part == root:
            break
        if part.is_symlink() or part.is_junction():
            raise ValueError("Links and junctions are outside this exercise")
    return target

def preview(folder):
    root = root_path(folder)
    files = sorted(root.iterdir(), key=lambda p: p.name.casefold())
    if len(files) > 30:
        raise ValueError("Choose a practice folder with at most 30 entries")
    rows = []
    for path in files:
        safe(root, path.name)
        if not path.is_file():
            continue
        if path.stat().st_size > 1024 * 1024:
            raise ValueError("Practice files must be at most 1 MiB")
        category = CATEGORIES.get(path.suffix.lower())
        rows.append(dict(source=path.name, destination=f"{category}/{path.name}" if category else None,
                         sha256=digest(path), size=path.stat().st_size,
                         category=category or "Keep", rationale="Extension only; content not inferred",
                         uncertainty="Contents may not match extension; review the proposed category"))
    plan = dict(version=1, root=str(root), files=rows)
    plan["id"] = plan_id(plan)
    return plan

def plan_id(plan):
    return hashlib.sha256(json.dumps({k:v for k,v in plan.items() if k != "id"}, sort_keys=True).encode()).hexdigest()

def save_new(path, obj):
    with open(path, "x", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)
        f.flush()
        os.fsync(f.fileno())

def append(log, obj):
    with open(log, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj) + "\n")
        f.flush()
        os.fsync(f.fileno())

def rename_new(source, destination):
    # Windows rename fails if destination exists. POSIX rename can overwrite.
    if os.name != "nt":
        raise ValueError("Move and undo in this teaching example require Windows")
    os.rename(source, destination)

def apply(plan, approved, log, stop=lambda: False):
    if approved != plan.get("id") or plan_id(plan) != approved:
        raise ValueError("Explicit approval must name the unchanged preview ID")
    root = root_path(plan["root"])
    if preview(root) != plan:
        raise ValueError("Inputs changed; create and approve a fresh preview")
    log = Path(log).absolute()
    if log.is_relative_to(root):
        raise ValueError("Keep the journal outside the practice folder")
    for row in plan["files"]:
        if not row["destination"]:
            continue
        destination = safe(root, row["destination"])
        if destination.exists():
            raise FileExistsError(row["destination"])
        if destination.parent.exists() and not destination.parent.is_dir():
            raise NotADirectoryError(row["destination"])
    with open(log, "x", encoding="utf-8") as f:
        f.write(json.dumps(dict(event="start", plan=plan)) + "\n")
        f.flush(); os.fsync(f.fileno())
    for row in plan["files"]:
        if stop():
            append(log, dict(event="stopped"))
            return
        if not row["destination"]:
            continue
        src, dst = safe(root, row["source"]), safe(root, row["destination"])
        if digest(src) != row["sha256"]:
            raise ValueError("Input changed during apply; preserve journal and undo")
        dst.parent.mkdir(exist_ok=True)
        safe(root, row["destination"])
        append(log, dict(event="intent", row=row))
        rename_new(src, dst)
        append(log, dict(event="moved", source=row["source"]))
    append(log, dict(event="complete"))

def recover_journal(log, output):
    """Preserve original evidence; copy only complete records to a fresh journal."""
    data = Path(log).read_bytes()
    lines = data.splitlines(keepends=True)
    if not lines or lines[-1].endswith(b"\n"):
        raise ValueError("No incomplete trailing record; inspect journal normally")
    # Even valid JSON without a newline is uncommitted; its intent was flushed earlier.
    complete = lines[:-1]
    records = [json.loads(line) for line in complete]
    if not records or records[0].get("event") != "start":
        raise ValueError("Missing complete start record; preserve for manual review")
    with open(output, "xb") as f:
        f.write(b"".join(complete)); f.flush(); os.fsync(f.fileno())

def undo(log):
    records = [json.loads(line) for line in Path(log).read_text(encoding="utf-8").splitlines()]
    plan = records[0]["plan"]
    root = root_path(plan["root"])
    # Intent records also cover interruption after rename but before 'moved'.
    for record in reversed(records):
        if record["event"] != "intent":
            continue
        row = record["row"]
        src, dst = safe(root, row["source"]), safe(root, row["destination"])
        if src.exists() and not dst.exists() and digest(src) == row["sha256"]:
            continue
        if src.exists() or not dst.is_file() or digest(dst) != row["sha256"]:
            raise ValueError("Undo conflict: preserve both paths and journal for review")
        append(log, dict(event="undo-intent", source=row["source"]))
        rename_new(dst, src)
        append(log, dict(event="undone", source=row["source"]))
    append(log, dict(event="undo-complete"))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("preview"); p.add_argument("folder"); p.add_argument("output")
    p = sub.add_parser("apply"); p.add_argument("plan"); p.add_argument("--approve", required=True); p.add_argument("--journal", required=True)
    p = sub.add_parser("undo"); p.add_argument("journal")
    p = sub.add_parser("recover"); p.add_argument("journal"); p.add_argument("output")
    args = parser.parse_args()
    if args.command == "preview":
        plan = preview(args.folder)
        if Path(args.output).absolute().is_relative_to(Path(plan["root"])):
            raise ValueError("Save preview outside practice folder")
        save_new(args.output, plan)
        print(json.dumps(plan, indent=2))
    elif args.command == "apply":
        apply(json.loads(Path(args.plan).read_text(encoding="utf-8")), args.approve, args.journal)
    elif args.command == "recover":
        recover_journal(args.journal, args.output)
    else:
        undo(args.journal)

if __name__ == "__main__":
    main()
