# Interrupted handoff and actual swarm: observed results

**2026-10-28, synthetic local Python exercise.** This is a report of one interrupted continuation and one separately delegated build, including failures. It is not evidence of general reliability or causal superiority over another method.

## Bottom line

The retained first-session artifact genuinely stops after pricing: 8 tests pass, while API and CLI remain byte-identical to the unfinished fixture. The second-session artifact preserves the recorded discretionary retry decision (omitted coupon and explicit null are distinct), preserves pricing byte-for-byte, and finishes the API/CLI. The separate swarm record reports disjoint pricing and integration contributions; the separate implementation and challenge files are retained.

**Both completed implementations nevertheless fail an expanded independent challenge:** a valid large integer product cannot be serialized by the CLI under Python's default decimal-digit limit. The original sequential grader missed this; the swarm's retained independent challenge caught it. Separate coordinator-assisted repairs and stronger grading are reported below, never substituted for the original outcomes.

## What is independently established versus reported

Artifact hashes, source comparisons, project tests, behavior probes and independent post-reset challenges were directly rerun. The first stage is demonstrably incomplete, and the successor preserves its pricing and discretionary decision.

The predecessor coordinator reported launching each interrupted session with fresh context, ending the first before launching the second from copied files/handoff only. Its full launch telemetry did not survive an environment reset. Exact original session identities/prompts cannot now be independently reconstructed; the protocol in README is a reproducible procedure, **not a recovered verbatim launch transcript**. These artifacts establish successful *handoff-compatible behavior*, not independently audited proof that the successor never saw other context.

The retained swarm record identifies `/root/complete_visible_skills/swarm_trial_coordinator`, separate `pricing` and `api_cli` children, and a fresh `challenger`; source ownership is reported as disjoint. Those historical assignments and skill-read traces are agent-reported, not independently authenticated tool telemetry. Post-reset verification, repair and harness-review workers were genuinely delegated separate tasks; they are follow-on reviewers, not replacements for missing original history.

All contexts share a host filesystem. Instruction-scoped fresh context is **not** a security sandbox. No private data, network service, production deployment or clinical work was tested.

## Original results retained without cherry-picking

| Artifact | Project tests | Original oracle | Interpretation |
|---|---:|---:|---|
| First-session checkpoint | 8/8 | core 29/29; API 0/19; CLI 0/7 | Expected incomplete checkpoint passes |
| Resumed session | 16/16 | 55/55 | Original grader passes; expanded challenge fails |
| Separate swarm | 25/26 | 54/54 | Full grade fails because retained challenger catches serialization defect |

An additional `trial-c` partial pricing attempt was found after reset: 8 tests and unfinished API/CLI, without a completed run record or known launch history. It is retained as `recorded/incomplete-repeat`, **not counted as a completed repetition or silently excluded**. No statistical reliability estimate follows.

The original independent post-reset challenge passed 7/8 for each completed artifact. The failing case uses a legal 4300-digit integer multiplied by 10, yielding a 4301-digit integer. Returning an invalid-request error would not satisfy the valid-input contract. See `recorded/recovery-verification/REVIEW.md`, exact hashes, original grades and independent challenge source/logs.

## Corrections and changed grading

The repair is explicitly a **coordinator-assisted post-evaluation correction**, not an unassisted fresh-agent success. Original sequential output is preserved under `recorded/resumed-original`; repaired output is separate. Original swarm CLI and failure evidence are preserved with its repair record and pre-repair manifest. Repairs are limited to the synthetic CLI, with the digit-conversion policy confined to one-shot command execution. This is not a production recommendation to remove resource protections.

Independent Standards review found a second weakness in the oracle: it could miss caching a valid first order before rejecting a later invalid order. The calibrated grader was strengthened after the trials. Original manifests remain retained; new results must distinguish the amended oracle from the predeclared one. This is iterative verification, not a preregistered controlled experiment.

The stronger deep-input probe also found that both originals emit a traceback on malformed JSON nested 10,000 levels deep (the earlier 1,200-level case passed on this runtime). Both repairs handle that error without altering the valid-input contract.

| Amended oracle, independently rerun | Project tests | Probes | Overall |
|---|---:|---:|---|
| Checkpoint | 8/8 | 29/58; integration intentionally incomplete | PASS checkpoint |
| Original resumed | 16/16 | 56/58 | FAIL two CLI probes |
| Original swarm | 25/26 | 55/57 | FAIL project challenge and two CLI probes |
| Assisted resumed repair | 16/16 | 58/58 | PASS |
| Assisted swarm repair | 26/26 | 57/57 | PASS |

Both repaired copies also pass the separate eight-test independent challenge. Import checks confirm the CLI does not change the importing host's integer-conversion policy. Protected briefs, pricing and existing tests remain unchanged by repair; the original sequential artifact remains untouched. Exact results and hashes: `recorded/recovery-verification/final-verification.json` and companion integrity manifests.

## Provenance and methods

Guide tree: `810638ff964be7206dde7c5b0ed482ae18df62f4`, published as main commit `941eefc4de89ff95f9ed2c2f237deee641a17a88` (local guide predecessor commit 16957ae has the same content tree). Original Matt source revision `59db609eb1e18aaf59b63284d0e52255aff0c63c`; original P-Stack source revision `c742dd61706fbacc1b95f1a20b7b988cf096ce6c`.

Participant records identify actual source readings of Matt TDD and required `tests.md`/`mocking.md`, P-Stack TDD, prove-it-works and test-behavior-not-implementation. Independent recovery reviewer read those originals; documentation coordinator read Matt writing-for-agents and P-Stack prove-it-works. This is procedural application of source documents, not a claim that unavailable native slash commands ran. See individual records for exact scope and commands.

## What this does not establish

No measured advantage against a matched baseline, no timing/cost claim, no broad project autonomy claim, no abrupt-process-crash experiment, no true host isolation, and no proof of durable model memory. The earlier cold-start baseline also succeeded. The source updater's live publication operation is a separate check, not established here.

The useful result is narrower: preserved decisions and working multi-module artifacts can be checked independently; adversarial challenge found a real implementation defect and a grading blind spot that ordinary green tests did not establish. Repeat with preregistered fresh agents and multiple tasks before claiming reliability.
