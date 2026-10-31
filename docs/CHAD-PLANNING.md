# From a foggy idea to agent-ready work

You do not need to know how to build something before asking for it. You do need
a way to separate **what you want**, **what remains undecided**, and **what an
agent can safely do next**.

This lesson is the planning companion to the [organizer exercise](CHAD-ORGANIZER.md).
You will turn a broad idea into a map, agreed requirements and small pieces of
work. You will also learn when to skip the map. The destination here is a useful
plan—not new organizer code or permission to move anyone's files.

**Read it in stages:** [choose the route](#1-pick-the-right-starting-point),
[make the map](#3-use-wayfinder-to-make-a-map-not-a-premature-build-list),
[record a decision](#4-resolve-one-decision-and-keep-the-answer),
[write the spec](#5-use-to-spec-to-write-down-the-agreement),
[slice the work](#6-use-to-tickets-to-make-small-complete-pieces), then
[check readiness](#7-read-ready-for-agent-correctly) and [practice](#8-practice-and-hand-off).
The live exercise spans sessions; you are not expected to finish it in one sitting.

If a term loses you, say **“Wait, what? Explain that with our organizer example.”**
Keep the approval and preservation rules when simplifying the explanation.

## 1. Pick the right starting point

Imagine two requests:

> **Small:** “Recognize `.rst` text files in the organizer preview. Keep unknown
> files untouched.”
>
> **Broad:** “I want an organizer for my computers, with my own categories,
> a clear preview, approved moves and a way to recover from interruptions.”

The first may need a small clarification, an agreed test and a bounded change.
The second hides choices about scope, platforms, rules, approval and recovery.
If those choices span multiple sessions, use:

**Wayfinder → agreed decisions → to-spec → to-tickets → authorized implementation**

That is a route, not a ceremony for every request:

| What you actually have | Where to start |
| --- | --- |
| A small, understood change or factual question | Its direct change, diagnosis or research route |
| Unclear choices that fit one design session | `grill-with-docs` and its underlying skills |
| A large idea whose route is still obscure across sessions | `wayfinder` |
| Agreed requirements for a substantial feature | `to-spec`, without repeating the whole interview |
| A trustworthy existing specification or ticket set | Check freshness and resume at its next incomplete stage |
| An incoming issue with uncertain claims or decisions | `triage`, then the design route it actually needs |

An issue is a request; a specification describes agreed behavior; an
implementation ticket is a small, verifiable piece of that behavior. A
**decision ticket** asks a question that must be answered before building.
Confusing these last two is how a list of guesses becomes a misleading backlog.

**Checkpoint:** explain why the `.rst` change does not automatically need a map.
The size of the uncertainty matters, not how impressive the project sounds.

## 2. Prepare the practice and read the real skills

Read [the connected workflow](WORKFLOW.md) and
[the operator method](OPERATOR_METHOD.md). Your agent must inspect the actual
project, current instructions, relevant decisions and its available tools.
Reading a repository does not install commands or grant access to your computer.

The relevant original sources are:

- [Wayfinder](../upstream/matt-pocock/skills/engineering/wayfinder/SKILL.md).
- [To spec](../upstream/matt-pocock/skills/engineering/to-spec/SKILL.md).
- [To tickets](../upstream/matt-pocock/skills/engineering/to-tickets/SKILL.md).
- [Grill with docs](../upstream/matt-pocock/skills/engineering/grill-with-docs/SKILL.md),
  which calls [grilling](../upstream/matt-pocock/skills/productivity/grilling/SKILL.md)
  and [domain modeling](../upstream/matt-pocock/skills/engineering/domain-modeling/SKILL.md).
- [Triage](../upstream/matt-pocock/skills/engineering/triage/SKILL.md), with its
  [agent brief](../upstream/matt-pocock/skills/engineering/triage/AGENT-BRIEF.md)
  and out-of-scope references when handling an incoming issue.

Follow each source's required references and invocation restrictions. These
entry points—Wayfinder, to-spec, to-tickets, grill-with-docs and triage—have
user-only invocation metadata in this repository. Their underlying primitives
have their own metadata; do not assume every skill has the same restriction.
Where a host has registered the command, the user can explicitly invoke it. Otherwise,
explicitly ask the agent to read and follow its permitted procedure; it must not
claim that a native slash command ran. This lesson is not installation authority.

For this exercise choose **paper or explicitly unpublished local Markdown**.
Select an empty practice location before authorizing any file creation. Use only
invented filenames, such as `garden.txt`, `picnic.md` and `mystery.bin`; no contents
need to be read and no files need to be moved. Do not use personal, synced,
network, clinical or production data. Preserve existing product, clinical,
security/data, native, persistence and teardown holds.

For real tracker work, first check the project's configured tracker, label
mapping, permissions and Wayfinding operations. If they are missing, use the
[setup skill](../upstream/matt-pocock/skills/engineering/setup-matt-pocock-skills/SKILL.md)
with its required human choices. Do not assume setup has happened because its
source is present. Paper/local drafts do not constitute tracker publication.

**Copyable practice request:**

> Help me plan the broad organizer idea above. Read this lesson, the project
> instructions, the operator method and the actual relevant skills. Work only
> on a paper rehearsal or unpublished drafts in my explicitly selected practice
> location. Explain the route and ask me one consequential decision at a time.
> Do not implement, publish, install, push a research branch or move files.
> Separate facts you verified, proposals, my answers and unresolved choices.

**Checkpoint:** agree the actual owner, destination, practice location and allowed
work. If the tools or location are unavailable, rehearse in conversation and
label it **not executed**, rather than pretending files or issues exist.

## 3. Use Wayfinder to make a map, not a premature build list

A **destination** says what this planning effort must establish. For our example,
a possible destination is “an agreed first-release specification for a safe
organizer.” The human must actually choose it; the example is not their answer.
Changing the destination changes the scope.

The **frontier** is the work you can take now. In Wayfinder it consists of open,
unblocked, unclaimed child decision tickets. A blocked question may still be
precise enough to create now; it simply cannot be taken yet.

### A map has five parts

The real map is one tracker issue labeled `wayfinder:map`, with child decision
tickets. In a local
rehearsal, use the configured local-tracker convention or clearly label the
artifact an unpublished mock map. Keep one source for each decision's detail.

```markdown
## Destination
A reviewed first-release specification for the organizer. (Proposed.)

## Notes
Planning only. Chad is the decision owner. Follow the operator method.
Record verified facts separately from proposed or accepted choices.

## Decisions so far
No decisions have been accepted yet.

## Not yet specified
Recovery experience: revisit once the first-release workflow is chosen.

## Out of scope
For this rehearsal: implementation, actual file moves and publication.
```

“Decisions so far” is an index of resolved decisions, not another copy of their
full answers. Open children are found through the tracker, not duplicated as a
second task list in the map. Refer to tickets by readable names with real links,
not a wall of numbers. The draft above has no real issue identifiers.

### Fog, question or exclusion?

| What you know | Where it belongs |
| --- | --- |
| “Which first-release workflow do we want: preview only or approved moves?” | A precise decision ticket, even though unanswered |
| “What recovery experience will the chosen workflow need?” is still too vague to scope | `Not yet specified`, until the question becomes sharp |
| A choice is already accepted | Its resolution record, indexed in `Decisions so far` |
| Work lies beyond this destination | `Out of scope`, not fog that silently becomes promised work |

A hard question is not necessarily fog: **can you state the question precisely?**
If yes, it can be a ticket. If a later answer exposes a precise new question,
create its ticket and remove that patch of fog. If a ticket proves out of scope,
record why, close it within authority and link it under Out of scope—not under
Decisions so far. Do not discard its history.

### Decision tickets have different jobs

| Wayfinder type | Plain-language job | Who supplies the answer? |
| --- | --- | --- |
| `wayfinder:research` | Find an external fact a decision needs, using the research skill | Agent, with evidence |
| `wayfinder:prototype` | Make a cheap concrete example to react to | Human feedback is required |
| `wayfinder:grilling` | Resolve a choice through conversation | Human decision owner |
| `wayfinder:task` | Do a prerequisite needed to make a decision, such as authorized access setup | Agent where permitted; otherwise the human |

A task ticket does not smuggle the product build into planning. Its action must
unblock a decision and still needs the appropriate permission. A prototype is
not production delivery. Research is not a license to send private data away.

**Wayfinder maps and children carry only `wayfinder:*` labels.** Do not give them
triage labels such as `ready-for-agent`. They are decisions, not implementation
work; their different label scheme is intentional.

Charting identifies the destination, known questions, dependencies and fog. Create
issues first, then wire relationships with their real identifiers. Use native
blocking where supported; otherwise the configured fallback. An assignee claims
a decision ticket before work so concurrent sessions do not duplicate it.

The actual skill separates charting from resolving: charting does not hand-resolve
its questions, and a working session resolves **one nonresearch ticket**. Research
is the parallel exception, where supported and authorized. The original research
flow uses a throwaway branch, pushed without a PR and never merged; our local-only
rehearsal does not authorize that push or claim to execute the full hosted flow.

**Checkpoint:** name one precise question, one fog area and one exclusion. Show
which question is takeable now and why. If there is no meaningful fog and the
whole journey fits one session, stop mapping and agree the simpler route.

## 4. Resolve one decision and keep the answer

The agent looks up facts it can discover. You decide consequential product
choices. For example, the existing organizer's preview and Windows-only moves
are source facts to inspect, not questions you should have to answer from memory.
A claim about another platform needs evidence, not a guessed compatibility promise.

Assimilation's [operator method](OPERATOR_METHOD.md) overrides upstream grilling's
whole-frontier question batches with **one decision at a time**. A worked question:

> A first release that moves files needs stronger recovery and platform evidence.
> We can learn about category rules without moving anything yet.
>
> A. Start with preview only. Cost: useful classification feedback, but no automated
> moving in the first release.
>
> B. Include approved moves. Cost: more approval, interruption and recovery design,
> plus verification on every supported platform before claiming support.
>
> ❓ Which first-release boundary should we design: A or B?
>
> ➡️ Recommend A for this learning project, because it keeps the first outcome
> observable while leaving original files in place.
>
> Held for later: rule conflicts, report behavior and the exact test boundary.

Now wait. The agent must not answer its own question. An answer of “A” settles
only that choice; it does not approve all future choices, publication or code.
If the real answer is B, follow that route rather than forcing this example.

Record significant choices as they land in the relevant ADR using the
[project template](templates/ADR.md). Include the owner, choice, alternatives,
consequences, evidence and unresolved details. Group related decisions; a trivial
clarification does not need its own file. Check existing ADR numbering and other
writers before creating a real one. A rehearsal ADR stays in the practice area.

A **hypothetical** record might say: “The learner chose preview-only for the first
release to avoid movement/recovery scope. Approved moves were considered but
excluded from this release. Profile conflict rules remain undecided.” It becomes
an actual decision only when the real owner answers and the record reflects that
answer. Choosing the behavior does not prove it works.

Agreed domain terms belong in the project's canonical glossary. Assimilation uses
`CONTEXT.md`, an explicit override of the source skill's `GLOSSARY.md` convention.
Use the established name in another project; avoid creating a competing glossary.
Implementation details belong in the ADR/specification, not glossary definitions.

Record a Wayfinder resolution on the ticket, close it within authority, and add
a named pointer to the map. Recompute the frontier: what became takeable, what
fog became precise, and what was invalidated? Preserve a closed-as-excluded
outcome separately from a decision actually resolved.

When the required design choices are settled, summarize them and say:

**Frontier empty — confirm shared understanding.**

Wait for the owner's confirmation. Deferred blockers are still blockers. “Zero
blocking decision fog” means the route to this named next phase is clear enough;
it does not mean zero risk, tested software or permission to build.

**Checkpoint:** another reader can tell what the owner decided, why, what remains
open and what remains unauthorized. Use a [context handoff](CHAD-CONTEXT-HANDOFF.md)
when continuing in a fresh session instead of recreating the interview.

## 5. Use to-spec to write down the agreement

A specification turns the settled decisions into an explanation of what should
exist. It is not a chance to quietly fill gaps with the agent's preferred product.

**Copyable request, after decisions are settled:**

> Read the actual to-spec skill and synthesize our accepted decisions, current
> project evidence, glossary and ADRs into an unpublished specification. Keep
> unresolved matters explicit. Propose the highest useful existing behavioral
> testing seam and check it with me before treating it as agreed. Do not restart
> the whole design interview, invent agreement or publish anything.

A **test seam** is where we can observe behavior without depending on the code's
internal arrangement. For a preview feature, it might be the public preview
interface or a command's observable output and unchanged inputs. The right seam
comes from the actual project. Prefer an existing high-level seam and agree it
with the owner; naming one in this tutorial is not that confirmation.

The original spec template covers:

- **Problem Statement:** the user's problem.
- **Solution:** how the user's experience improves.
- **User Stories:** who needs each behavior and why, including failures and edges.
- **Implementation Decisions:** settled interfaces, architecture and contracts.
- **Testing Decisions:** observable behavior, modules/seams and existing test examples.
- **Out of Scope:** boundaries that prevent accidental expansion.
- **Further Notes:** remaining context the reader needs.

Use the full original template for a real specification, not this summary as a
replacement. Avoid brittle file/line instructions or a code dump. The source
allows a small prototype-derived shape when it expresses a real decision more
precisely than prose.

For example, a hypothetical preview-only agreement could lead to a story:
“As a learner, I want unknown extensions to remain Keep, so the organizer does
not guess a destination.” A matching acceptance example uses invented
`mystery.bin`, observes no proposed destination, and verifies unchanged inputs.
The example says nothing about authorized moves or production support.

If synthesis uncovers a blocking choice, return to that choice. Do not call the
spec complete merely because every heading contains text. Once validly produced,
the source applies `ready-for-agent` without an extra triage pass; actual tracker
publication still needs authority. An unpublished draft has no live label.

**Checkpoint:** trace one requirement to its actual decision/evidence and one
observable acceptance check. The owner has confirmed the testing seam.

## 6. Use to-tickets to make small complete pieces

A **vertical slice** delivers one narrow behavior through every layer it needs.
For a command-line tool that might mean input, validation, preview output and
behavioral tests—not a database or a screen that the project does not have.
“Write all data code” followed by “write all UI code” leaves neither ticket useful
on its own.

**Copyable request:**

> Read the actual to-tickets skill and our full current specification and comments.
> Propose small end-to-end tickets with testable acceptance criteria and genuine
> blocking edges. Show me titles, what each delivers and why it depends on another.
> Ask whether the pieces are too coarse or fine, whether edges are correct, and
> whether anything should merge or split. Keep them unpublished until I approve
> both the breakdown and any separately required publication.

The following is a **hypothetical breakdown**, not approved organizer work. It
assumes the real design has already settled profile format, precedence, invalid
input behavior, report content and the test seam. If not, resolve those first.

| Proposed ticket | What it delivers | Blocked by |
| --- | --- | --- |
| Preview one folder with a selected rule profile | A chosen profile produces an exact read-only preview, including agreed invalid-input behavior | None, once the agreed spec and permissions are established |
| Compare assignments between two profiles | A learner sees which proposed categories would change without moving originals | Preview one folder with a selected rule profile |
| Export a human-readable preview report | A learner can inspect the agreed preview details in the specified report format | Preview one folder with a selected rule profile |

Here the latter two use the first ticket's preview contract. They do not depend
on each other. If the actual code already supplies that contract, reconsider the
edges rather than forcing this picture onto it. Dependencies express necessity,
not our preferred reading order. Perform any necessary prefactoring first.

### What one ticket needs

A useful ticket includes **What to build**, independently verifiable **Acceptance
criteria**, and **Blocked by** (native edges where supported, otherwise the
configured text fallback). Link its parent specification when there is one.

For the first hypothetical slice, acceptance might include:

- A valid selected profile produces exactly the agreed destinations for invented
  example files; unknown extensions remain Keep.
- A malformed or conflicting profile follows the agreed error contract instead
  of guessing categories. The spec must define that contract first.
- Original file paths and bytes remain unchanged; no move, action journal or
  category folder is created by preview.
- The agreed test seam covers both a valid profile and its rejected-input behavior.

These demonstrate the **shape** of criteria. They are not a complete new product
specification or permission to use real files. Durable tickets describe behavior
and contracts rather than edit instructions tied to file paths and line numbers.

Review the proposed granularity and edges with the owner before publication.
Actual `to-tickets` creates one local file per ticket or one tracker issue per
slice, blockers first. On a supported tracker, it uses native dependency links
and attaches tickets as sub-issues of an existing source issue. A parent/child
relationship is not itself a blocking relationship. **Do not close or modify the
parent issue as part of to-tickets.** Planning its children does not deliver it.

A wide mechanical refactor is the exception to ordinary vertical slicing: use
**expand → migrate batches → contract**, preserving compatibility and green
checks between batches where possible. If even batches cannot stand green alone,
the source allows a shared integration branch with a final integrate-and-verify
ticket. Do not use that exception to excuse arbitrary half-built features.

**Checkpoint:** explain what each slice demonstrates, how its acceptance is
checked, and why each blocker genuinely gates it. Do not assume every ticket
can start just because the breakdown has been approved.

## 7. Read ready-for-agent correctly

An implementation ticket can be well specified and still be waiting on another
ticket or authorization. Keep these questions separate:

| Question | What establishes it? |
| --- | --- |
| Is it specified? | An agreed, testable brief/spec without blocking product guesses |
| Is it dependency-unblocked? | Each required prerequisite outcome is actually satisfied |
| Is it authorized now? | Current scope, owner, tools/data permissions and preserved holds allow the action |
| Is it done? | Acceptance evidence for the actual implementation, including required checks/review |

`ready-for-agent` means sufficiently specified for an agent; it is **not** an
implementation order, a passed test, deployment approval or proof of completion.
Work the dependency frontier within current authority. Check why a blocker closed:
a duplicate, rejected or excluded ticket may not have delivered the required
outcome. If status and evidence disagree, reconcile them before dependent work.

For incoming requests, [the triage workflow](TRIAGE_WORKFLOW.md) includes current
source/claim checks, duplicate and prior-rejection checks, owner direction,
necessary design discussion and the durable brief. Its ordinary triaged issues
have exactly one category (`bug` or `enhancement`) and one state, using the adopted
mapping. Conflicting state roles need maintainer direction. Triage posts use the
source's AI-generated disclaimer; a clear outcome is read back after authorized
publication.

| Triage state | Plain-language meaning |
| --- | --- |
| `needs-triage` | Evaluation or design remains |
| `needs-info` | A specific answer is needed from the reporter |
| `ready-for-agent` | Complete, testable brief suitable for agent work |
| `ready-for-human` | The next work requires human judgment, access or manual action; explain why |
| `wontfix` | Rejected or already implemented; record which, rather than pretending it was built now |

Those category/state rules do not override Wayfinder's **wayfinder-only** decision
labels. Properly synthesized specs and tickets from the source skills do not
need a redundant triage interview. If new evidence invalidates their decisions,
return to the affected stage and reconcile downstream artifacts.

### Readiness challenge and answer key

For each case, ask: “Can the agent start implementation now?” Then check the
answer key. These are **hypothetical permissions**, not authorization for our
practice. “Implementation authority” means the owner has authorized the bounded
work in principle; missing decisions or prerequisites can still prevent starting.
The eligible example also assumes an available workspace, suitable tools and no
conflicting owner. Claim the ticket before acting.

| Case | Specified? | Prerequisites met? | Implementation authority? | Start implementation? |
| --- | --- | --- | --- | --- |
| Unanswered product choice | No | Unknown | Yes | No |
| Ready but dependency-blocked | Yes | No | Yes | No |
| Ready but permission-held | Yes | Yes | No | No |
| Ready and eligible | Yes | Yes | Yes | Yes |
| Blocker closed as duplicate; outcome unknown | Yes | Unknown | Yes | No |
| Human-only manual verification | Yes | Yes | Human only | No |
| Wayfinder decision question | Not a build ticket | N/A | No | No |

For the first case, resolve the actual owner's choice. For the second, wait for
and verify the prerequisite outcome. For the third, preserve the hold and seek
only the specific missing authority when needed. For a duplicate closure, find
the surviving work and its evidence; closed status alone is insufficient. For
human-only verification, give that person a precise checklist. For the Wayfinder
question, continue authorized planning—not product implementation.

Only the eligible implementation case reaches the implementation frontier. Even
there, starting is not finishing. Tests, review and actual acceptance evidence
are later obligations, and publishing or merging still has its own authority.

## 8. Practice and hand off

### Case A: know when to skip the map

Explain the route for the `.rst` preview request from the first section. Identify
its current behavior, narrow desired change, unchanged-file boundary and test
seam to agree. Do not implement it in this planning exercise. Continue with
[implementation and P-Stack](CHAD-IMPLEMENTATION.md) and
[Writing for Agents with TDD](CHAD-TDD.md) only when that later work is authorized.

### Case B: plan the broader organizer

1. **Charting session:** choose the actual destination. Draft the five-part map,
   two or more precisely stated questions, any genuine dependencies, and a fog
   area if one exists. Keep a precise but blocked question as a ticket, not fog.
2. **Decision session:** take one unblocked, unclaimed decision. Investigate facts,
   ask its real owner, record the actual answer and update the frontier. Preserve
   the one-nonresearch-ticket session boundary. Do not answer for the learner.
3. **Checkpoint session:** preserve the current stage and artifacts using the
   context-handoff lesson. Remaining questions stay visible. Repeat bounded
   decision sessions only as needed; finishing the first session is not finishing
   the whole map.
4. **Specification session:** after blocking choices are genuinely settled and
   understanding confirmed, synthesize the unpublished spec and agree the test
   seam. Record the evidence for moving to this phase.
5. **Ticket session:** propose independently verifiable slices and real edges.
   Let the owner review the breakdown. Assess readiness, dependencies and
   authorization separately; keep publication held in this rehearsal.

You may instead use a **tabletop illustration** with explicitly hypothetical
answers to understand the whole route quickly. Label those answers hypothetical
and the process **not executed**. A prepared answer key does not replace a live
human decision or prove the source skills ran.

### Give a fresh reader the artifacts, not the whole chat

Use this prompt with a genuinely fresh task when your host supports one:

> Read the accessible planning artifacts and current project instructions.
> Restate the destination, actual decision owner, current phase, accepted choices,
> evidence, unresolved questions and approval holds. Identify which tickets are
> specified, which are dependency-unblocked, and which actions are authorized.
> Reconcile stale or conflicting facts. Give one next allowed action and its stop
> condition. Do not publish, implement or turn hypothetical answers into approval.

The handoff needs locations/revisions the successor can actually read, plus
pending or uncertain operations and their owners if any. A fresh conversation
neither restores missing permissions nor makes an uncertain action safe to repeat.

**Pass:** the fresh reader reconstructs the actual stage, decisions, holds and
next safe action without guessing or restarting settled questions. **Not proved:**
software correctness, reliable behavior across all agents/hosts, successful
publication, or completion of the planned product. A paper exercise remains a
paper exercise even when the explanation is excellent.

You are ready for the next lesson when you can say, in plain language:
**“This is what we decided, this is what remains uncertain, and this is the one
piece of work we can actually take next.”**
