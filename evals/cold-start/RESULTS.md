# Observed cold-start run — 2026-10-28

## Setup

Two fresh agent tasks received the identical prompt in [README](README.md), differing only in isolated local paths. Both had local shell/file access and the same explicit ban on networking, browser work, installation, delegation and publication. No prior conversation was inherited. Both received the same four-file synthetic checkout fixture, not a live user project. Neither was told which original skill to read or which work-record template to use. The candidate mirror did **not** contain this evaluation harness or result report during its trial.

- Baseline guide tree: `126a7c99e9fa26c422071557f372df76b6a82026` (equivalent to public main `4244a960` at the start).
- Candidate guide commit: `07de9c6a7f7b6e6706b06c0a192271dc5f3249c5` (entry protocol, helper and documentation changes; before adding this report).
- One trial per condition. No timing or cost comparison, randomized repeats, blind human rating or cross-model claim.

## Direct artifact observations

The independent grader first tested the unmodified fixture: its original **two unit tests passed**, but `shipping_cost(50)` returned **5 instead of 0**. Thus the grader detects the real reported defect rather than accepting a green but incomplete existing suite.

| Observed outcome | Baseline | Candidate |
| --- | --- | --- |
| Final implementation | `subtotal >= 50` | `subtotal >= 50` |
| Independent probes: 0, 49.99, 50, 50.01, 100 | All five pass | All five pass |
| Project test suite after work | Three tests pass | Five tests pass |
| Added boundary regression(s) | Exactly 50 | Exactly 50, immediately below/above |
| Protected project README/AGENTS | Hashes unchanged | Hashes unchanged |
| Assimilation mirror | Git worktree unchanged | Git worktree unchanged |
| Authorized durable audit record | `trial-log.md` | `trial-log.md` |

Both agents fixed the task. **This does not demonstrate improved functional accuracy or general autonomy from the new guide.** More tests in one sample are not proof of superior quality. Both were explicitly asked to leave an audit log, so the existence of that log is not credited to the guide.

## Trace and record review (not independent tool telemetry)

The agents' retained command logs and produced artifacts were inspected: [baseline trace](observations/baseline-trace.md), [candidate trace](observations/candidate-trace.md), [baseline independent grade](observations/baseline-grade.json), [candidate independent grade](observations/candidate-grade.json), and [initial failing grade](observations/before-grade.json). These are agent-recorded traces, not an independently instrumented tool-access audit:

- Baseline reported reading AGENTS, README, DOCTRINE, WORKFLOW, original Matt diagnosis/TDD/review material and original P-Stack TDD/behavior-testing material. Its record explains permitted adaptations, red/green results and self-review limits.
- Candidate reported reading START_HERE first, then project instructions, original Matt diagnosis and original P-Stack prove-it-works/behavior-testing material. It recorded exact source pins, capability observations, project acceptance rule, reasoning for a narrow comparator change, actual failed/passed checks and a completed-task handoff.
- Candidate encountered a failed Git-status command because the fixture is not a Git repository. Its record explicitly preserved that failure instead of claiming Git evidence, and used an actual file comparison for its final inspection.
- Both described a failing equality regression before the implementation change, then passing tests. Final code and independently rerun tests support the resulting repair; the historical red sequence is supported by their recorded traces, not independently replayed agent tool events.
- Neither claimed independent review, native slash-command activation or external deployment. The records explicitly distinguish local source procedures from host runtime capabilities.
- Candidate did **not** invoke the optional `onboard.py` helper; it used the manual original-source reading path. The helper is separately covered by nine behavioral CLI tests, not credited as live-used in this trial.
- Candidate used the explicitly authorized audit log as its existing run-record equivalent rather than creating a second `.assimilation/run.md`. This is permitted by the guide and avoids duplicate bookkeeping.

## What this establishes—and does not

Observed: an unfamiliar agent followed the new entry path and performed a real bounded repair, selected original sources, recognized an unavailable Git capability, preserved the local authority boundary and left usable evidence. The source index has separate CLI tests for unrelated working directories, missing/tampered sources, uncertain routes and honest host limits. The evaluation harness itself is tested to reject the initial bug and protected-file changes while accepting the actual repair.

Not established: that the guide caused the success (baseline also succeeded), that every unfamiliar model or host will succeed, URL-only retrieval/clone authentication, actual delegation, production integration, privacy-sensitive judgment, browser-only operation, long interrupted handoffs, or enforcement against a malicious agent. No user/private data was included. This procedure supplies a practical starting contract; it does not create missing runtime powers.
