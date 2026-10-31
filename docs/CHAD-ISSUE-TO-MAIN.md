# Chad's next lesson: take one issue from request to main

You have learned to write instructions, build tickets and test behavior. Now
connect those skills: **understand the request, prepare one worktree, implement
the agreed brief, review the change, then integrate it within your authority.**

One vocabulary correction: **you merge a pull request's changes, not a ticket.**
The issue records the requested outcome. The branch holds commits. The worktree
is where you edit and run them. The PR proposes integrating those commits. Close
the issue only when its acceptance criteria are actually satisfied.

```text
incoming issue → triage → decisions + brief → authorized implementation
                                               ↓
                               one branch + one owned worktree
                                               ↓
                         tests → independent review → PR → main
```

Use the [local rehearsal worksheet](../examples/chad-issue-to-main/README.md)
alongside this lesson. Its small enhancement is: **recognize `.rst` notes as Text
while unknown files remain Keep.** It uses disposable synthetic files, not real
personal files. Its local integration is not a public GitHub PR or hosted CI run.

## 1. Triage means evaluate, not immediately build

Read the actual [triage skill](../upstream/matt-pocock/skills/engineering/triage/SKILL.md)
and its agent-brief/out-of-scope references. On a host that has registered it,
explicitly invoke `/triage` for the exact issue. Otherwise ask the agent to read
and follow that source; don't claim a slash command ran. Reading Assimilation
does not install commands.

For live work, first read the configured tracker and category/state mapping.
If missing, follow the skill's request for
[`setup-matt-pocock-skills`](../upstream/matt-pocock/skills/engineering/setup-matt-pocock-skills/SKILL.md)
with the owner's decisions and permissions. Do not guess a repository or create
labels as a side effect of reading this lesson. The worksheet instead supplies a
local-only tracker convention; it changes no live tracker configuration.

The agent reads the whole issue, previous answers, linked PRs and source. It
searches for existing behavior and earlier rejection decisions, then recommends
one category and one state with reasons. It waits for the maintainer's direction.
For the practice, `.rst` currently being Keep is expected baseline behavior, so
the request is an **enhancement**, not automatically a bug.

| State | What it tells you |
| --- | --- |
| `needs-triage` | Evaluate or resolve design questions |
| `needs-info` | A specific missing reporter answer blocks progress |
| `ready-for-agent` | The brief is complete enough for an agent |
| `ready-for-human` | The next work needs the human judgment/action described in the brief |
| `wontfix` | Rejected or already implemented; distinguish the reason |

Use the actual label mapping, exactly one category and one state. Conflicting
states require maintainer resolution. A direction to continue `needs-triage`
means keep evaluating, not stop after applying a label. A `to-tickets` result
that is already agent-ready need not repeat the whole interview.

Verify claims before grilling: inspect and safely reproduce the relevant
behavior, or report what remains unverified. For our exercise, obtain a preview
showing an invented `.rst` file as Keep. If it already works at your chosen base,
do not manufacture a failing test; report the redundant request.

**Done:** the current behavior, owner, prior decisions, proposed category/state
and remaining gaps are explicit. This follows the canonical
[ticket-to-brief workflow](TRIAGE_WORKFLOW.md), not a second triage policy.

## 2. Grill with docs; record decisions as they land

Explicitly request
[`grill-with-docs`](../upstream/matt-pocock/skills/engineering/grill-with-docs/SKILL.md)
when the request still needs decisions. Its actual procedure calls **grilling**
and **domain-modeling**. Read those sources and required formats too.
Assimilation's [operator method](OPERATOR_METHOD.md) requires **one decision per
reply**, even though upstream grilling describes batching a frontier of questions.

Here is an **illustrative** exchange, not a recorded approval for your files:

> We need to decide whether recognizing a note means reading its meaning or just
> recognizing its filename suffix.
>
> A. Keep extension-only classification. Cost: the extension may misdescribe the
> contents; the existing uncertainty warning remains.
>
> B. Parse the document. Cost: a larger data-access, dependency and test surface,
> outside this small exercise.
>
> ❓ Should this enhancement use A or B?
>
> ➡️ Recommend A, because it keeps the agreed organizer boundary intact.
>
> Held for later: case handling and acceptance checks.

Wait for the actual owner's answer. Investigate technical facts yourself; don't
ask the user questions the source can answer. For example, inspect the existing
case-insensitive suffix behavior before recommending how `.RST` should work.

Record significant, durable or security-relevant decisions in the relevant ADR
**when they are made**, not after implementation. Preserve the canonical
`CONTEXT.md` convention; don't create a rival glossary. In this tiny exercise,
[ADR 0008](adr/0008-practice-organizer.md) already explains extension-only
classification and exact-preview approval. Reference that decision. A reversible
suffix addition needs a precise brief, not a ceremonial new ADR. If the owner
changes a durable boundary, update the decision record appropriately, with
alternatives, consequences and its accepted scope, before building on it.

Summarize settled behavior and remaining holds. When the decision frontier is
empty, use the operator method's exact confirmation line:

**Frontier empty — confirm shared understanding.**

**Done:** the owner confirms shared understanding; decisions/ADRs and unresolved
holds are findable. This confirmation is not missing implementation or merge
permission.

## 3. Turn agreement into an agent-ready contract

The triage skill's
[agent-brief format](../upstream/matt-pocock/skills/engineering/triage/AGENT-BRIEF.md)
is the durable implementation contract. It states current/desired behavior,
interfaces, independently checkable acceptance and non-goals—not a fragile list
of line numbers or a prescribed internal implementation.

Compare your result with the
[filled practice brief](../examples/chad-issue-to-main/AGENT-BRIEF.md). The brief
describes the behavior; a separate bounded assignment can name the exact allowed
workspace and files. Use [Writing for Agents](CHAD-TDD.md) to make the next action,
stop condition and completion criteria clear. Keep one canonical issue/brief
rather than copying slightly different versions into every agent's chat.

For authorized live triage posts, preserve the original skill's required prefix:

```text
> *This was generated by AI during triage.*
```

Without publication authority, save an explicitly unpublished local draft. A
label or posted brief does not establish that blockers were resolved, that an
agent owns the work, or that code changes are authorized.

**Implementation gate:** current confirmed brief; satisfied dependencies; agreed
public test seam; one named owner/worktree; permission for the bounded code/test
work; separate holds still recorded. For this lab, agree `preview(folder)` before
writing its new test: it observes classification and unchanged files, **not**
Windows moves, host obedience or production safety.

## 4. Give the work its own worktree

A Git worktree is a separate checkout with its own working files, staging area
and current checkout (`HEAD`). Linked worktrees share repository objects,
branch/tag references, default repository configuration and the stash. They are
not separate security sandboxes or copies of every external resource.
[Git's worktree reference](https://git-scm.com/docs/git-worktree) describes these boundaries.

Use one branch and one accountable writer per worktree. Verify its full path,
branch, immutable starting commit and status before editing. Point the agent,
terminal, test runner and editor at that exact path; creating a worktree does not
move an already-running terminal or agent into it. A worktree cannot prevent two
processes from sharing a database, port, credentials or an external output path.

Follow the [worksheet's checked setup and cleanup sequence](../examples/chad-issue-to-main/README.md).
Preserve someone else's dirty files and stop on branch/path collisions instead
of forcing checkout or stashing their work. The source repository and Vox's
separate work remain outside this exercise.

**Done:** the agent reports its actual worktree/branch/base and allowed changes,
with no competing owner. Keep that identity in the existing private run record.

## 5. Now actually invoke implement

Once the implementation gate is met, explicitly use
[`implement`](../upstream/matt-pocock/skills/engineering/implement/SKILL.md), not
another planning pass. Example, after replacing the placeholders:

```text
/implement the confirmed brief in [canonical issue or local brief].
Work only in [exact worktree] on [branch]. Use the agreed preview(folder) seam
with synthetic files and the recorded scope/holds. Read the actual TDD and
relevant P-Stack sources. Deliver code, test evidence, independent review and
a local commit; do not publish, merge, or move practice files.
```

If a ticket reference is provided, the original implement skill first fetches it
and states its title; ambiguous references require clarification. The path-based
fallback is an explicit request to follow the actual source, not pretend tool use.

Implement uses [TDD](../upstream/matt-pocock/skills/engineering/tdd/SKILL.md) where
possible at agreed seams: one behavior test → observed meaningful red → smallest
green change, then repeat if another slice is needed. Refactoring belongs to
review, with checks rerun afterward. A test-discovery error or zero tests is not
the desired red. Use the [earlier TDD lesson](CHAD-TDD.md) for the method.

Read and explicitly apply relevant P-Stack principles at their actual decision
points; do not invoke every workflow merely because it exists:

| Source | Job in this exercise |
| --- | --- |
| [Test behavior, not implementation](../upstream/pstack/skills/principle-test-behavior-not-implementation/SKILL.md) | Assert literal preview results and preserved files, not private dictionary/helper structure |
| [Foundational thinking](../upstream/pstack/skills/principle-foundational-thinking/SKILL.md) | Keep one owner per checkout and inspect shared state before adding parallel work |
| [Prove it works](../upstream/pstack/skills/principle-prove-it-works/SKILL.md) | Read actual outputs/diffs and run the feature before declaring success |

These sources retain their invocation restrictions. Using their principles does
not mean a native P-Stack arena, multi-vendor review or host hook ran. For a wider
change, choose the relevant additional workflow and follow its full source.

The extension affects the shared preview used by later apply operations: it can
change a plan ID and destination. The training scope is preview-only, **not** a
claim that downstream behavior is unaffected. Preserve exact fresh-plan approval.
Check any instruction that lists supported extensions so it agrees with code.

Run focused checks as you work and the applicable full suite before completion.
Inspect configured typechecking/lint commands; if absent, say so rather than add
an unrelated dependency. Respect platform limits: Linux root tests and the
Windows organizer suite are different checks. Unavailable checks remain visible
and cannot satisfy a real merge gate.

**Done:** a real diff satisfies the brief; red/green evidence is retained; current
test results and unavailable checks are explicit. A plan describing a fix is not
implemented work.

## 6. Review the exact change, not the author's confidence

Use the actual [code-review skill](../upstream/matt-pocock/skills/engineering/code-review/SKILL.md)
with the recorded starting commit and canonical brief. Make a local review
checkpoint commit so its `git diff BASE...HEAD` is nonempty; review must also
account for any remaining working edits. A checkpoint is not permission to push.

The skill runs **Standards** and **Spec** as independent parallel reviewers and
reports them separately. Standards checks repository rules; Spec checks the
agreed behavior and scope. If parallel independent agents are unavailable,
disclose a sequential adaptation rather than claim two drones reviewed it.
Fix concrete findings, rerun affected/full applicable checks, commit repairs and
review the changed revision. Read the actual candidate diff and file list before
staging; avoid sweeping unrelated work into a commit.

**Done:** the exact candidate commit is identified, review findings are resolved
or explicitly held, and evidence matches that revision. Agent review is not a
formal GitHub approval and never substitutes for a required legitimate approver.

## 7. PR, checks, merge, then acceptance

For the local lab, draft a PR description outside the worktree and use the
worksheet's local rehearsal branch. **Stop before public publication.** Preparing
this lesson, finishing code or creating a local commit grants no live push/PR/merge
permission.

For separately authorized real work:

1. Verify the intended repository, feature head and target branch. Push only the
   authorized feature branch and open the PR through available supported tooling.
   Summarize behavior, evidence, limits and linked issue. Follow the actual
   [PR-writing skill](../upstream/matt-pocock/skills/engineering/pr/SKILL.md).
2. Read back the actual PR, diff and head. Wait for current required checks and
   reviews; examine unresolved threads and failures. A stale green run from an
   older head does not qualify the new one. Draft-to-ready can trigger new runs.
3. If head/base changes or conflicts appear, reconcile ownership/integration,
   review the new diff and rerun necessary checks. Preserve repository policies
   and approval holds; do not invent an approval or force past a refusal.
4. Merge normally only with current authority and eligible state, checking the
   expected head where supported. If the result is uncertain, inspect the PR and
   target branch before retrying. Ending a turn is not proof of a failed merge.
5. Read back the merged PR and actual target-branch content/commit. Confirm the
   issue's acceptance, not merely a green badge. Deployment, activation or native
   qualification can still be outstanding.

Use a closing keyword such as `Closes #ACTUAL_ISSUE` only when this PR genuinely
satisfies that whole issue. GitHub interprets closing keywords for PRs targeting
the default branch; a linked issue can close automatically on merge. A partial
slice should use a non-closing reference and retain its remaining work.
[GitHub's linking documentation](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/linking-a-pull-request-to-an-issue)
explains the mechanism; automatic closure is not independent acceptance evidence.

**Done:** the approved change is verified on the intended branch and the issue
accurately reflects what is delivered versus still blocked.

## 8. Retire the workspace without losing work

Cleanup is a separate permitted action, not an automatic reward for a merged PR.
Use the [worksheet's cleanup gate](../examples/chad-issue-to-main/README.md#cleanup-gate).
First reconcile process/agent ownership, preserve evidence outside the removable
directory, inspect tracked/untracked/**ignored** files, and verify the intended
integration. Keep ambiguous or unmerged work. A squash merge can preserve changes
without preserving the original branch tip's ancestry; do not force-delete to
make a command pass.

If work must pause at any stage, use the
[context/handoff lesson](CHAD-CONTEXT-HANDOFF.md) and the canonical
[fleet rule](FLEET_HANDOFF.md). Carry the issue, decisions, worktree, exact commit,
tests, owner, pending operations and holds. A fresh agent should continue the
next authorized step—not start triage or implementation over from scratch.

**Your final explanation:** “This issue asked for this behavior. These decisions
made it ready. This worktree held the implementation. These tests and reviews
checked it. This PR integrated it—or this exact gate still prevents integration.”
