# ADR 0011: fleet handoff state and structural check

- Status: Accepted direction; repository adoption pending review
- Date: 2026-10-31
- Owner: Operator

## Context

A turn can end while useful authorized work remains. Uncertain admission can
lead to duplicate execution; a retry window can be mistaken for a deadline on
admitted work. Repositories have different hooks and independently owned changes.
The operator accepted a canonical start/end handoff and coordinator check, with
implementation limited to mechanisms the actual environment supports.

## Decision

Keep one canonical [Fleet handoff](../FLEET_HANDOFF.md) rule: start/resume
inspection, actual-state and evidence handoff, precise blocker/alternative
diagnosis, admission reconciliation, original task handoff deadline, and owned
continuation. Apply the fleet's 15-minute limit to retry attempts, not admitted
work, and its at-most-24-hour handoff interval without resetting on resume.
Preserve current permissions, stronger tool restrictions and project holds.
Reuse existing private task records instead of a public operational ledger.

Offer a read-only JSON structural checker and synthetic command tests. Existing
PR validation discovers the tests; it does not inspect real task handoffs.
Short owner-integrated pointers can reference the canonical published revision
in other repositories after scope, collisions and acceptance gates are checked.
Retain existing engineering skill authority and safety checks.

## Alternatives considered

- A universal Stop hook: unsupported as a fleet-wide claim. Host events, private
  record access and coexistence with existing hooks have not been qualified.
- Copies of the validator in every repository: creates competing definitions
  and multiple maintenance points.
- Prose alone: cannot mechanically flag contradictory completion, pending-work,
  admission, retry and deadline fields in a recorded handoff.

## Consequences

The explicit checker never runs tasks, changes settings or permissions, follows
evidence links, uploads private material, or authorizes retry/merge/deployment.
A structural pass is weaker than actual task acceptance. Coordinator judgment
must remain grounded in current evidence. No branch protection or host hook is
changed. Publication, merge, checkout adoption, owner readback, host execution
and actual acceptance remain separate states.

Retire the checker when an existing supported mechanism covers the same failures
without duplication. Reverting it changes no application data or host settings;
the underlying ownership and safety requirements remain with the operator.

## Verification and references

- `tests/test_fleet_handoff.py` exercises the public command using synthetic
  records, including refusal controls, unchanged input and non-echoed values.
- Initial independent review found two structural false passes: completed work
  with a planned retry, and an uncertain blocker with a retry. Both were reproduced
  before correction; the added controls now refuse those records.
- The completed Linux validation on October 31, 2026 used Python 3.12.14 and
  `python -B -m unittest discover -s tests -v`; source snapshot verification and
  clean-checkout onboarding checks also passed. This is local evidence, not a
  hosted-CI or native-Windows claim.
- Actual live hook enforcement and fleet-wide adoption remain unverified.
