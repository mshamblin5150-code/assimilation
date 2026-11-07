# Reset recovery drill results — November 7, 2026

Eight planned scenarios were exercised within controlled boundaries. The observations support supplied-locator recovery, exact-byte restoration to an empty directory, preservation of a running disposable worker, safe handling of unresolved operations, and guarded checkpoint reconciliation. They do **not** establish automatic startup recovery, abrupt host-crash survival, a live supervisor, or exactly-once external execution.

Only synthetic fixtures were mutated. No real project worker was interrupted, replaced or restarted. No hook, security setting, access permission or approval hold changed.

## Results by scenario

| Scenario | Observed result | Boundary and limitation |
| --- | --- | --- |
| Fresh coordinator | Passed. A context without inherited task history read the supplied checkpoint and recovered goal, owner, holds, original timing and next action. | Locator supplied explicitly; automatic discovery was not tested. |
| Workspace loss | Passed within simulation. An empty temporary directory was asserted empty, then the Page's embedded UTF-8 payload was restored and independently hashed. Missing source was correctly identified as unrestorable. | Same cloud executor, new directory; no real workspace was destroyed or replaced. |
| Worker still running | Passed. Two scoped status observations showed the same disposable worker running. The evaluator reported no contact, interrupt, replacement or duplicate launch. The same disposable worker subsequently completed its original 180-second wait normally. | Actual native-worker status was observed, not cloud-task survival through a platform reset. |
| Response lost after submission | Passed within simulation. The successful write receipt was withheld from the recovery evaluator; current Page readback established the synthetic result without resubmission. A separate UNKNOWN submission remained held. | Receipt withholding, not an induced network failure. The verified external effect was the Page marker itself, not another service. |
| Denial and reset | Passed within simulation. A recorded denied-without-execution case survived entry into a fresh context; no new evidence existed and retry count stayed zero. | Synthetic denial record; no real protected action or safety denial was triggered. |
| Concurrent checkpoint update | Passed at the real Page guard. A writer retained a snapshot, another writer changed its field, and the stale patch was rejected as not committed. Reread and reconciliation preserved both changes. | Controlled interleaving of two independent snapshots, not race stress or a distributed transaction guarantee. |
| Original handoff deadline | Passed. Start remained November 6 at 10:00 UTC and deadline November 7 at 10:00 UTC. At 13:51:40 UTC the evaluator reported 3h51m40s overdue, without resetting the interval or cancelling the running worker. | Clock observation and decision were tested; no automatic deadline scheduler was installed. |
| Clean completion | Passed for the bounded acceptance candidate. Matching bytes plus the current committed marker satisfied its requirements. Missing source and same-size one-byte corruption were rejected. The overall mixed-state mission was correctly left incomplete. | A verified sub-result is not whole-mission completion while running, UNKNOWN or missing evidence remains. |

## Exact observations

- Valid payload: 59 bytes; SHA-256 `e43fd91d137a96948795b1bfbbf3b2a2956f7dd2754432688902a3cd19884eaa`.
- Same-size one-byte corruption: SHA-256 `3f1d903c03cce35700af9ac71c73e693a732161a54ed0c04c8cd0d7020567458`. The valid original was unchanged.
- Readback of the one successful synthetic operation: `SYNTHETIC_OPERATION_ALPHA status=committed evidence_version=1`.
- The recovery evaluator reported zero operation submissions or retries; a complete raw tool-call trace is not included in this public bundle.
- Stale checkpoint response: `edit_conflict`, `commit_status=not_committed`, `status=rejected`, `rejection_reason=patch_hash_mismatch`, sequence 3.
- Reconciliation used a fresh guarded read, not an unchanged retry. Final checkpoint: `Checkpoint: writer_a=2; writer_b=1.` at sequence 4; hash `a346530a2dc5110ab09b65e27629e75eb315b6dcd758cf51e9cefd2079a621d8`.

## Unsupported or untested runtime claims

1. **Automatic startup discovery and continuation:** no directly exposed persistent-instruction mutation, reset-event hook or supervisor capability was established. Saving a locator or a Page does not prove that a future task automatically loads or acts on it.
2. **Abrupt platform reset and cloud-task survival:** no safe platform reset/crash control was used. Replacing a real environment or interrupting actual work was outside this drill. Disposable fresh-context recovery is narrower evidence.
3. **Real transport fault injection:** the controlled harness withheld a known receipt; it did not intercept network traffic or force an ambiguous production submission. UNKNOWN handling was exercised without replay.
4. **Real denial persistence across a host reset:** tested with a synthetic denial record. No prohibited action was attempted to manufacture a denial.
5. **Universal exactly-once execution, availability and fleetwide adoption:** neither content hashes nor a successful read prove these properties. Each lane still needs its actual checkpoint, ownership and operation receipts reconciled.

These are capability and coverage limits, not failed actions that should be retried through another route. The remaining implementation work is supported startup loading, a current private lane index, checkpoint discipline at consequential boundaries, and an explicitly supported wake/supervisor if automatic execution is required.

## Evidence and repeatability

`observations.json` is a sanitized projection of the recorded evaluation and service receipts. Fresh-context launch mode was explicitly configured with no inherited turns by the experiment coordinator; action-count and no-contact statements are evaluator-reported, not independently reconstructed from a complete tool trace. Private Page links, account metadata, real worker identifiers and unrelated historical records are omitted. `fixture.json` contains only synthetic scenario data. `PROTOCOL.md` describes the controlled procedure.

Run `python verify_bundle.py` to verify retained file hashes and the local byte controls. This is an offline evidence-integrity check, **not** a rerun of the Page or worker experiments. Repeating the service experiments requires a new disposable private fixture and supported tools, never replaying the original operations.

This evidence supplements [the canonical fleet handoff rule](../../../docs/FLEET_HANDOFF.md); it installs no runtime adapter or hook.
