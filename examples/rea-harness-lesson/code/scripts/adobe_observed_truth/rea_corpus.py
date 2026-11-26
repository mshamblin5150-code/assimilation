"""Static REA corpus of the Photoshop 2026 and Illustrator 2026 installs.

python -m scripts.adobe_observed_truth.rea_corpus manifest --out <corpus>
python -m scripts.adobe_observed_truth.rea_corpus inspect  --out <corpus>
python -m scripts.adobe_observed_truth.rea_corpus decompile --out <corpus> [--max-mb N]
python -m scripts.adobe_observed_truth.rea_corpus bundle   --out <corpus>

manifest  lists every native binary with SHA-256, size and publisher.
inspect   runs REA's engine-free PE inspections (imports, exports, resources) on every binary.
decompile runs REA analyze + decompile-all (Ghidra) on every Adobe-published binary,
          smallest first, several at once within a memory budget; each step resumes.
bundle    wraps every REA Evidence record the steps returned into one importable bundle.

Every step skips work whose output already exists, so a run can be stopped and restarted.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .rea_evidence import evidence_bundle

APPS = {
    "photoshop": Path(r"C:\Program Files\Adobe\Adobe Photoshop 2026"),
    "illustrator": Path(r"C:\Program Files\Adobe\Adobe Illustrator 2026"),
}
NATIVE_SUFFIXES = {".exe", ".dll", ".8bf", ".8bi", ".8be", ".8bx", ".8by", ".8bp", ".8li", ".aip", ".apl"}
REA = ["npx", "-y", "rea-agents@6.8.0"]
_TOOLS = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "ReverseEngineering"
GHIDRA_ENV = {
    "GHIDRA_INSTALL_DIR": str(_TOOLS / "Ghidra-12.1.4"),
    "JAVA_HOME": str(_TOOLS / "Temurin-21.0.13"),
    # Unset means no per-function limit: on 2026-11-08 one function ran ~9 h, grew decompile.exe
    # to ~69 GB virtual, exhausted the commit limit, and every later job failed to start Java.
    "REA_GHIDRA_DECOMPILE_TIMEOUT_SECONDS": "300",
}
INSPECTIONS = ("inspect-pe-imports", "inspect-native-exports", "inspect-pe-resources", "inspect-pe-certificates")
MB = 1 << 20
# Adobe signs the open-source and vendor libraries it ships; these names are not Adobe's code.
THIRD_PARTY = re.compile(
    r"^(libcef|libEGL|libGLESv2|av(codec|format|util)-|opencv_|imgcodecs|imgproc|boost_|icudt|"
    r"tbb|adobeusd_|ArriImageSdk|REDR3D|kdu_|vulkan-1|vk_swiftshader|git2|embree|flann|libzip|"
    r"libmpg123|scintilla|HalideRuntime|pngquant|codexhdedecoder|typequest_|icu(cnv|in|uc)|"
    r"chrome_elf|libcrypto|libssl|node\.dll|libcairo|xerces|dnssd|d3dcompiler|dxcompiler|dxil|cudart)",
    re.IGNORECASE,
)


def heap_gb(size: int) -> int:
    """Ghidra JVM heap for a binary of this size; the native decompilers need memory on top."""
    if size < 1 * MB:
        return 2
    if size < 10 * MB:
        return 4
    if size < 50 * MB:
        return 8
    return 20


def build_manifest(out: Path) -> list[dict]:
    import win32api

    entries = []
    for app, root in APPS.items():
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in NATIVE_SUFFIXES:
                continue
            try:
                language, codepage = win32api.GetFileVersionInfo(str(path), r"\VarFileInfo\Translation")[0]
                company = win32api.GetFileVersionInfo(
                    str(path), rf"\StringFileInfo\{language:04x}{codepage:04x}\CompanyName"
                ) or ""
            except Exception:
                company = ""
            relative = path.relative_to(root)
            entries.append(
                {
                    "app": app,
                    "path": str(path),
                    "relative": str(relative),
                    "work_dir": str(out / app / str(relative).replace("\\", "__")),
                    "bytes": path.stat().st_size,
                    "sha256": _sha256(path),
                    "company": company.strip(),
                    "adobe": "adobe" in company.lower(),
                }
            )
    (out / "manifest.json").write_text(json.dumps(entries, indent=1), encoding="utf-8")
    return entries


def run_rea(arguments: list[str], output: Path, env: dict[str, str] | None = None) -> bool:
    """Run one REA CLI command, keeping stdout as JSON and stderr beside it; True on success."""
    output.parent.mkdir(parents=True, exist_ok=True)
    partial = output.with_suffix(".partial")
    with partial.open("w", encoding="utf-8") as stdout, output.with_suffix(".err").open("w", encoding="utf-8") as stderr:
        code = subprocess.call(
            [*REA, *arguments, "--format", "json"],
            stdout=stdout,
            stderr=stderr,
            env={**os.environ, **(env or {})},
            shell=True,  # npx is a .cmd shim on Windows
        )
    if code == 0:
        partial.replace(output)
        return True
    partial.replace(output.with_suffix(".failed.json"))
    return False


def is_decompiled(work_dir: Path) -> bool:
    """Whether one binary's pseudocode is all on disk. Either decompile-all returned, or it
    failed only afterwards: on the largest binaries REA journals every procedure and then
    cannot build its result ("Invalid string length"), so a failed run whose journal covers
    every procedure the analysis found counts too."""
    if (work_dir / "decompile-all.json").exists():
        return True
    journal = work_dir / "pseudocode" / "decompile-journal.jsonl"
    if not (work_dir / "decompile-all.failed.json").exists() or not journal.exists():
        return False
    analysis = json.loads((work_dir / "analyze.json").read_text(encoding="utf-8"))
    with journal.open(encoding="utf-8") as lines:
        journalled = sum(1 for line in lines if '"kind":"function"' in line.replace(" ", ""))
    return journalled >= analysis["normalized_result"]["procedure_count"]


def inspect_all(entries: list[dict], workers: int) -> None:
    jobs = [
        (entry, command)
        for entry in entries
        for command in INSPECTIONS
        if not (Path(entry["work_dir"]) / f"{command}.json").exists()
    ]
    print(f"inspect: {len(jobs)} jobs", flush=True)

    def work(job):
        entry, command = job
        # Photoshop.exe is 252 MB; REA's default read budget is 64 MiB.
        arguments = [command, entry["path"], "--max-file-bytes", str(512 * MB)]
        ok = run_rea(arguments, Path(entry["work_dir"]) / f"{command}.json")
        print(f"{'ok  ' if ok else 'FAIL'} {command} {entry['app']}/{entry['relative']}", flush=True)

    with ThreadPoolExecutor(workers) as pool:
        list(pool.map(work, jobs))


def signer(entry: dict) -> str | None:
    """Organization of the leaf code-signing certificate, from REA's certificate inspection."""
    path = Path(entry["work_dir"]) / "inspect-pe-certificates.json"
    if not path.exists():
        return None
    tables = json.loads(path.read_text(encoding="utf-8"))["normalized_result"].get("entries") or []
    certificates = (tables[0].get("pkcs7") or {}).get("certificates") or [] if tables else []
    issuers = {c["issuer"]["text"] for c in certificates}
    for certificate in certificates:
        subject = certificate["subject"]
        if subject["text"] in issuers or "timestamp" in subject["text"].lower():
            continue
        return next((a["value"] for a in subject["attributes"] if a["oid_name"] == "organizationName"), None)
    return None


def is_adobe_code(entry: dict) -> bool:
    if entry["adobe"]:
        return True
    # A blank publisher field is common on Adobe's own DLLs; another vendor's name is not.
    name = Path(entry["relative"]).name
    return not entry["company"] and signer(entry) == "Adobe Inc." and not THIRD_PARTY.match(name)


# Binaries not decompiled, by file name, with why. Their partial pseudocode stays on disk.
SKIPPED = {
    # Content-credentials signing library. Both copies decompiled about 19 functions an hour on
    # 2026-11-18 (a third hitting the 5-minute cap) and held Photoshop.exe out of the memory budget.
    "adobe_c2pa.dll": "decompiles too slowly; not interface code",
}


def is_skipped(entry: dict) -> bool:
    return Path(entry["relative"].replace("\\", "/")).name in SKIPPED


def decompile_queue(entries: list[dict], max_bytes: int | None) -> list[dict]:
    """Adobe binaries whose pseudocode is not all on disk yet, smallest first."""
    queue = sorted(
        (
            e
            for e in entries
            if is_adobe_code(e) and not is_skipped(e) and (max_bytes is None or e["bytes"] <= max_bytes)
        ),
        key=lambda e: e["bytes"],
    )
    return [e for e in queue if not is_decompiled(Path(e["work_dir"]))]


def resume_flag(pseudocode: Path) -> list[str]:
    """REA refuses to export into an existing folder without --resume, and refuses --resume
    without one. An interrupted export leaves the folder (journal, no index yet)."""
    return ["--resume"] if pseudocode.is_dir() else []


def decompile_all(entries: list[dict], budget_gb: int, max_bytes: int | None, startup_hours: float = 48) -> None:
    queue = decompile_queue(entries, max_bytes)
    print(f"decompile: {len(queue)} binaries, budget {budget_gb} GB heap", flush=True)
    lock = threading.Condition()
    in_use = [0]

    def work(entry: dict) -> None:
        heap = min(heap_gb(entry["bytes"]), budget_gb)
        with lock:
            lock.wait_for(lambda: in_use[0] + heap <= budget_gb)
            in_use[0] += heap
        try:
            work_dir = Path(entry["work_dir"])
            env = {
                **GHIDRA_ENV,
                "GHIDRA_HEADLESS_MAXMEM": f"{heap}G",
                # decompile-all reruns the whole analysis first: Photoshop.exe took over 48 h.
                "REA_GHIDRA_STARTUP_TIMEOUT_MS": str(int(startup_hours * 3600 * 1000)),
            }
            snapshot = str(work_dir / "analysis.snapshot")
            started = time.monotonic()
            ok = (work_dir / "analyze.json").exists() or run_rea(
                ["analyze", entry["path"], "--snapshot", snapshot], work_dir / "analyze.json", env
            )
            pseudocode = work_dir / "pseudocode"
            ok = ok and run_rea(
                ["decompile-all", entry["path"], "--snapshot", snapshot, "--output", str(pseudocode), *resume_flag(pseudocode)],
                work_dir / "decompile-all.json",
                env,
            )
            minutes = (time.monotonic() - started) / 60
            print(f"{'ok  ' if ok else 'FAIL'} {minutes:7.1f} min {entry['bytes'] / MB:8.1f} MB "
                  f"{entry['app']}/{entry['relative']}", flush=True)
        finally:
            with lock:
                in_use[0] -= heap
                lock.notify_all()

    with ThreadPoolExecutor(max(1, budget_gb // 2)) as pool:
        list(pool.map(work, queue))


def bundle_all(out: Path) -> Path:
    records = {}
    for path in out.rglob("*.json"):
        if path.name in {"manifest.json", "rea-corpus-bundle.json"} or path.parent.name == "pseudocode":
            continue
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        if isinstance(record, dict) and str(record.get("evidence_id", "")).startswith("ev_"):
            records[record["evidence_id"]] = record
    target = out / "rea-corpus-bundle.json"
    target.write_text(json.dumps(evidence_bundle(list(records.values())), ensure_ascii=False), encoding="utf-8")
    print(f"bundle: {len(records)} records -> {target}")
    return target


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("step", choices=["manifest", "inspect", "decompile", "bundle"])
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=8, help="parallel inspect jobs")
    parser.add_argument("--budget-gb", type=int, default=20, help="total Ghidra heap across parallel decompiles")
    parser.add_argument("--max-mb", type=float, help="only decompile binaries up to this size")
    parser.add_argument("--startup-hours", type=float, default=48, help="Ghidra import+analysis limit per step")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    if args.step == "manifest":
        entries = build_manifest(args.out)
        print(f"manifest: {len(entries)} binaries, {sum(e['adobe'] for e in entries)} Adobe-published")
        return
    if args.step == "bundle":
        bundle_all(args.out)
        return
    entries = json.loads((args.out / "manifest.json").read_text(encoding="utf-8"))
    if args.step == "inspect":
        inspect_all(entries, args.workers)
    else:
        decompile_all(entries, args.budget_gb, int(args.max_mb * MB) if args.max_mb else None, args.startup_hours)


if __name__ == "__main__":
    sys.exit(main())
