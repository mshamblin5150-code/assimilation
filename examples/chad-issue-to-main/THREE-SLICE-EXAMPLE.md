# One parent, three slices: merge progress without claiming completion

Use with [lesson step 7](../../docs/CHAD-ISSUE-TO-MAIN.md#7-pr-checks-merge-then-acceptance).
This is a documentation exercise, not permission to publish, merge, probe a
native executable or change a real issue's state.

## Real IDs, clearly bounded history

The real parent is [issue #9 — Windows onboarding and bounded prerequisite diagnostics](https://github.com/mshamblin5150-code/assimilation/issues/9).
[PR #10](https://github.com/mshamblin5150-code/assimilation/pull/10) merged its first
read-only runtime-report slice. At the 2026-11-01 source check, #9 was **open**;
the [confirmed brief](https://github.com/mshamblin5150-code/assimilation/issues/9#issuecomment-6538185667)
still required the optional selected-executable Git diagnostic, verification
and acceptance. This checkpoint does not reconstruct every prior state change.

The three-slice breakdown below is a **teaching plan**, not a claim that three
PRs already exist. The first sample rewrites how that delivered slice could be
described; it is **not PR #10's historical title or body**. The second and third
are prospective: their evidence has not been produced by this exercise. Use
their actual PR numbers only after real creation; do not invent them in advance.
Read the current parent/brief again before doing any real work.

| Slice | Example PR title | Delivered evidence / completion target | What remains on parent #9 |
|---|---|---|---|
| 1 | Part 1 of issue #9 — read-only runtime report | Existing PR #10; exact head `640f72ac51d9853a3f0bcd010f3a9a6d886e24e9`, merged as `69d0498990ef2628f7a2f12d2d0ff367dda77851` | Selected Git diagnostic, its verification and owner acceptance |
| 2 | Part 2 of issue #9 — selected Git diagnostic and synthetic tests | Prospective implementation at the confirmed injected-process seam, exact candidate checks and independent review | Separately authorized native observation and final acceptance, as the parent requires |
| 3 | Final part of issue #9 — verification and acceptance reconciliation | Prospective final evidence/limits, integrated-source identity and owner's full parent acceptance | Nothing within the accepted parent scope; distinct installer issues/holds stay separate |

The parent is the bounded diagnostic, not the entire Windows installer. Finishing
#9 must not silently close unrelated installer work or claim installation is
qualified. A three-part plan is an example, not a mandatory number of PRs.

## Slice 1 draft — evidence delivered, parent open

The historical [exact-head CI receipt](https://github.com/mshamblin5150-code/assimilation/actions/runs/41149499901)
and parent discussion are evidence pointers to open, not tests rerun by this lesson.
For the real merge, verify the issue state immediately afterward; the current
open checkpoint alone is not proof it stayed open throughout its history.

```text
Title: Part 1 of issue #9 — read-only runtime report

Parent: issue #9 (partial delivery; keep parent open).
Delivered: OS/runtime and Python prerequisite reporting, with Git explicitly
unverified/not-probed and installation not admitted.
Evidence: PR #10; reviewed head 640f72ac51d9853a3f0bcd010f3a9a6d886e24e9;
merge 69d0498990ef2628f7a2f12d2d0ff367dda77851; exact-head run 41149499901.
Remaining: selected Git diagnostic, required verification and owner acceptance.
Next owner: the actual parent owner, currently recorded as Vox; recheck before handoff.
After merge: read back the landed slice and issue #9; expected parent state OPEN.
Record actual state and time. Do not mark the remaining acceptance items complete.
```

The phrase “Part 1 of issue #9” is a reference, not a closing directive. Keep that
same non-closing intent in the actual commit and generated merge text. The
checks in [the lesson](../../docs/CHAD-ISSUE-TO-MAIN.md#merge-a-slice-without-closing-the-parent)
also cover accidental sidebar closing links.

## Slice 2 draft — prospective implementation, parent still open

Author the next slice only within its real authorization. The parent brief
preserves a passive default, operator-selected trusted executable, bounded
output/deadline/error behavior, compatibility-unverified reporting and no
automatic discovery or repair. Its synthetic seam is not a native probe.

```text
Title: Part 2 of issue #9 — selected Git diagnostic and synthetic tests

Parent: issue #9 (partial delivery; keep parent open).
Delivery target: implement the confirmed diagnostic contract and help/docs;
retain passive default and installation refusal.
Evidence now: NOT RUN / NOT IMPLEMENTED by this teaching exercise.
Before a real PR: replace this line with actual candidate, commands, outputs,
independent review and any failures/skips. Never turn this target into a receipt.
Remaining: separately authorized native observation and final acceptance required
by the current parent; preserve other outstanding criteria if any.
Next owner: the verified owner of that remaining work, not an invented assignee.
After authorized merge: read back the landed candidate and issue #9;
expected parent state OPEN. Record the observed state and unchecked remainder.
```

Even if all synthetic tests pass, this slice does not satisfy an outstanding
native-evidence or acceptance gate. The real PR can merge only under its own
authority and current reviews/checks; no such permission comes from this sample.

## Slice 3 draft — close only after full acceptance

Do not start by assuming the word “Final” makes it final. Build a reconciliation
of **every** parent criterion: evidence location, tested revision, result/limit,
remaining hold and the owner's acceptance. Preserve significant failed results.
Obtain any separate native-probe authority before observing the named executable;
do not perform that probe as part of this lesson. Review the final integrated
behavior and exact documentation/evidence candidate.

```text
Title: Final part of issue #9 — verification and acceptance reconciliation

Parent: issue #9.
Delivery target: final scoped evidence and acceptance reconciliation.
Evidence now: NOT RUN / NOT ACCEPTED by this teaching exercise.
Closure gate: every current parent criterion is satisfied with actual evidence;
required owner acceptance is recorded; merge and closure authority are current.
If any criterion or authority is missing: keep the parent OPEN and name the gap.
If all gates are met before merge: add the closing directive only then.
If acceptance requires a post-merge check: omit it, verify after integration,
then close manually only with authority and read back the actual closed state.
```

Only when the complete gate above is met, the final PR body may include the
literal directive `Closes #9`. That line is **not** part of either partial draft,
and it must not be pasted into a real PR just to demonstrate the syntax. Verify
the actual final PR, merge commit/content and parent state afterward; record
the accepted scope and any genuinely separate follow-up issue without quietly
moving unfinished parent requirements out of scope.

## Rehearse without touching GitHub

Keep three local PR drafts and a parent checklist in the existing private
`EVIDENCE` directory from [the worksheet](README.md). After each **simulated**
merge, write the expected parent state and remaining criteria. Label those states
simulated: they do not test GitHub's automatic closure or prove a live merge.

For drafts 1 and 2, inspect titles, bodies, included commits, merge/squash previews
and closing links. Show why a hidden parent-closing directive makes the draft
unsafe even when its title says “Part.” For draft 3, first leave acceptance
missing: the correct outcome is still open. Then supply a clearly invented
accepted fixture and explain the authorized closing path. No live issue is
closed, reopened or rewritten in this exercise.

**Pass:** the learner can show two partial delivery receipts with an open
parent, explain each remainder, and refuse final closure while any acceptance
or authority is missing. Read back actual states in real work; never substitute
these sample states for observations or guess why an unrelated issue closed.
