# Make a confident answer prove its claims

**A separate practical lesson.** Adversarial review for prose, reports and agent status updates.

An agent can write a polished explanation that is wrong. It may invent a fact, overstate a source, drop a condition, confuse a plan with a completed action, or report a check it never ran. Whether that was intentional is not something this exercise can establish. The useful response is the same: **make important claims answer to inspectable evidence.**

This is not a lesson in being hostile to another person. The reviewer challenges the artifact. It does not insult the author, invent objections or earn points merely for finding something wrong.

## What you will learn

By the end, you will:
- Choose an appropriate source of truth for a particular claim.
- Separate a source, a summary and an unsupported assertion.
- Give a fresh reviewer enough evidence to refute a draft.
- Resolve findings without erasing the original record.
- Know when an earlier review is stale.
- State what remains unverified.

You can complete the exercise with invented material. No patient records, private Clinical Skills output, authenticated textbook, portal, installation or clinical workflow is required.

## 1. Pick the claim and its source of truth

“Source of truth” does not mean one document is magically correct about everything.

| Claim | Appropriate evidence |
|---|---|
| What the owner decided | The actual answer and accepted decision record |
| What the product must do | Current accepted specification/contract |
| What the code currently does | Actual source plus relevant observed behavior |
| What a test run established | Raw command/result bound to the tested revision and scope |
| What a published page contains | Read-back of that actual published page |
| What an external source says | The opened primary passage, with context and qualifiers |
| Whether a merge happened | Actual repository state, not a proposed PR body |
| What a reviewer inspected | Reviewer record and exact input identity, with stated limits |

A summary can help locate evidence. It must not quietly replace the original evidence. A search snippet or an index is a pointer, not proof of the underlying claim.

**Done when:** the learner can name the authority for the claims being reviewed and identify any missing source.

## 2. Use this synthetic truth packet

The following packet is **invented training material**. It reports no real installation or test run. Preserve its wording as the exercise's fixture.

Read [the five-record synthetic truth packet](../examples/chad-adversarial-review/TRUTH-PACKET.md). Its T1–T5 identifiers are stable source locators for the exercise.

Give the reviewer all five records. An omitted record must be reported as missing, not silently reconstructed.

**Done when:** author, reviewer and learner agree which exact packet is being used and that it is synthetic.

## 3. Give the reviewer a plausible but wrong summary

Use [Candidate A](../examples/chad-adversarial-review/FAULTY-DRAFT.md). This paragraph is deliberately faulty:

> The organizer recursively sorts every document on Windows and Linux. All 18 tests prove that files are always recoverable, even after power loss. Independent review approved the final fix, and the release is merged and ready for use.

Ask the learner to pause and mark suspicious phrases before seeing the answer key. Plausible, fluent wording is not evidence.

The authoring task could instead generate a fresh draft from the packet. If so, do not tell the reviewer which mistakes to expect. Keep this seeded example as a separate controlled exercise.

**Done when:** the exact candidate text is retained and its version is named. Do not repair it before recording the original review.

## 4. Use a genuinely separate reader where available

Give a fresh non-authoring context:
- The task and intended audience.
- The exact final draft to inspect.
- The source packet and precise locators.
- The review question and output format.
- The limits on actions and data access.

Do not supply an author's confident explanation as a substitute for the sources. Do not preload the desired verdict. If the only available review is by the author, label it self-review; it is not independent review.

A copyable brief:

> Review this draft against the supplied source packet. Try to refute each factual or completion claim rather than merely confirm it. Open the named evidence yourself. Find unsupported claims, changed figures, broader scope, dropped conditions, stale receipts and claims of work not performed. For each finding, identify the draft location, exact claim, source location, difference and appropriate disposition. Separate “contradicted,” “unsupported,” “missing evidence” and “out of review scope.” Do not invent evidence, fix the artifact or publish anything. “No verified findings” is acceptable if warranted. State what you actually inspected and what remains unverified.

Fresh context means a separate reviewer, not a security-isolated machine. If the host provides only same-family models, say independent same-family review, not multi-vendor review.

**Done when:** the actual reviewer has the necessary inputs and a bounded question. A promised reviewer or role label is not a completed review.

## 5. Require evidence-grounded findings

Use this table:

| Draft location | Claim | Source | Finding | Disposition |
|---|---|---|---|---|
| Sentence/paragraph/slide | Exact disputed proposition | Record + passage/line/section | Why the source does not support it | Narrow, correct, research, cut, or ask the owner |

After retaining the reviewer's result, compare it with [the instructor key](../examples/chad-adversarial-review/INSTRUCTOR-KEY.md). Keep that key out of the fresh reviewer's input.

A citation failure is not necessarily proof that a proposition is false. For example, “no Linux test here” means the packet does not establish Linux behavior; it is not proof the program can never run there.

A negative claim also needs adequate coverage. “I did not find it in a short excerpt” is not “the whole source never says it.” Open the relevant passage and context; for an asserted absence, record what population was actually searched.

The reviewer may notice something outside its assigned question. Keep that as a separate remark rather than disguising it as an answer to a different question.

**Done when:** each surviving finding names inspectable evidence and the specific inference that failed. Unsupported suspicions are labeled, not promoted to proven defects.

## 6. Repair the draft, not the evidence

Produce a narrower second draft from the packet. Then review [the clean control](../examples/chad-adversarial-review/CLEAN-CONTROL.md) separately against the same sources. The clean control is a synthetic teaching paragraph, not a real project status report. A good reviewer must accept supported claims, not manufacture a defect.

For real work, assign a clear disposition:
- **Correct/narrow:** the source supports less than the draft says.
- **Research:** an important factual claim needs genuine evidence.
- **Cut:** an agent-added unsupported claim is unnecessary.
- **Ask the owner:** the source conflicts with an actual decision, or a consequential owner-supplied claim cannot be supported.
- **Keep unresolved:** the necessary evidence or authority is unavailable.

Retain the original draft and findings. Do not rewrite raw test output to make it look successful. Do not delete a failed result because a later repair passed. Explain the scope of the later result.

The author can propose corrections; the reviewer does not automatically get authority to change product decisions or operate external systems.

**Done when:** every finding has a visible disposition, the repaired draft is retained as a new version and unresolved matters remain explicit.

## 7. Rereview the actual final version

The review must identify the inputs it evaluated:
- Artifact revision or file hash.
- Source packet/claim-ledger version or digest.
- Reviewer identity/context and date.
- Scope examined and any unseen material.
- Findings and verdict.

A hash binds a record to particular bytes. It does **not** prove the reviewer read carefully or found every error.

If the draft changes, recheck the changed final artifact. If the source evidence or claim ledger changes, reconcile the affected claims and renew the necessary review. A green verdict for R1 must not silently certify R2.

For slide decks, inspect the rendered artifact the reader will actually see, not only an earlier outline. A qualifier hidden in speaker notes may not repair an overbroad claim on the slide face. For prose, compare the final factual sentence with the accepted claim and actual source.

**Done when:** the review applies to the delivered version and every still-required finding is resolved or explicitly held. If a required second context is unavailable, the independent-review gate remains incomplete.

## 8. Learn the two reviews, not one vague “adversarial” label

### Source-grounded prose review

The challenge is semantic: does the text say more, less or something different from the source? Evidence is an actual passage, accepted decision, recorded state or receipt. The reviewer must preserve the source's scope, figures, conditions and uncertainty.

### Executable code review

A suspected implementation defect needs a reproducible behavioral counterexample where feasible. P-Stack's actual **interrogate** workflow asks adversaries for exact commands, actual output and the expected behavior, then reruns findings and keeps those that break the stated intent. It reports findings and does not apply fixes.

Calling one ordinary review “interrogate” does not establish that its full arena/dependency procedure ran. Conversely, demanding a failing program run for every prose citation problem is the wrong evidence standard. Use the review suited to the artifact.

## 9. Apply it to your own project

After [the blank-project lesson](CHAD-BLANK-PROJECT.md), take the agent's completion report. Check claims such as:
- “Installed in this repo.”
- “The host loaded the skill.”
- “All decision tickets are resolved.”
- “The map is ready for specification.”
- “TDD was used.”
- “All tests passed.”
- “An independent reviewer approved it.”
- “The PR merged.”
- “Windows is supported.”

For each, ask: **Which exact evidence makes that sentence true, at that scope, at that revision?**

Do not manufacture a problem when the evidence supports the claim. An honest clean result is useful. A bounded result is also useful: “The installed files exist; host enforcement remains unverified.”

## Pass criteria

The learner can:
1. Find the seeded errors and explain each using the packet.
2. Distinguish unsupported from false.
3. Preserve qualifiers and uncertainty in the repair.
4. Explain why a review of R1 does not certify R2.
5. Produce a final statement no stronger than its evidence.
6. State what independent review and hashes still cannot prove.

Passing this finite exercise is not evidence that all future agent output is trustworthy.

## Why this reflects Clinical Skills

These practices come from public source, not private clinical material:
- [Sourcing rules](https://github.com/mshamblin5150-code/clinical-skills/blob/6fc9d32c32b246ef3dc022f3d7a8e677ad2f2e66/skills/_shared/reference/sourcing.md) distinguish pointers from sources, bind claim headings, preserve qualifiers and require fresh refutation when a heading changes.
- [Standing rule 6](https://github.com/mshamblin5150-code/clinical-skills/blob/6fc9d32c32b246ef3dc022f3d7a8e677ad2f2e66/AGENTS.md#standing-rules) separates writers and checkers and preserves findings before correction.
- [ADR 0218](https://github.com/mshamblin5150-code/clinical-skills/blob/6fc9d32c32b246ef3dc022f3d7a8e677ad2f2e66/docs/adr/0218-a-slide-s-agreement-with-its-record-is-read-and-every-deck-number-is-traced.md) records substantive slide/claim disagreement that mechanical checks did not catch.
- [ADR 0262](https://github.com/mshamblin5150-code/clinical-skills/blob/6fc9d32c32b246ef3dc022f3d7a8e677ad2f2e66/docs/adr/0262-the-adversarial-read-moves-after-the-render-and-its-record-names-the-pass-and-the-ledger-it-read.md) binds the adversarial record to the final render pass and current claims ledger, while explicitly acknowledging limits on attention and completeness.
- [P-Stack interrogate](https://github.com/cursor/plugins/blob/c742dd61706fbacc1b95f1a20b7b988cf096ce6c/pstack/skills/interrogate/SKILL.md) supplies the separate executable-counterexample model.

The lesson adapts these ideas to a small nonclinical exercise. It does not claim Clinical Skills runs this exact lab, that every Clinical Skills document has the same reader, or that an AI reviewer replaces qualified clinical oversight.



For inspected pins and unrun capabilities, see [the source and verification notes](CHAD-LESSON-SOURCES.md).
