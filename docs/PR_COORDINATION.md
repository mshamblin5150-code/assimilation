# PR coordination: verify checks and preserve instruction scope

Use this procedure before changing PR readiness, waiting for CI, carrying approval conditions into a handoff, or coordinating work after a reset. Keep the [canonical fleet handoff](FLEET_HANDOFF.md) authoritative for ownership, denied actions, uncertain admission and original deadlines.

## Short correction

Before readiness changes or CI waits, inspect this repository’s actual workflow triggers, exact-head checks/statuses and applicable requirements. Bind each instruction to its original reply context, repository, PR/action, artifact/head and conditions. Empty checks, aggregate pending with zero statuses, or marking ready do not prove a test job ran or will run. Keep targeted approval conditions within their project and action. Preserve real requirements, holds, denials, uncertain operations and original handoff deadlines; continue only independently authorized work.

## 1. Bind the instruction to its target

Read the instruction together with its original reply context. Record the repository, PR or action, exact artifact or head, explicit conditions, and the person who owns the decision. Separate a targeted reply from a standing instruction. A CI-green condition on one repository's evidence PR does not become a standing condition for another repository; an approval in the second repository does not authorize the first.

**Done:** the private record identifies the target and conditions, with a source locator. Ambiguous scope stays unresolved. Correcting context alone authorizes neither a denied retry nor a merge.

## 2. Inventory the actual check producers and requirements

Through supported access, inspect workflow files and event/branch/path/draft/job conditions relevant to the PR, exact-head check runs, commit statuses, and applicable required checks and reviews. Separate:

- draft or ready state;
- local tests and review evidence;
- observed hosted jobs, their tested SHA, outcome and skips;
- required checks/reviews and any unavailable requirement evidence;
- authorization to publish, change readiness, merge or accept a compatibility change.

A workflow listing establishes configuration, not execution. An empty check set establishes no observed hosted pass. An aggregate pending status with zero individual statuses establishes no running job. Marking ready changes PR state; it establishes no workflow execution by itself. An unavailable rules endpoint leaves requirements unknown and does not justify expanding access.

**Done:** name each established check producer and applicable requirement, or the exact evidence gap. Record the inspection time and head. Repeat when the head or relevant configuration changes.

## 3. Choose the next authorized action

If an applicable producer is established, follow its actual event and job conditions, and observe the resulting run rather than assume it started. Do not change readiness solely to manufacture a check without authority.

If no applicable PR workflow or external producer is established, disclose that fact. Continue the next independently authorized action instead of waiting for an invented CI event. This does not waive an actual requirement, unknown requirement, review, safety hold or required decision.

Carry denials and uncertain outcomes into the handoff. Reconcile an uncertain operation before any repeat; a context correction, new task or elapsed time does not clear it.

**Done:** one owner has a concrete next action, observable success condition and stop condition, or a precise blocker.

## Dated example: zero check records

On November 7, 2026, an authorized source inspection found a reviewed private-repository head with zero check runs and an aggregate pending status with zero individual statuses. Its only listed workflow performed issue dependency reconciliation on issue events, a schedule and manual dispatch; it had no pull-request or ready-for-review trigger. The PR's local tests and reviews remained separate evidence. The branch-rules endpoint was unsupported, leaving external or branch requirements unestablished as absent.

This is a sanitized observation, not a hosted pass, permission grant or universal statement about that repository. Exact private repository identifiers and approval records remain in the operator's private runbook. Reinspect the actual target on every use.

## Verification and publication limits

The correction adds documentation only. It changes no workflow, check producer, protection setting, permission, hook, task custody or approval rule. Existing [controlled reset-recovery evidence](../evals/reset-recovery/2026-11-07/) remains separate; this text does not rerun those experiments or establish automatic recovery.

The private runbook is the operational source for the dated incident and adoption receipts. Public content contains the general procedure and sanitized observation, with no private transcript, live approval payload, account identifier or private source.

## Adoption at a natural boundary

At the next assignment or handoff, the coordinator supplies the short correction and this document's exact revision. The recipient acknowledges the procedure in its own task record. Preserve active slices and the original handoff deadline, at most 24 hours or the earlier assigned limit. Record delivery, acknowledgment and observed use separately; a saved file or unacknowledged message proves neither adoption nor automatic enforcement.

## Sources

- [Canonical fleet handoff](FLEET_HANDOFF.md): ownership, evidence, retry limits, private records and deadlines.
- [Swarm operating model](SWARMS.md): command hierarchy and bounded coordination.
- [GitHub workflow events](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows): event and draft/readiness behavior must be checked in the actual workflow.
- [GitHub checks API](https://docs.github.com/en/rest/checks/runs#list-check-runs-for-a-git-reference): inspect check records for the exact reference.
- [GitHub combined status API](https://docs.github.com/en/rest/commits/statuses#get-the-combined-status-for-a-specific-reference): inspect the individual statuses as well as the aggregate state.
