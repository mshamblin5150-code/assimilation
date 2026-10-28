# Independent recovery verification — pre-repair artifacts

Reviewer: fresh delegated `verify_trials` agent, 2026-10-28 UTC. Scope: retained synthetic projects and supplied interrupted-handoff grader; no implementation edits, external calls, installation, real data, or publication. New evidence files only under this directory. Python 3.12.14, integer-string digit limit 4300.

## Sources and method

Read actual guide README, AGENTS, START_HERE, DOCTRINE, SWARMS and pinned original Matt `skills/engineering/tdd/{SKILL.md,tests.md,mocking.md}` plus P-Stack `skills/{tdd,principle-prove-it-works,principle-test-behavior-not-implementation}/SKILL.md`. Matt pin `59db609eb1e18aaf59b63284d0e52255aff0c63c`; P-Stack pin `c742dd61706fbacc1b95f1a20b7b988cf096ce6c`. These were source readings and permitted procedure, not native slash invocation. This is review/challenge, not an implementation TDD cycle; no red-to-green correction is claimed. Tests use project-preapproved public seams only, with literal contract-derived expectations and no private helper assertions or mocks.

Read each project's protected AGENTS/brief, checkpoint RUN_RECORD, actual trial-b modules and all six tests in test_challenge.py. Read the grader/README; inspected retained checkpoint-grade.json before grading. Its predeclared policy is `distinct`, stage `checkpoint`, mode `interrupted`; this agrees with checkpoint RUN_RECORD. Swarm grading uses its own brief and no additional retry-policy requirement.

## Commands and results

Commands from workspace root (output retained as `*-grade.json` and `*-grade.stdout`):

```
python -B assimilation-handoff-work/evals/interrupted-handoff/grade.py assimilation-handoff-evidence/checkpoint-a --retry-policy distinct --stage checkpoint --output assimilation-handoff-evidence/recovery-verification/checkpoint-a-grade.json
python -B assimilation-handoff-work/evals/interrupted-handoff/grade.py assimilation-handoff-evidence/resumed-a --retry-policy distinct --output assimilation-handoff-evidence/recovery-verification/resumed-a-grade.json
python -B assimilation-handoff-work/evals/interrupted-handoff/grade.py assimilation-handoff-evidence/trial-b --mode swarm --output assimilation-handoff-evidence/recovery-verification/trial-b-grade.json
```

| Artifact | Project unittest result | Oracle checks | Overall requested grade |
|---|---|---|---|
| checkpoint-a | 8/8 pass | core 29/29, API 0/19, CLI 0/7 | PASS checkpoint, intentionally incomplete |
| resumed-a | 16/16 pass | core 29/29, API 19/19, CLI 7/7 | PASS complete under existing grader |
| trial-b | 25/26 pass, one failure | core 29/29, API 18/18, CLI 7/7 | FAIL (project tests) |

Checkpoint API/CLI remain byte-identical to fixture, and all protected file hashes pass the correct interrupted/swarm baseline. Resumed pricing is byte-identical to checkpoint (`acd1b9cc1604751183bef2f234e50c6ab7c5114a88dd655beb98d7f8608509d9`). `integrity.json` records key file hashes; `pre-repair-manifest.json` records every retained non-cache file in all three projects before repair. No pricing or protected files were edited by this reviewer.

## Independently reproduced contract defect

Actual retained trial-b challenge has six tests. Five pass, including its deep-invalid JSON, rounding/threshold, late atomic failure, nested defensive-copy and legacy cases. `test_cli_valid_large_integer_product_emits_success` fails: 4300 decimal nines times quantity 10 is a valid 4301-digit integer result, but `json.dumps` raises ValueError outside the CLI try block, emitting traceback and exit 1.

A separately written `independent_challenge.py` exercises pricing literals, legacy generator, Python boolean/float equality replay trap, omitted/null raw-shape distinction, atomic validation and mutations, ordinary CLI/invalid boolean CLI, deep-invalid JSON, and a different 4300-digit value (eights) times 10. Run on both retained trial-b and resumed-a:

```
python -B assimilation-handoff-evidence/recovery-verification/independent_challenge.py assimilation-handoff-evidence/trial-b
python -B assimilation-handoff-evidence/recovery-verification/independent_challenge.py assimilation-handoff-evidence/resumed-a
```

Each runs 8 tests: 7 pass, 1 fails, exit 1. Full transcripts are `trial-b-independent.log` and `resumed-a-independent.log`. Both correctly reject True and 1.0 replay values that compare equal to original integer fields and preserve the existing cache. Both preserve distinct omitted/null identity. Both fail valid large-integer CLI output. Thus resumed-a passes the predeclared oracle, but is NOT supported as fully contract-correct by expanded independent challenge.

### Contract assessment and correction recommendation

This failure is in scope: the protected brief permits nonnegative integer unit cents and positive integer quantity with no maximum size; its CLI must return success for valid input. A 4300-digit JSON number is accepted by the current parser; multiplication by ten then crosses Python's conversion guard. Rejecting this request as invalid merely by catching serialization ValueError would still fail the contract. A minimal synthetic-only correction can deliberately support unbounded integer conversion at the short-lived CLI boundary, restoring interpreter configuration when callable main returns if it changes process-global settings. Retain regression tests for valid parsing/output beyond the default limit. Do not silently invent a monetary size cap or weaken tests. Removing runtime limits is not automatically an appropriate production security policy; external resource limits and a product-approved bound would be separate requirements outside this fixture.

## Limitations

These are direct artifact and execution observations, not proof of historical fresh-agent isolation, original tool traces, actual assignment overlap, abrupt process termination, or a genuine live swarm. Original agents are absent after reset. Agent-authored RUN_RECORD/worker notes remain self-report; current independent reviewer existence does not retroactively verify their telemetry. No model/host generality, reliability rate, causal advantage, production safety, deployment permission, or monthly updater outcome follows. Existing grader lacks the demonstrated huge-output check; 54/55 successful probes are not exhaustive. All failures above were retained; no hidden repairs or failing-test removal occurred in this review.
