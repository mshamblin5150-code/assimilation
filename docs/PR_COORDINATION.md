# PR coordination: verify checks and preserve instruction scope

Use this procedure before changing PR readiness, waiting for CI, investigating a denied or disputed action, carrying approval conditions into a handoff, or coordinating work after a reset. Keep the [canonical fleet handoff](FLEET_HANDOFF.md) authoritative for ownership, denied actions, uncertain admission and original deadlines.

## Short correction

Before readiness changes or CI waits, inspect this repository’s actual workflow triggers, exact-head checks/statuses and applicable requirements. Bind each instruction to its original reply context, repository, PR/action, artifact/head and conditions. Empty checks, aggregate pending with zero statuses, or marking ready do not prove a test job ran or will run. Keep targeted approval conditions within their project and action. Preserve real requirements, holds, denials, uncertain operations and original handoff deadlines; continue only independently authorized work.

## 1. Bind the instruction to its target

Read the instruction together with its original reply context. Record the repository, PR or action, exact artifact or head, explicit conditions, and the person who owns the decision. Separate a targeted reply from a standing instruction. A CI-green condition on one repository's evidence PR does not become a standing condition for another repository; an approval in the second repository does not authorize the first.

A worker reading an instruction establishes what that worker read, not what an external action reviewer received. Keep available worker instructions, submitted tool evidence and reviewer input distinct; unavailable inputs remain unknown.

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

## Denied or disputed action evidence

For an investigation, reuse the existing private lane record and the [operation receipt outline and visibility limits](FLEET_RESET_RECOVERY.md#operation-receipts-and-visibility). Retain only supported evidence:

- The attempted repository, PR/action and head or artifact, with the actual tool result and known execution status. Attribute a worker's report when the raw result is unavailable.
- The original scoped instruction or approval locator and material disclosures, including retained failures, absent hosted checks and requirement-visibility gaps.
- The instructions actually admitted to the executing worker and its acknowledgment, separately from evidence available to the action reviewer.
- Any later scoped approval and separate readiness and merge receipts. Record the denied and accepted outcomes together; later success does not erase the denial.

Mark missing inputs unknown. Compare the records before attributing different outcomes to wording. A stronger instruction, earlier success on another candidate or local review does not establish why an action was accepted. Keep retained failures and compatibility holds visible.

This is a diagnostic aid, not a new routine approval gate or request to renew valid authority. Follow the [canonical retry limits](FLEET_HANDOFF.md#retry-and-admission); preserve ownership, original deadlines and independent authorized progress. A new task or route is not a way around a denial.

**Done:** the existing record separates observation, attributed report and unknown inputs, with one owned next action or precise blocker. A causal explanation remains unresolved unless the available comparison supports it.

## Dated example: zero check records

On November 7, 2026, an authorized source inspection found a reviewed private-repository head with zero check runs and an aggregate pending status with zero individual statuses. Its only listed workflow performed issue dependency reconciliation on issue events, a schedule and manual dispatch; it had no pull-request or ready-for-review trigger. The PR's local tests and reviews remained separate evidence. The branch-rules endpoint was unsupported, leaving external or branch requirements unestablished as absent.

This is a sanitized observation, not a hosted pass, permission grant or universal statement about that repository. Exact private repository identifiers and approval records remain in the operator's private runbook. Reinspect the actual target on every use.

## Dated investigation: denial followed by scoped approval

A November 8, 2026 investigation retained a worker-reported readiness denial and nonexecution, a later exact-head approval acknowledging retained failures and absent hosted checks, and subsequent readiness and merge outcomes verified through repository records. Another case had verified external outcomes but missing executing-call and denial details. Earlier overnight successes involved different candidates, not a controlled causal comparison; retained failures and compatibility holds were not waived.

Two independent adversarial reviews examined the diagnosis and handoff. They did not reproduce the approval system or recover its raw denied/accepted inputs. The evidence supports recording the scoped approval and execution alongside the denial, not claiming that broader or stronger wording guarantees acceptance, that the original authority was insufficient, or that a transmission failure occurred. Readiness and merge remain separate actions.

## Worked comparison of separate interruptions

A November 9, 2026 comparison distinguished three events that should not be
collapsed into one approval problem:

- An interim coordinator instruction explicitly prohibited publication. The
  worker stopped before attempting it. The restriction was later released and
  publication and merge were verified. This explains that stop, not unrelated
  automatic denials.
- Another worker intended and attempted draft publication, then reported an
  automatic rejection and asked for clarification. That sequence is not a
  voluntary request for fresh consent before acting. Missing original-grant and
  destination references in its immediate handoff were useful to repair, but
  were not established as the rejection's cause.
- A merge attempt was reported denied over an unproven check condition. A
  subsequent instruction forwarding authorization was separately rejected before
  admission. A coordinator attributed a later successful forwarding attempt to
  new requirements evidence; repository readback verified the eventual merge.
  The forwarding report was not an original request envelope or reviewer-input
  record, and the final state did not explain the earlier decisions.

Apply the existing procedure by carrying original authority and question
context, the established destination and covered actions, current candidate,
actual requirements, and any phase restriction or release separately. A hash
identifies bytes; a grant establishes authority; an execution receipt establishes
an observed outcome. These are different kinds of evidence.

In the reviewed example, the draft was published for final-byte source review
before merge. That sequence does not establish a universal pre-upload review
requirement. Newly available original authority evidence
can be materially new; repeating an assertion is not. Any retry still follows
the canonical limits.

A later worker reported saving and reading back the correction, then reported a
separate readiness denial. That report does not independently verify the saved
record or establish that the correction resolves approval review. The comparison
establishes no single hidden cause, wording remedy, new approval gate or changed
hold.

## Verification and publication limits

The correction adds documentation only. It changes no workflow, check producer, protection setting, permission, hook, task custody or approval rule. Existing [controlled reset-recovery evidence](../evals/reset-recovery/2026-11-07/) remains separate; this text does not rerun those experiments or establish automatic recovery.

This update incorporates the general guidance in private runbook revision 14, dated November 8, 2026 (23:06 UTC). It is a sanitized publication, not a full export or a second operational record. The private runbook remains the source for incident details and adoption receipts. Public content excludes private source links, repository identifiers, task/message identifiers, transcripts, approval payloads, account metadata and personal data.

## Adoption at a natural boundary

At the next assignment or handoff, the coordinator supplies the short correction and this document's exact revision. The recipient acknowledges the procedure in its own task record. Preserve active slices and the original handoff deadline, at most 24 hours or the earlier assigned limit. Record stored guidance, delivery, acknowledgment, observed use, synthetic drills and automatic enforcement as separate claims; a saved file, acknowledgment or successful drill proves no live enforcement.

## Sources

- [Canonical fleet handoff](FLEET_HANDOFF.md): ownership, evidence, retry limits, private records and deadlines.
- [Swarm operating model](SWARMS.md): command hierarchy and bounded coordination.
- [GitHub workflow events](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows): event and draft/readiness behavior must be checked in the actual workflow.
- [GitHub checks API](https://docs.github.com/en/rest/checks/runs#list-check-runs-for-a-git-reference): inspect check records for the exact reference.
- [GitHub combined status API](https://docs.github.com/en/rest/commits/statuses#get-the-combined-status-for-a-specific-reference): inspect the individual statuses as well as the aggregate state.
