# Harness engineering: make agent work inspectable

A harness is the surrounding system of instructions, tools, permissions, state,
checks and feedback that lets an agent work on a bounded task. A longer prompt
alone does not supply those capabilities. Start with the smallest loop that
produces observable progress; add machinery when an actual failure justifies it.

This is Assimilation guidance, not an installer, hook or automatic permission
grant. For a worked exercise, use [Chad's lesson](CHAD-HARNESS-ENGINEERING.md).

## Read the synthesis and its sources critically

The [Celeste Anders gist](https://gist.github.com/celesteanders/21edad2367c8ede2ff092bd87e56a26f)
is a useful reading map, not official vendor policy. Its four references offer
different experiments and practices:

| Source | Useful contribution | Limit when applying it here |
| --- | --- | --- |
| Anthropic, [Effective harnesses for long-running agents](https://www.anthropic.com/research/effective-harnesses-for-long-running-agents), November 2025 | Incremental features, durable progress records and checking running behavior across sessions | Reported experiments do not certify another model, host or project |
| Geoffrey Huntley, [Ralph Wiggum as a software engineer](https://ghuntley.com/ralph/), July 2025 | A focused iteration loop and fast checks that reject wrong output | An endless loop is not permission to retry a denied or uncertain operation |
| Anthropic, [Harness design for long-running application development](https://www.anthropic.com/research/harness-design-long-running-apps), March 2026 | Explicit evaluation criteria and separation of generation from evaluation | Extra agents and context resets have costs; use them for a demonstrated need |
| OpenAI, [Harness engineering](https://openai.com/index/harness-engineering/), February 2026 | Repository navigation, legible application state and mechanically enforced constraints | Its experimental autonomy and merge practices do not replace this repository's human gates |

These are source-attributed ideas, not reproduced benchmarks. No speedup or
general reliability claim follows from this guide.

## Fit the harness to existing skills

Read each original source before use. A repository copy does not register a
slash command or activate an explicit-only skill.

| Need | Existing source | Concrete output |
| --- | --- | --- |
| Decide intended behavior | [Operator method](OPERATOR_METHOD.md), applicable [workflow](WORKFLOW.md) | Settled scope, owner and unresolved decisions |
| Write useful context | [Writing for Agents](../upstream/matt-pocock/skills/productivity/writing-for-agents/SKILL.md) | Short navigation pointers; definitions and caveats kept together |
| Implement an agreed behavior | [TDD](../upstream/matt-pocock/skills/engineering/tdd/SKILL.md) | Public seam, independently expected result, observed RED then GREEN |
| Challenge a change | [Code Review](../upstream/matt-pocock/skills/engineering/code-review/SKILL.md) | Separate Standards and Spec findings when its workflow is actually run |
| Check the result | [Prove It Works](../upstream/pstack/skills/principle-prove-it-works/SKILL.md) | Direct artifact/value evidence |
| Keep tests meaningful | [Test Behavior](../upstream/pstack/skills/principle-test-behavior-not-implementation/SKILL.md) | Observable outcomes, not assertions about internal wiring |
| Put checks at external inputs | [Boundary Discipline](../upstream/pstack/skills/principle-boundary-discipline/SKILL.md) | Validated inputs and explicit refusal/error outcomes |

A separate reviewer should seek counterexamples for material claims. If an
independent reviewer is unavailable, disclose a sequential self-review; do not
call it independent or claim a parallel Standards/Spec workflow occurred.

## Three slice checkpoints

These are this guide's proposed reusable checkpoints, not claims about a past run.

| Checkpoint | Questions | Completion evidence |
| --- | --- | --- |
| Before the slice | What outcome, owner, source revision, public seam and permissions apply? Does the behavior already exist? | Bounded contract and checks, current state, preserved holds |
| During the slice | What did the latest observation establish? Is the next step still within scope? | Focused result; RED/GREEN only when actually observed; failures and uncertain operations retained |
| Before completion or handoff | Does the exact artifact meet the contract? What is running or blocked? | Readback/test/review evidence, remaining limits, next owner and action; no implied merge or deployment consent |

A checkpoint is a judgment point, not an automatic permission prompt. Continue
already authorized work; ask only when a real decision or approval is missing.

## Keep the record small and truthful

Use the canonical ticket and existing run record rather than introducing another
competing task queue. Record exact source identity, scope, owner, authorized
commands, outcomes, failed checks, skips, limitations and next action. Link
approved evidence; keep private operational details outside the public repository.

Persist the distinction between not started, admitted, running, completed,
denied and unknown. A lost response is not proof that nothing happened.
[The fleet handoff rule](FLEET_HANDOFF.md) preserves ownership during interruption.

Baseline checks should be relevant and authorized. Select the narrow public seam
first, then broaden only when a change or failure justifies it. A pure injected
test does not qualify native behavior; a UI test is useful only where UI behavior
is part of the contract. Documentation changes need source/link/claim checks,
not invented behavioral RED results.

## Adapt the gist's hazardous defaults

- Preserve human edits and recovery evidence. Do not copy automatic destructive
  reset or deletion recipes into a shared workspace.
- Review setup scripts and upstream material as data before any separately
  authorized execution. Reading instructions does not authorize installation.
- Keep capability restrictions in the host. A prose rule, audit hook or shell
  parser is not an OS sandbox; POSIX shell parsing does not secure PowerShell.
- Stop denied routes and reconcile uncertain outcomes before repetition.
  More iterations cannot manufacture authority or resolve an unknown effect.
- Keep credentials, private paths, transcripts and unexpected payloads out of
  public progress records. Publish only the approved public-safe scope.

Retire checks and scaffolding when direct evidence shows they no longer help.
Maintain the [safety](SAFETY.md), [doctrine](DOCTRINE.md) and operator boundaries:
no automatic publication, merge, installer activation or permission changes.
