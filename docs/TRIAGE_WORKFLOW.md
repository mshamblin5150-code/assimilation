# From incoming ticket to an agreed agent brief

Use this workflow when triaging an incoming request whose intended behavior still
needs decisions. It connects the original `triage`, `grill-with-docs`, `grilling`
and `domain-modeling` skills; read their complete sources and required references.
Respect their invocation restrictions and the host's available tools. This guide
does not install slash commands or activate copied upstream configuration.

For a small, fully understood request, complete triage directly. Tickets already
produced by `to-tickets` are agent-ready by construction; do not restart triage.
For an uncertain multi-session project, use the [larger planning route](WORKFLOW.md#large-uncertain-projects-from-map-to-implementation).

## 1. Establish facts and ownership

Read the full ticket, prior comments, labels, linked changes and relevant source,
glossary and ADRs. Search for existing behavior and prior rejection records.
Separate source inspection, observed execution, synthetic tests and unverified
claims. A passing check establishes its tested scope, not completion of the whole
request. Report failures and skips alongside passes.

Identify who owns each decision. If the operator leaves a ticket with someone
else, record that owner and stop asking the current operator to settle that
ticket. Preserve its blockers and acceptance criteria. Do not infer a GitHub
account, contact the owner or dispatch work merely from an ownership note.

Done when the requested outcome, current behavior, owner, existing decisions and
remaining gaps are explicit.

## 2. Recommend category and state

Recommend one category (`bug` or `enhancement`) and one state, using the tracker's
adopted label mapping. Explain the consequences in plain language:

| State | Consequence |
| --- | --- |
| `needs-triage` | Evaluation or design remains; keep the request open. |
| `needs-info` | Progress needs a specific answer from the reporter. |
| `ready-for-agent` | A complete, testable brief lets an agent proceed without product guesses. |
| `ready-for-human` | The next work requires a person's judgment, access or manual action; explain why. |
| `wontfix` | Close because the request is rejected or already implemented; explain which. |

The triage skill requires direction after the recommendation. Carry forward
direction already supplied in the session; ask again only if new evidence changes
the proposed outcome. Explain all available choices when asking for a state.
Apply authorized tracker changes and read them back. Exactly one category and
one state should remain. If state roles conflict, flag the conflict and ask the
maintainer before doing anything else, as required by the original triage skill;
do not infer a resolution from generic tracker-edit authority.

Done when the maintainer has directed the outcome or continued evaluation. An
accepted `needs-triage` label is the beginning of evaluation, not an instruction
to stop resolving the request's design gaps.

## 3. Verify, then interview one decision at a time

Verify factual claims before asking the operator to decide: reproduce a bug where
authorized; inspect and run relevant checks on proposed code where permitted.
An unavailable or unauthorized check remains explicitly unverified. Investigate
technical facts yourself; ask the operator for product choices and authority.

When decisions remain, use `grill-with-docs` with its `grilling` and
`domain-modeling` primitives. Follow [the operator method](OPERATOR_METHOD.md)
for the exact one-decision question format, options/costs, recommendation and
deferred-decision line. That method overrides the original skill's whole-frontier
question batch and applies beyond ticket triage.

Wait for the answer, record it and recompute the remaining decisions before
asking the next question. A short answer such as `a` resolves only that question.
Keep settled choices settled unless contrary evidence or an operator correction
reopens them. Choosing a desired behavior grants no missing execution authority.

Done when every blocking decision for the named next phase is resolved or
explicitly excluded with the operator's agreement. Deferred blockers are still
blockers; do not describe them as resolved.

## 4. Document decisions as they land

Maintain the project's canonical glossary as domain terms are agreed. This
repository's explicit `CONTEXT.md` filename override and rules for other target
projects are defined in [the operator method](OPERATOR_METHOD.md).
Record significant, durable or security-relevant choices immediately in
`docs/adr/` using the [project ADR template](templates/ADR.md). Include the owner,
agreed choice, alternatives, consequences, evidence and unresolved details.
An unfinished interview does not invalidate an already settled decision; label
the accepted scope precisely and keep unresolved choices visible.

Inspect existing ADR numbers before creating one, including the current remote
tree if the local checkout is stale. Preserve other workers' edits. Use the
existing run record for session status and outstanding questions, rather than
creating a second task queue. Keep the ticket as the canonical work tracker.

Done when another agent can distinguish operator decisions from proposals and
resume at the next unanswered question using the actual documents.

## 5. Confirm understanding and produce the outcome

When no decision remains, summarize the agreed scope and write this exact line:

**Frontier empty — confirm shared understanding.**

Wait for the operator's shared-understanding confirmation before acting on the
finished design. This is distinct from implementation, publication, installation,
merge and deployment authority; retain any gates that still apply.

Prepare the triage skill's durable brief with current and desired behavior,
interfaces, observable acceptance criteria and explicit non-goals. A human brief
also explains what needs a person. For `needs-info`, preserve established facts
and ask specific reporter questions. For rejection, follow the original
out-of-scope rules; already-implemented behavior is not a rejected feature.

Publish only within current authority, prefix triage posts with
`> *This was generated by AI during triage.*`, apply the directed labels and read
back the result. If publication is unavailable, deliver an unpublished draft.

Done when the agreed outcome and its evidence are visible in the actual artifact,
with remaining authority and verification limits stated honestly.

## Example from issues 9 and 11

Both issues were classified `enhancement / needs-triage`. Issue 9's operator
selected an optional check of a trusted, explicitly selected Git executable;
default reporting stays passive. That decision belongs in an ADR while its
remaining diagnostic semantics are discussed. Issue 11 was left with Chad;
its design decisions are outside the current operator interview.

After Matt confirmed the complete brief, issue 9 moved to enhancement /
ready-for-agent and its [authoritative brief](https://github.com/mshamblin5150-code/assimilation/issues/9#issuecomment-6538185667)
was posted and read back. The bounded authoring task is specified; implementation
and native verification remain outstanding. Always read the current tracker
rather than treating this historical example as live status.

See [the workflow decision](adr/0009-documented-ticket-triage.md) and
[the Git-check decision](adr/0010-explicit-git-prerequisite-check.md).
