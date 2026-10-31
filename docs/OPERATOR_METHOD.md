# Matt's working method: grilling with ADRs

This is the repository's default method for design interviews. Every coordinator
and drone using this repository must read it before asking design questions.
It records Matt Shamblin's explicit instructions, including his request that
Chad's drones can follow the same method from repository files alone. A target
project's more specific instructions and its operator's explicit directions take
priority; Matt does not become the decision owner of Chad's work.

Use `grill-with-docs` when substantive design choices need discussion. Read the
actual `grill-with-docs`, `grilling` and `domain-modeling` skills and required
references. Preserve their invocation restrictions. This method supplements the
original sources and overrides their whole-frontier question batching with one
decision at a time. A small, understood change or factual query can use its direct
route without an interview.

Read these original sources when applying this method:

- [Grill with docs](../upstream/matt-pocock/skills/engineering/grill-with-docs/SKILL.md).
- [Grilling](../upstream/matt-pocock/skills/productivity/grilling/SKILL.md).
- [Domain modeling](../upstream/matt-pocock/skills/engineering/domain-modeling/SKILL.md), including its required formats/references.
- For incoming tickets, [triage](../upstream/matt-pocock/skills/engineering/triage/SKILL.md) and its brief/out-of-scope references.

The copies preserve their publishers' invocation restrictions. An explicit user
invocation or another valid authorization must satisfy any user-only restriction;
this guide is not permission to invoke a restricted command automatically.

## The repeatable loop

1. **Read before asking.** Establish the outcome, source evidence, current ticket,
   glossary, relevant ADRs, prior answers and decision owner. Investigate facts
   yourself. Keep unknown facts separate from choices only the operator can make.
2. **Explain the blockage.** State why a decision is necessary before showing
   choices. Use ordinary words; explain the effect on the person using the product.
3. **Ask one decision.** Present the complete set of credible options for that
   decision, with costs and a recommendation, using the exact format below.
4. **Wait and interpret narrowly.** A reply such as `a` or `b` settles that option
   for that question. Preserve the answer across turns. New user messages steer
   the active work; they do not erase prior decisions unless they change them.
5. **Write the ADR now.** Each substantive design interview has an ADR record.
   Create or update the relevant ADR as significant decisions land, rather than
   waiting until the interview ends. Group related decisions in the same ADR;
   a trivial clarification does not need its own file. Update agreed domain terms
   in the canonical glossary; keep technical design in the ADR/specification.
6. **Recompute what remains.** Ask the next independent blocking decision only
   after its prerequisites are settled. Use judgment for routine implementation
   details; ask about consequential product choices and unresolved authority.
7. **Confirm the finished design.** Summarize the agreement and use the exact
   closing line below when the decision frontier is empty. After confirmation,
   proceed within existing authority and preserve any separate gates.

## Exact question format

Before the question block, explain the uncertainty, relevant facts and lettered
options. State each option's concrete cost or consequence. Then use:

```text
[Why this choice is necessary, in plain words.]

A. [Choice and concrete cost.]
B. [Choice and concrete cost.]
[Include other credible choices where applicable.]

❓ [Exactly one decision question referring to those choices.]

➡️ Recommend [letter], because [reasons].

Held for later: [specific deferred decisions, or nothing.]
```

One decision can have clarifying questions inside its single `❓` block, but the
block must not hide a second decision. Do not bundle unrelated decisions. Explain
all options for the question; a recommendation alone is insufficient. Avoid
internal labels, row numbers or implementation jargon that the operator must
translate before deciding.

When no decision remains, write this exact closing line:

**Frontier empty — confirm shared understanding.**

Wait for shared-understanding confirmation before acting on the completed design.
Continue already authorized independent work while a question is pending. Do not
ask for permission already supplied, and do not treat silence as an answer.

## Worked question and response

Suppose the operator must choose how an optional diagnostic signals failure:

> The requested check can fail while the rest of the diagnostic report is useful.
> We need automated callers to know whether that requested check completed.
>
> A. Return success with a failed-check field. Cost: callers must inspect the
> report to notice the failure.
>
> B. Return an error status and keep the report. Cost: callers must handle the
> error status, but the failure is immediately visible.
>
> ❓ Should a failed requested check use A or B?
>
> ➡️ Recommend B, because the command should signal that the requested work failed.
>
> Held for later: execution limits and acceptance tests.

If the operator replies `b`, update the relevant ADR immediately: record the
owner's choice, why B was chosen over A, its effects on callers, and what remains
unresolved. Do not ask the same choice again, start implementation or mark the
whole design accepted. Investigate routine technical details and continue with
the next unresolved operator decision. If none remains, summarize the concrete
design, use the closing line above and wait for confirmation.

## ADR and handoff requirements

This repository uses `CONTEXT.md` as its single canonical glossary. This is an
explicit local filename override of the bundled domain-modeling skill's
`GLOSSARY.md` / `GLOSSARY-MAP.md` convention; do not create a competing glossary.
In another target project, preserve its established glossary name and context
map unless its operator explicitly changes that convention.

Use [the ADR template](templates/ADR.md). Record who decided what, the reason,
alternatives and costs, consequences, verification evidence and remaining choices.
Mark a settled choice as accepted only for its actual scope. A partially resolved
design still has an explicit open frontier. Choosing behavior is not proof that
it works, and does not supply missing implementation or publication permission.

Before adding an ADR, inspect the existing numbering and the current remote tree
when the checkout is stale. Preserve other workers' changes. Link the ADR from
the ticket/specification or existing run record so successors can find it. An
unpublished local ADR must be described as local, not available on GitHub.

Every bounded handoff includes:

- The actual decision owner, scope, permitted work and preserved holds.
- This method and the applicable skill sources to read.
- The canonical ticket, relevant ADRs, current source revision and evidence.
- Settled answers, remaining decisions and the next authorized action.

A coordinator passes these references to its drones and checks their actual
output against the method. One agent can follow the same procedure serially.
The presence of this document neither starts a swarm nor grants delegation.

## Respect ownership and keep momentum

When Matt leaves a ticket with Chad, route that ticket's decisions to Chad within
the authority actually granted; stop asking Matt to decide them. Recording an
owner does not identify an account, authorize a message, dispatch a drone or
prove the owner has accepted the work.

Carry forward accepted classifications and choices. Reopen a decision only when
new evidence or an operator correction changes it, explaining why. In triage,
`needs-triage` means continue the evaluation; changing that label alone does not
finish the job. Use [the ticket workflow](TRIAGE_WORKFLOW.md) for tracker-specific
steps and the [Vox handoff](VOX_HANDOFF.md) for a coordinator's startup instruction.

## Checks before handing off

Read back the actual ADR and tracker changes. Report what ran, what was inspected
and what is untested. Claim independent review only when another reviewer examined
the actual work. Resolved design questions, passing tests and operator acceptance
are separate claims. Keep implementation, native probes, installation, merge and
deployment within their actual authorization.
