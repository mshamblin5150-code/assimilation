# Fleet handoff: preserve ownership and actual state

Use this rule when starting, resuming, delegating, stopping, or handing off an
authorized task. Project instructions and current operator limits remain in
force. This supplements the selected engineering skills; it restores none of
DAVID's retired drone ceremonies. Reuse the task's existing private run record.
The decision and enforcement limits are recorded in
[ADR 0011](adr/0011-fleet-handoff-state-and-structural-check.md).

## Start or resume

1. Read the actual project instructions and relevant skills at the current
   revision. Record the repository, revision, ticket (or explicit untracked
   request), objective, allowed work, holds, owner, and coordinator.
2. Read the latest handoff and reconcile it against supported task status,
   repository state, and receipts. Distinguish a completed turn from completed
   work, and reported activity from confirmed admission or execution. Claim one
   writer per artifact; resolve overlapping ownership before writing.
3. Name the next authorized action, observable success condition, and stopping
   condition. Carry the original task start and handoff deadline when resuming.
   The fleet's task handoff interval is at most 24 hours; a shorter assigned or
   platform deadline wins. A resume does not reset it.

Start is established when these facts and any unresolved admission are recorded.
When admission is uncertain, reconciliation is the next action for that operation;
independent authorized work can continue with its own owner and record.

## Before stopping or handing off

1. State what actually changed and its current state: not started, running,
   blocked, or complete. Keep failures visible. Give exact artifact/revision and
   test or readback references, separating executed, read, and untested claims.
2. List pending operations and their IDs. A running operation remains owned;
   ending a turn, losing a connection, or reaching a retry deadline does not make
   it complete, canceled, failed, or safe to repeat.
3. For every blocker, record the exact action and target, observed outcome,
   reason (or unknown cause), what was tried, and the remaining authorized local
   and cloud alternatives. State why a route is available, unavailable, blocked,
   or inapplicable. Name the smallest real missing input or approval; avoid
   inventing a new gate when supported source facts or another allowed seam suffice.
4. Record the next owner, next action and success condition. At the task deadline,
   hand off actual state and operation IDs to the coordinator. Reconcile existing
   work before a successor starts; a new name or executor never clears a hold.

Complete means the requested outcome and its required verification/acceptance
are established, with no pending operation or blocker. Otherwise preserve an
incomplete state and an owned continuation. User-requested stopping remains valid;
record what remains rather than relabeling it complete.

## Retry and admission

- A 15-minute retry window governs attempts to start or retry the named operation,
  not the duration of admitted work. Record its actual start and expiry; continue
  admitted work to its authorized result or genuine stop condition.
- Check uncertain outcomes through supported records before repeating. Missing
  messages or an old completed turn alone do not prove a new request never ran.
- A genuine safety or access denial stops that route. A retry needs materially
  new, relevant evidence and a known non-executed outcome, and is made only once
  per such evidence. Carry the original denial and new basis into the handoff.
  Time elapsed alone is not new evidence. An uncertain denied operation must
  first be reconciled. Respect stricter tool-specific retry restrictions.
- Evaluate only alternatives already within authority. Another account, host,
  proxy, executor, endpoint, or permission change is not a way around a denial.
  Local work needing the user's clicks waits for the required approval and
  check-in; continue independent permitted work without waking the user.

## Coordinator check

Read the handoff, verify the consequential claims against current supported
evidence, and compare them with the requested outcome. Keep active work with its
owner. Reconcile uncertain admission before resending. Assign useful authorized
unowned work; escalate only the precise remaining decision or access need. Record
who accepted the continuation and its original deadline. A missing or malformed
handoff is an incomplete coordination record, not authority to duplicate work.

## Optional structural check

`python scripts/check_fleet_handoff.py path/to/private-handoff.json` checks the
version 1 JSON fields illustrated in
[`templates/FLEET_HANDOFF.json`](templates/FLEET_HANDOFF.json). Keep real records
private; never commit PHI, credentials, private transcripts, or sensitive evidence.
Use references and minimal safe summaries, not copied patient or account content.

The command reads only the supplied record, performs no task or network action,
and prints field-level findings without echoing record values. Exit 0 means the
record is structurally consistent, **not** that claims are true, work is complete,
permissions exist, or every alternative was considered. Exit 1 means a structural
finding; exit 2 means unreadable or invalid input. All fields are required; empty
lists are explicit none. Evidence references are locators, not automatically read.
Input is one UTF-8 JSON file, at most 256 KiB, with unique keys and no non-JSON
constants. Timestamps must include UTC. The check compares recorded times; it
does not certify their truth or poll a clock, host, repository, or task service.

Existing Assimilation PR validation discovers the synthetic checker tests. That
tests the checker, not real task handoffs. No turn-stop hook is installed by this
change. A repository pointer, a local invocation, a CI run, and a live host hook
are distinct adoption claims. Add a host adapter only after its documented event,
permissions, private record location, independent review, and actual behavior are
verified. Preserve existing PHI, clinical, product, security/data, persistence,
native, teardown, and approval checks. Never change branch protection or host
permissions merely to make this check mandatory.

Retire this checker if an existing supported handoff mechanism covers the same
failures; retain the ownership, evidence, and safety requirements in that mechanism.
