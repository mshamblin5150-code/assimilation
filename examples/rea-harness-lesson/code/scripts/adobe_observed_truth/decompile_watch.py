"""One progress check of a rea_corpus decompile run: report only, never stop or restart anything.

python -m scripts.adobe_observed_truth.decompile_watch --corpus <dir>

For every REA job running: its step, hours, the Ghidra CPU gained since the last check, and
where it is. What the first runs taught:

- decompile-all reimports the binary and reruns Ghidra's whole analysis before it writes any
  function, so 0 functions for about as long as the first analysis took is normal (Photoshop.exe:
  41 h). The report says when functions should start.
- On the largest binaries REA journals every function and then fails building its result
  ("Invalid string length"). That FAIL leaves all the pseudocode on disk, and is reported as done.
- A stall is little Ghidra CPU over a long interval, not a function count that stays at 0.

Appends to <corpus>/decompile-watch.log and prints the same lines; state is kept beside it.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from .rea_corpus import is_decompiled

STALL_CPU_PER_MIN = 0.1  # under 6 Ghidra CPU minutes an hour; a busy job gains about 60
STALL_MIN_INTERVAL = 10  # minutes: shorter gaps are too noisy to judge
LOGS = ("decompile.log", "decompile-large.log", "decompile-rerun.log")


@dataclass(frozen=True)
class Job:
    binary: str  # app/relative path, as the decompile logs name it
    step: str  # analyze or decompile-all
    started: datetime
    hours: float
    cpu_min: float
    mem_gb: float
    journalled: int  # functions REA has journalled so far
    procedures: int | None  # functions the first analysis found
    first_analysis_h: float | None


def job_line(job: Job, previous_cpu_min: float | None, minutes_since: float | None) -> str:
    gained = "n/a (new)" if previous_cpu_min is None else f"{job.cpu_min - previous_cpu_min:g}"
    line = f"  {job.binary}  {job.step}  {job.hours:g} h; ghidra cpu {job.cpu_min:g} min (+{gained}), {job.mem_gb:g} GB"
    if job.step == "decompile-all" and job.journalled == 0:
        line += "; re-analysing before decompiling"
        if job.first_analysis_h is not None:
            expected = job.started + timedelta(hours=job.first_analysis_h)
            line += f" (first analysis took {job.first_analysis_h:g} h: functions expected about {expected:%Y-%m-%d %H:%M})"
    elif job.step == "decompile-all":
        line += f"; decompiling: {job.journalled:,}"
        if job.procedures:
            line += f" of {job.procedures:,} functions ({job.journalled / job.procedures:.0%})"
        else:
            line += " functions"
    if (
        previous_cpu_min is not None
        and minutes_since is not None
        and minutes_since >= STALL_MIN_INTERVAL
        and (job.cpu_min - previous_cpu_min) / minutes_since < STALL_CPU_PER_MIN
    ):
        line += "  STALL?"
    return line


def logged_line(log_name: str, line: str, decompiled: bool) -> str:
    if line.startswith("FAIL") and decompiled:
        return f"  logged: {log_name} : done, pseudocode all on disk (REA's result failed): {line}"
    return f"  logged: {log_name} : {line}"


def _journalled(work_dir: Path) -> int:
    journal = work_dir / "pseudocode" / "decompile-journal.jsonl"
    if not journal.exists():
        return 0
    newlines = 0
    with journal.open("rb") as handle:
        while chunk := handle.read(1 << 24):
            newlines += chunk.count(b"\n")
    return max(newlines - 1, 0)  # the first line is the header


def first_analysis(work_dir: Path) -> tuple[int | None, float | None]:
    """Functions the first analysis found and how long it took: from its stderr being created
    (the start; a late warning moves its last-write time) to its result being written."""
    result, started = work_dir / "analyze.json", work_dir / "analyze.err"
    if not result.exists():
        return None, None
    count = json.loads(result.read_text(encoding="utf-8")).get("normalized_result", {}).get("procedure_count")
    hours = None
    if started.exists():
        hours = round((result.stat().st_mtime - started.stat().st_birthtime) / 3600, 1)
    return count, hours


def _running(entries: list[dict]) -> tuple[bool, list[Job], dict[str, Path]]:
    import psutil

    runner_alive, jobs = False, []
    work_dirs = {f"{e['app']}/{e['relative']}": Path(e["work_dir"]) for e in entries}
    by_path = {e["path"].lower(): f"{e['app']}/{e['relative']}" for e in entries}
    now = datetime.now()
    for process in psutil.process_iter(["name", "cmdline", "create_time"]):
        command = " ".join(process.info["cmdline"] or [])
        if re.search(r"rea_corpus\s+decompile", command):
            runner_alive = True
        if process.info["name"] != "node.exe" or not re.search(r"rea\.mjs.*\b(analyze|decompile-all)\b", command):
            continue
        binary = next((key for path, key in by_path.items() if path in command.lower()), None)
        if binary is None:
            continue
        cpu, mem = 0.0, 0.0
        try:
            java = next((c for c in process.children(recursive=True) if c.name() == "java.exe"), None)
            if java:
                times = java.cpu_times()
                cpu, mem = round((times.user + times.system) / 60, 1), round(java.memory_info().rss / (1 << 30), 2)
        except psutil.Error:
            pass
        started = datetime.fromtimestamp(process.info["create_time"])
        procedures, first_h = first_analysis(work_dirs[binary])
        jobs.append(
            Job(
                binary=binary,
                step="decompile-all" if "decompile-all" in command else "analyze",
                started=started,
                hours=round((now - started).total_seconds() / 3600, 1),
                cpu_min=cpu,
                mem_gb=mem,
                journalled=_journalled(work_dirs[binary]),
                procedures=procedures,
                first_analysis_h=first_h,
            )
        )
    return runner_alive, jobs, work_dirs


def check(corpus: Path) -> list[str]:
    state_path = corpus / "decompile-watch.state.json"
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
    previous_cpu: dict[str, float] = state.get("cpu", {})
    last = datetime.fromisoformat(state["at"]) if "at" in state else None
    now = datetime.now()
    minutes_since = (now - last).total_seconds() / 60 if last else None
    entries = json.loads((corpus / "manifest.json").read_text(encoding="utf-8"))
    runner_alive, jobs, work_dirs = _running(entries)

    lines = [f"{now:%Y-%m-%d %H:%M}  run alive: {runner_alive}; jobs running: {len(jobs)}"]
    cpu_now = {}
    for job in jobs:
        key = f"{job.binary}|{job.step}"
        cpu_now[key] = job.cpu_min
        lines.append(job_line(job, previous_cpu.get(key), minutes_since))
    seen: dict[str, int] = state.get("logs", {})
    counts, last_logged = {}, ""
    for name in LOGS:
        path = corpus / name
        if not path.exists():
            continue
        logged = path.read_text(encoding="utf-8").splitlines()
        counts[name] = len(logged)
        for line in logged[seen.get(name, 0):]:
            if line.startswith(("ok", "FAIL")):
                binary = re.split(r"\s+MB\s+", line, maxsplit=1)[-1]
                done = line.startswith("FAIL") and binary in work_dirs and is_decompiled(work_dirs[binary])
                lines.append(logged_line(name, line, done))
        if logged:
            last_logged = f"{name} : {logged[-1]}"
    if not jobs:
        lines.append(f"  no job running; last logged: {last_logged}")
    with (corpus / "decompile-watch.log").open("a", encoding="utf-8") as log:
        log.write("\n".join(lines) + "\n")
    state_path.write_text(json.dumps({"at": now.isoformat(), "cpu": cpu_now, "logs": counts}, indent=2), encoding="utf-8")
    return lines


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--corpus", type=Path, required=True)
    print("\n".join(check(parser.parse_args().corpus)))


if __name__ == "__main__":
    main()
