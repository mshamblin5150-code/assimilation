# Interrupted-session and real-swarm engineering evaluations

These are **two separate exercises**, not a promise that Assimilation creates a runtime. They use a synthetic, multi-module Python quotation service, a legacy interface, integer money rules, idempotent retry behavior and a JSON command-line boundary. Only the authorized fixture is executed. The grader has subprocess timeouts but is **not a sandbox for arbitrary untrusted code**.

## What the exercises can establish

- **Interrupted continuation:** a first genuinely fresh agent implements and verifies pricing, leaves integration unfinished and writes a durable `RUN_RECORD.md`. Its turn ends. A different fresh agent receives only the guide and copied project/record, not the original conversation or coordinator summary, and finishes the API/CLI. A behavior probe verifies that a discretionary choice recorded by session 1 survives session 2.
- **Actual swarm:** a separate coordinator delegates disjoint module ownership to real child agents, reconciles integration and requests an independent challenger. Record actual assignments, overlapping writes (if any), corrections and evidence. Naming three roles inside one conversation is not a swarm test.
- The task wording is initially underspecified, but most ambiguity is resolved by reading `PROJECT_BRIEF.md`. One retry-identity choice remains deliberately discretionary. This is not open-ended product discovery or a clinical judgment exercise.

## Preparation and authority

Use an immutable Assimilation guide checkout and a new approved local directory:

```sh
python evals/interrupted-handoff/prepare.py /approved/trial
# Separate full swarm exercise:
python evals/interrupted-handoff/prepare.py /approved/swarm --mode swarm
```

Existing destinations are refused. Project `AGENTS.md` and `PROJECT_BRIEF.md` are protected. Local Python/file operations and tests at the named public seams are authorized; network, installs, credentials, production data and publication are not. Only the swarm condition permits actual child delegation. Use synthetic data throughout.

Record exact guide/fixture/grader revisions, launch prompts, agent identities and host capabilities. Freeze fixture and stage-1 snapshots. Keep the grader and calibration implementation outside participating agents' allowed file scope. Shared filesystems still allow technically possible access: this is instruction-scoped access with fresh conversation contexts, **not enforced sandbox isolation**.

## Interrupted-session protocol

1. Launch session 1 with no inherited history, guide URL/local mirror, target path and this task: “Make batch quoting work reliably, including discounts, delivery and retry handling without breaking old callers. Read project context. Implement only core pricing and its tests, leave API/CLI unchanged, write a factual RUN_RECORD with decisions/evidence/remaining work and stop incomplete.”
2. Give session 1 the permitted choice: omitted coupon versus explicit `null` may be either equivalent or distinct for retry identity. It must choose, explain alternatives and persist the choice for the next session; do not implement the API yet. No later coordinator summary conveys that choice to session 2.
3. Wait for the first agent's turn to end. Freeze a complete project snapshot. Independently grade the checkpoint: pricing must work, API/CLI must still fail and their files must be unchanged. Record the chosen retry policy **before** session 2 starts. Do not repair failed participant work silently; report or rerun under a new trial ID.
4. Copy only the project snapshot to a fresh destination. Start a different agent with no inherited history: “Resume the authorized project from its files and RUN_RECORD. Complete remaining work, preserve recorded decisions, verify it and update the record. Use the supplied immutable guide; local files/shell only.” Supply no first-session messages, expected results, hidden probes or grading feedback.
5. Independently grade completion and the predeclared retry policy. Compare protected files and pricing code with the checkpoint; inspect whether the record describes actual remaining work and whether later tests reflect preserved decisions. Grade behavior, not mere record presence.

```sh
python evals/interrupted-handoff/grade.py /approved/checkpoint --stage checkpoint --retry-policy distinct
python evals/interrupted-handoff/grade.py /approved/resumed --retry-policy distinct
```

Use `equivalent` instead if that was session 1's actual frozen choice. Do not select the policy after seeing session 2's output.

## Separate swarm protocol

Launch a fresh coordinator on the `--mode swarm` fixture, the immutable guide and actual available child tools. Require bounded ownership (pricing versus API/CLI), contract coordination, reconciliation and a separate fresh challenger after workers finish. The coordinator may not silently reclassify self-review as independent. Preserve factual worker/coordination records and actual final artifacts, then run:

```sh
python evals/interrupted-handoff/grade.py /approved/swarm --mode swarm
```

Inspect actual child identities, assignments and diffs alongside the independent functional oracle. A passed grader does not prove no overlapping work occurred or validate every claimed historical action.

## Grading and robustness

The oracle checks literal money results, legacy generators, malformed inputs, post-discount shipping thresholds, aggregate floor rounding, large integer cents, atomic validation, mutable cache boundaries, replay type validation, independent instances and CLI JSON/exit behavior. Calibration tests reject the original fixture, premature completion, wrong decisions and protected-file changes, and accept an independent synthetic solution. These tests calibrate the grader, not agent competence.

Inspect capabilities and read/command claims against retained evidence. Agent-authored histories are **self-reported traces**, not independent tool telemetry. Separately rerun project tests and inspect produced code and protected hashes. A turn ending is not proof an OS process was killed; a prepared handoff is not an abrupt crash recovery experiment.

For robustness, repeat with new fresh agents and clean fixtures, preregister repetitions and policies, retain failures, and vary host/model and task only under a stated protocol. Compare equal capabilities and immutable guide revisions if testing causal benefit. Report all trials, not only successful runs. One successful pair and one successful swarm cannot establish reliability, significance, cost/speed advantage or general autonomous competence. The earlier cold-start baseline also passed; no superiority claim follows here.

See [RESULTS.md](RESULTS.md) for what actually ran, artifacts, provenance and limitations. Live monthly updater verification is a separate operational check, not established by these exercises.

## Recheck the retained trial artifacts

From the repository root, run the amended oracle on the immutable original and
assisted-repair copies. Original failures are expected and preserved:

```sh
python evals/interrupted-handoff/grade.py evals/interrupted-handoff/recorded/checkpoint --stage checkpoint --retry-policy distinct
python evals/interrupted-handoff/grade.py evals/interrupted-handoff/recorded/resumed-original --retry-policy distinct  # expected FAIL
python evals/interrupted-handoff/grade.py evals/interrupted-handoff/recorded/swarm-original --mode swarm  # expected FAIL
python evals/interrupted-handoff/grade.py evals/interrupted-handoff/recorded/resumed-repaired --retry-policy distinct
python evals/interrupted-handoff/grade.py evals/interrupted-handoff/recorded/swarm-repaired --mode swarm
```

The archived logs retain their original workspace paths as historical evidence;
use the commands above for the checked-in locations. The incomplete extra attempt
is retained for transparency, not scored as a successful replication. Original
harness hashes are in `recorded/harness-manifest.json`; post-trial amendments and
calibration evidence are in `recorded/harness-review/`.
