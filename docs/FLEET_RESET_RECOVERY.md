# Fleet reset recovery

Use this guide after context loss, workspace loss, an interrupted connection, or
an overdue handoff. It extends [the fleet handoff rule](FLEET_HANDOFF.md), which
remains authoritative for ownership, deadlines, retries, and approval holds.

A reset is a recovery event, not a new authorization or proof that work stopped.
The goal is to recover enough verified state to continue the next useful,
authorized action without duplicating work or making the operator repeat facts.
This document installs no hook, scheduler, supervisor, or automatic recovery.
Before PR readiness changes, CI waits, or investigating a disputed action, use
[PR coordination](PR_COORDINATION.md) for actual check producers, scoped authority
and evidence limits.

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

### Operation receipts and visibility

Before a consequential operation, record its target, authorization basis, and
how its outcome can be checked. Preserve the operation ID when one exists. After
it returns, record the observed result and receipt. If a response is lost, retain
an unknown outcome until reconciled. An operation ID helps reconciliation; it is
not an exactly-once guarantee.

Capture the safe result when it returns, rather than reconstructing it from a
later summary. Reuse the existing private lane record with one receipt per
attempt. Add only missing fields from this outline; it is a manual reference,
not an installed logger, new checker schema, execution gate, or permission:

- **Binding:** existing owner, action, bounded target, candidate revision or
  artifact hash, and original authority references with their scope.
- **Identifiers and time:** returned call, request, session or service identifiers
  when exposed; source start/completion times when exposed; and the recorder's
  observation time with timezone. Keep recorder labels separate from service IDs.
- **Outcome and provenance:** state, safe result excerpt, surfaced reason, exit
  status or receipt, and whether evidence is a direct result, preserved result,
  attributed worker report, or independent readback.
- **Reconciliation:** observed effect, supporting evidence reference, later
  approval or retry receipt, remaining uncertainty, next owner and supported
  observation. Preserve each attempt instead of overwriting a denial.

Distinguish planned, submitted with outcome unknown, running, awaiting approval,
denied, succeeded and failed, attaching evidence for the recorded state. Admission
proves receipt, not execution. Approval does not establish that execution started
or succeeded. Denial alone does not certify
nonexecution; retain the tool's execution statement or the worker attribution.
Timeouts, transport loss and missing receipts remain unresolved until reconciled.
The [canonical retry limits](FLEET_HANDOFF.md#retry-and-admission) still apply.

Record unexposed values as unknown (or null), with the reason; do not invent IDs
or timestamps. Keep credentials and sensitive payloads out of receipts. Label
redacted excerpts and omissions instead of calling them complete unchanged
results. A file hash verifies preserved bytes, not an authentic execution trace.

Use only views actually exposed by existing authorized tools or exports.
Documentation of a capability does not establish its availability. Readback
corroborates external state at observation time, not earlier reviewer inputs or
a complete execution history. Missing detail calls for the next supported
observation or an explicit visibility limit, not internal-storage access, a
worker resume, fork, or restart, broader access, or renewed approval merely to
fill a field.
Preserve the original owner, deadline and holds while recording these limits.

Read back a durable save before calling it preserved. Check identity and contents,
not merely that the upload command returned. Preserve the previous verified copy
until the new one is verified. For guarded updates, a revision conflict calls for
reconciliation rather than overwriting another writer's changes.

### Carry applicable authority through continuation

In the existing private handoff, retain the original user-grant locator and actual
scope, the specific action, candidate and destination it covers, and the admitted
instruction separately. Distinguish implementation, publication, readiness and
merge; authority for one does not by itself establish authority for the others.

Reuse applicable existing authority without asking again solely because of a new
turn, elapsed time, a covered routine slice or a qualification-only continuation.
This does not extend expired or time-limited authority. Establish genuine scope
changes, withdrawals, unmet requirements and required confirmations from their
actual sources. A missing reference calls for supported evidence recovery or an
explicit uncertainty, not an invented absence of permission.

Consult current saved rules through their supported authoritative source. Keep
their contents out of the runbook, and keep assistant summaries distinct from
original user-grant provenance.

Successful earlier operations neither prove a denial-free period nor explain
hidden reviewer decisions or grant authority themselves. Preserve exact exposed
outcomes and their evidence limits. An actual denial remains subject to the
existing retry rules; repeating already-used authority is not materially new
evidence. Continue independent authorized work and report the precise remaining
blocker.

These practices add no wording cure, execution gate, logger, permission expansion,
bypass or automatic enforcement. Existing custody, original deadlines, uncertainty
safeguards and substantive holds remain controlling.

### Learn from observed operational denials

When a worker or coordinator observes an operational approval or access denial,
preserve the receipt in the existing private lane record and reconcile uncertain
execution. As an ongoing response, the coordinator initiates a bounded read-only
comparison of the action, candidate, destination, original grants, admitted
instructions, and exposed result, with focused independent challenge. Record an
evidence-supported procedural correction or an explicit no-change finding with
its evidence. Continue unrelated authorized work; this review does not block it.

Link repeated reports of the same known incident instead of duplicating
investigations. Keep different actions, attempts, and materially different
evidence separate; leave unknown incident identities unresolved. Expected
negative-control refusals remain qualification evidence. Record argument-binding
failures separately from approval denials. Repeated denial alone requires neither
another amendment nor a broader approval request.

Retain full available source-reference identifiers and mark unresolved shorthand.
Scope each readback claim to its actual query. Distinguish original returned
results, preserved recorder-authored wrappers, coordinator summaries, attributed
actor reports, and independent service observations. Missing original operation
identifiers, event times, and reviewer inputs remain unknown. Capture weaknesses
do not establish a denial's cause, and this procedure does not claim to fix
approval review.

This response uses ordinary supported coordination when a denial is actually
observed. It installs no detector, universal logging, monitoring infrastructure,
or automatic enforcement; creates no execution gate; and grants no denied-action
retry, bypass, broader data collection, polling, or permission change. Existing
custody, original deadlines, grants, denials, uncertainty safeguards, and all
holds remain controlling.

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

## Recover an engineering partnership

The user sets direction and decides substantive changes outside existing
authorization. An engineering design partner may work alongside the code owner
without taking code custody. Keep one production-code owner, a separate design
partner, and independent evidence review.

Before sending work, the coordinator reconciles supported task state, current
source and candidate identity, ownership and write fences, original task
lifetimes, grants, denials, and uncertain operations against existing private
records and project instructions. A reset renews none of them. Resolve uncertain
admission through supported observation before replaying a request.

Carry source-grounded counterexamples and tradeoff findings through the
coordinator at the code owner's next natural task boundary, subject to current
user direction. Preserve frozen work; keep implementation with its owner rather
than interrupting or launching competing work. The code owner evaluates findings
against the current candidate. The design partner challenges mechanisms and
tradeoffs within its assigned scope. Independent review records evidence and
disposition without expanding authority or replacing runtime qualification.

Record actual reading and application during legitimate work in the existing
private lane record: source/candidate identity, the decision, and its observable
result or remaining uncertainty. Saved guidance, delivery, and receipt-only
acknowledgment establish neither application nor automatic enforcement or
installed supervision. Recovery preserves all existing substantive holds,
pending or uncertain operations, and their original owners and deadlines. This
guidance grants no execution or merge authority.

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
