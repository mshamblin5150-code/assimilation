# Permanent Python quality tools

Ruff and mypy are retained development dependencies in `pyproject.toml`, not temporary audit tools. This script-only repository intentionally has no package/build metadata. The developer group is independent of runtime requirements. No CI gate is added while baseline debt remains.

## Setup (PowerShell, from repository root)

Use a verified Python 3.10+ executable. This machine was verified with Python 3.12.8:

```powershell
& C:\codeing\python\python\python.exe -I -m venv "$HOME\.venvs\assimilation-quality"
$p = "$HOME\.venvs\assimilation-quality\Scripts\python.exe"
& $p -I -m pip install --index-url https://pypi.org/simple 'pip>=25.1'
& $p -I -m pip install --index-url https://pypi.org/simple --group dev
```

The environment lives outside the checkout, so no ignore-file edits or tracked binaries are needed. Do not recreate an existing environment blindly. Dependency ranges permit compatible upgrades; they are not a reproducibility lock.

## Nonmutating checks

```powershell
$p = "$HOME\.venvs\assimilation-quality\Scripts\python.exe"
& $p -I -m ruff check --no-cache .
& $p -I -m mypy --cache-dir "$HOME\.venvs\assimilation-quality\mypy-cache"
& $p -I -m mypy --cache-dir "$HOME\.venvs\assimilation-quality\mypy-cache" evals/cold-start/grade.py evals/cold-start/prepare.py
& $p -I -m mypy --cache-dir "$HOME\.venvs\assimilation-quality\mypy-cache" evals/interrupted-handoff/grade.py evals/interrupted-handoff/prepare.py evals/interrupted-handoff/probe.py
```

Ruff includes maintained top-level Python in scripts, tests and each evaluation harness. It does not scan immutable nested fixtures, recorded runs, upstream reference snapshots, downloaded vendor content, or local review/candidate worktrees. Mypy defaults to scripts and tests; run the two harness commands separately because their grade/prepare module names collide in one invocation. Keep all three mypy commands when assessing coverage. No broad error or missing-import suppression is enabled. Untyped function bodies are checked, but this is not strict typing or complete coverage of dynamically loaded code. Tool targets preserve the documented Python 3.10 floor.

## Verified baseline (2026-11-10)

- TOML parsed successfully with Python tomllib; installed Ruff 0.17.4 and mypy 1.20.2 from PyPI in the isolated environment.
- Ruff: 5 findings across 23 maintained files (3 F401, 1 E731, 1 E402). The final file-discovery check confirmed fixtures and recorded evidence are excluded.
- Default mypy: 64 errors in 12 files, 18 source files checked.
- Cold-start harness: no issues in 2 files.
- Interrupted-handoff harness: 13 errors in probe.py, 3 files checked. Two are missing parcelquote imports: the probe expects a separately supplied evaluation target. Other findings include container inference and assignment issues.

These are actual failing advisory checks, not passing quality gates. No automatic fixes, runtime changes, integration tests, host-skill installation, publication or upstream execution were performed. Preserve fixtures/evidence and address maintained-code findings in separately authorized changes. Existing unrelated working-tree changes were left alone.

Read AGENTS, README, START_HERE, doctrine, operator method and swarm guidance. Original code-review and prove-it-works sources were inspected as procedural references; their full native workflows were not invoked. Verification here consists of direct config parsing, installed tool checks and nonmutating analysis, not a claim of independent review or runtime correctness.


All commands use Python -I to ignore inherited PYTHONPATH and user site packages. This avoids unrelated machine-level packages leaking into the tooling environment; no global environment setting is changed.

Verification with -I: pip check reports no broken requirements; tool versions and all three mypy baselines plus Ruff findings remain unchanged.
