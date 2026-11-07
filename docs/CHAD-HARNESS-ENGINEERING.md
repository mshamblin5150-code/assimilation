# Chad's practical lesson: one inspectable agent slice

Use this lesson to see what a harness adds to an ordinary coding conversation.
Read the [guide](HARNESS_ENGINEERING.md), then the existing
[practice organizer lesson](CHAD-ORGANIZER.md). Everything below uses invented
practice data. It is a proposed exercise, not a report that these steps ran.

## Choose one observable outcome

Ask the agent:

> Read the project instructions and the actual TDD and P-Stack references linked
> by the harness guide. In an authorized disposable practice copy, investigate
> whether an organizer preview remains valid after a listed file changes.
> Start with inspection; preserve existing behavior and unrelated work.
> Propose the exact test seam and allowed command before executing anything.

The existing public seams are organizer `preview` and `apply`.
The existing `test_changed_after_preview` already exercises stale-input refusal.
Search and read it before proposing a duplicate implementation. Finding the
behavior already covered is a useful result, not a reason to invent a defect.

The intended outcome is precise: preview synthetic garden.txt, change its bytes,
then applying the stale plan refuses without moving the changed file. This
teaching program assumes a quiet test-owned folder; it does not prove hostile
concurrent-writer protection or installer security.

## Use the three checkpoints

These apply the guide's proposed before/during/after slice practice.

1. **Before:** name the test-owned scope, source revision, existing test and
   permitted command. Done means both the reader and agent can state the expected
   refusal and what must remain unchanged.
2. **During:** inspect the existing test and source first. If execution is
   authorized, run only the selected synthetic exercise with an existing
   interpreter. Keep the actual output and label skips or errors honestly.
   Stop dependent work on an uncertain operation; preserve its identity.
3. **Before finishing:** compare the exact artifact and observed result with the
   promise. Have a separate reviewer seek a counterexample where available;
   otherwise disclose sequential self-review. Record the remaining human choices.
   Passing a practice check does not approve a real move or the Windows installer.

## Make evidence disagree with a wrong claim

Have the reviewer challenge these statements:

| Claim | Evidence needed |
| --- | --- |
| The stale preview was refused | Actual refusal through apply, not an internal helper call |
| The file stayed intact | Readback of the synthetic file in its expected location |
| The test can detect a move | An authorized positive control using an unchanged synthetic input |
| No new code is needed | Existing source/test references and their actual scope |
| The exercise is complete | Result, source identity and all unresolved checks recorded |

If code really needs changing, agree the public seam first and use a focused
RED/GREEN cycle. If the existing test passes, report inspection or regression
verification; do not relabel it as a new test-first implementation.

## Rehearse an interruption without causing one

Write a short handoff from the actual exercise state. Include:

- The selected practice scope and exact source revision.
- What was inspected versus executed; command, outcome and evidence.
- Whether an operation is still running, denied or uncertain.
- Who owns the next action and what approval remains.

Then ask a fresh reader to explain the next safe action using only that record.
Do not kill a process, rerun a move or delete evidence to simulate a handoff.
A missing result means reconcile the existing operation, not start another one.

## Finish with human judgment

Ask: “What does this evidence prove, what does it not prove, and what remains
my decision?” A correct answer separates synthetic behavior from native
qualification, review from acceptance, and a preview from approval to move files.

The organizer's explicit approval sentence and journal rules still apply to any
actual practice move or undo. This lesson does not authorize personal-folder
access, installation, security changes or public posting.

Continue with [context handoff practice](CHAD-CONTEXT-HANDOFF.md) and
[evidence retrieval practice](CHAD-EVIDENCE-FIRST.md).
The linked gist and four primary readings are indexed in the harness guide;
read them as references, not instructions that override the project.
