# Fleet reset recovery

Use this guide after context loss, workspace loss, an interrupted connection, or
an overdue handoff. It extends [the fleet handoff rule](FLEET_HANDOFF.md), which
remains authoritative for ownership, deadlines, retries, and approval holds.

A reset is a recovery event, not a new authorization or proof that work stopped.
The goal is to recover enough verified state to continue the next useful,
authorized action without duplicating work or making the operator repeat facts.
This document installs no hook, scheduler, supervisor, or automatic recovery.

## Preserve before a reset

Keep three things distinct:

- **Recovery guide:** this public procedure and a discoverable pointer to it.
- **Current work record:** the existing private handoff record for each lane,
  with its owner, original start/deadline, current revision, pending operations,
  evidence, holds, and next action. Reuse it rather than creating a second roster.
- **Recovery artifacts:** the approved files needed to restore work, with stable
  locators, byte sizes, and hashes where supported. A local path is only a locator;
  it does not prove the bytes survive a lost workspace.

Store only material approved for each destination. A public repository is suitable
for sanitized guidance and synthetic evidence, not private task records, access
credentials, private transcripts, clinical data, or unapproved unpublished work.
A Drive backup inherits its destination's access settings; verify those settings
before placing private material there. Saving a copy does not grant wider access.

Before a consequential operation, record its target, authorization basis, and
how its outcome can be checked. Preserve the operation ID when one exists. After
it returns, record the observed result and receipt. If a response is lost, retain
an unknown outcome until reconciled. An operation ID helps reconciliation; it is
not an exactly-once guarantee.

Read back a durable save before calling it preserved. Check identity and contents,
not merely that the upload command returned. Preserve the previous verified copy
until the new one is verified. For guarded updates, a revision conflict calls for
reconciliation rather than overwriting another writer's changes.

## Recover in order

1. **Locate.** Read the current project instructions, this guide, and the latest
   private handoff through supported access. Verify the actual capabilities and
   destinations available now. Completion: authoritative records are located, or
   the missing locator/access is named precisely.
2. **Reconcile ownership.** Inspect supported task status and receipts. Classify
   every pending operation as confirmed running, confirmed terminal, denied and
   known not executed, or unresolved. Preserve active ownership and original
   start/deadline. Completion: each operation has an owner and observed state;
   unresolved operations have an explicit reconciliation step.
3. **Reconcile results.** Compare the record with the current repository revision,
   changed files, candidate/PR state, reviews, tests, and external effects relevant
   to the task. Keep run, read, and untested claims separate. Completion: the next
   action rests on current evidence rather than an old status label.
4. **Restore only what is missing.** Retrieve approved artifacts into an isolated
   workspace and verify identity, size, and hash where available. Record any
   verification gap. Completion: required artifacts match the recorded source,
   or the exact missing artifact is a blocker. Reconstruction is not proof of
   recovery and does not authorize repeating an uncertain external operation.
5. **Continue one owned action.** Keep running work with its owner. For unowned
   work, establish one writer before resuming. A successor may write only after
   the previous writer's disposition is reconciled and concurrent writes are
   prevented through a supported mechanism. Completion: the next useful action
   has an owner, authorization, success criterion, and stop condition.
6. **Save the recovery receipt.** Record sources read, observed state, artifacts
   restored, unresolved outcomes, original deadline, and accepted continuation.
   Read it back. Completion: a subsequent fresh session can locate and verify
   the continuation without relying on this session's recollection.

An overdue handoff needs a state-preserving handoff, not a fresh 24-hour clock or
an assumption that admitted work is canceled. A denied operation remains denied
after a reset; use the canonical handoff rule's evidence and retry requirements.
If a real decision is missing, ask for that precise decision and continue useful
independent work. Preserve any applicable no-wake or local-interaction hold.

## What the recovery receipt must establish

Reuse the existing handoff format. Add only missing recovery facts:

- The authoritative work record and the time its claims were checked.
- The repository/ref/commit and any remaining working-tree changes.
- Each pending operation, its receipt or missing ID, current outcome, owner,
  authorization reference, and next reconciliation step.
- Each recovered artifact's source, identity, integrity check, and destination.
- The original deadline, unchanged holds, next owner/action, success/stop criteria,
  and where the verified recovery receipt is saved.

A structural checker can detect missing fields. It cannot establish authorization,
actual execution, a truthful completion claim, or a live recovery mechanism.
See the [handoff checker limits](FLEET_HANDOFF.md#optional-structural-check).

## Verify recovery without disturbing live work

Use disposable workspaces, synthetic records, and simulated operation receipts.
Check these failure modes before claiming that a recovery procedure is reliable:

1. Fresh context can find the guide and current record from the documented pointer.
2. Lost workspace contents can be restored and matched to recorded hashes.
3. A still-running owner is preserved without issuing duplicate work.
4. A lost response is reconciled before any retry.
5. A recorded denial and its relevant evidence survive the reset.
6. A stale guarded write is rejected and reconciled without losing newer work.
7. The original deadline survives recovery and an overdue handoff is visible.
8. Completion is claimed only after the requested acceptance and external state
   are verified; incomplete or blocked work remains visibly incomplete.

For each drill, retain inputs, exact command or procedure, expected result,
observed result, and limitations. Record genuine failures as well as passes.
Synthetic results demonstrate only the tested procedure, not live hook delivery,
all-host activation, crash-proof storage, or successful recovery of every lane.
Existing [interrupted-handoff evidence](../evals/interrupted-handoff/RESULTS.md)
illustrates evidence reporting; its results apply only to its recorded scope.

## Roll out at natural handoffs

Publish and verify the guide, then make its pointer discoverable through supported
project instructions. Apply it when a lane next starts or hands off; do not
interrupt a frozen change just to adopt documentation. Check each lane's actual
continuation and recovery evidence before claiming fleet-wide adoption.

Install a hook or supervisor only as a separate, authorized change with verified
host support, review, and an observed event-to-recovery result. Repository content,
a project-instruction pointer, a manual drill, and a live host integration are
separate claims. Preserve the existing safety, clinical, product, security/data,
persistence, native, teardown, and approval boundaries throughout.
