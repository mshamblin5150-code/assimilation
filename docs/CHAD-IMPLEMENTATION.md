# What implementation does, and where P-Stack fits

For your own new repository, start with [the blank-project walkthrough](CHAD-BLANK-PROJECT.md). After implementation, use [adversarial prose review](CHAD-ADVERSARIAL-REVIEW.md) to check the agent's completion claims against actual evidence.

Read this after [Writing for Agents with TDD](CHAD-TDD.md). Keep the first organizer lesson short: inspect an exact preview before approving changes. This reference explains the development process behind the example.

The installed Matt Pocock implement skill was read for this lesson. It takes a user spec or tickets, uses TDD at agreed interfaces, runs focused checks regularly and the full suite at the end, requests code review, and commits the work. It is not a planning substitute or permission to merge. Here the delegated requirements supply the spec; no issue tracker or ticket publication is needed.

## Follow one behavior through the process

| Stage | Inputs and actions | Output and done criterion |
| --- | --- | --- |
| Requirements and acceptance | User wants preview, approved moves, preservation and undo. For the new regression, a file named Text must block category creation before journal reservation. | One observable expectation with a synthetic folder and expected preservation |
| Writing for Agents | Express preview, explicit approval, stop and recovery in ordered skill steps; link optional details and state what ends each step. | An agent can identify the next allowed action and when to wait |
| TDD red | Add one test at the agreed preview/apply interface, run before implementation. | Observed failure for the missing behavior, preserved in TDD-RED.txt |
| Implement | Read the failing path, identify that category-parent validation happens too late, add the smallest preflight check before journal creation. | Code changes the required behavior without adding unrelated functionality |
| Validate green | Run the new test and relevant regression suite; inspect actual temporary files and journal absence. | All 18 tests pass; existing preservation cases still work |
| Review and refactor | Simplify repeated destination resolution after green, rerun the suite, have an independent reviewer challenge it. | Same behavior, 18 passing tests, reviewed evidence and explicit limits |
| Deliver | Record changed files, evidence and remaining gates; commit only in the isolated candidate. | A reviewable patch and local commit, with active integration/publication still unperformed |

Implementation makes decisions inside the agreed requirement. In this slice, it chooses where the guard belongs and how to report the condition. It does not decide to organize more folders, change the user's approval, install readers or rebuild clinical references.

Planning decides which behavior should exist. Implementation changes the code and instructions to produce it. Validation tries to show it does not. A response describing a plan is not implemented code; passing unit tests is not evidence that a host invoked the skill correctly.

The actual history matters. The initial organizer and 17 tests already existed before this teaching extension. Only the new category-parent collision has the recorded test-first cycle. The new test calls preview/apply with real temporary files rather than mocking their internals. Source logs and independent review separate observed behavior from explanations written afterward.

## Use P-Stack deliberately

The installed pstack router and its catalog were read. It lists source workflows; it does not enable a global mode. Its direct expanded-source resource lookup failed with “failed to read skill resource.” This lesson therefore uses the complete actual sources already preserved in this isolated Assimilation snapshot, at the P-Stack revision recorded in sources.lock.json, c742dd61706fbacc1b95f1a20b7b988cf096ce6c. This is not a claim that the installed router's separate e43c7ee snapshot was extracted or its native workflows executed.

| Source to read when needed | When and why | Organizer artifact or evidence |
| --- | --- | --- |
| [principle-foundational-thinking](../upstream/pstack/skills/principle-foundational-thinking/SKILL.md) | Before changing data ownership or adding concurrent actors; choose data structures and isolate shared writes | Existing preview rows/ID, journal records and separate workspace; ADR 0008 explains the chosen boundary |
| [principle-test-behavior-not-implementation](../upstream/pstack/skills/principle-test-behavior-not-implementation/SKILL.md) | When writing the new regression; catch broken user behavior while surviving internal cleanup | New preflight test observes error, journal absence and preserved file bytes; remained green after refactor |
| [principle-prove-it-works](../upstream/pstack/skills/principle-prove-it-works/SKILL.md) | Before completion claims; inspect the real result | Actual red/green/refactor output, synthetic CLI round trip and independent rerun |
| [blast-radius](../upstream/pstack/skills/blast-radius/SKILL.md) | Advanced impact review before integrating a change; identify the fact safety depends on and prove it with code | Integration should rerun the full organizer suite on the reconciled base; currently no overwrite is supported by initial/late collision tests on Windows, not by prose alone |
| [architect](../upstream/pstack/skills/architect/SKILL.md) | Optional deeper progression if the small exercise becomes a cross-platform/concurrent organizer; compare structurally different designs before locking in an interface | A future interface sketch, competing designs and rationale; not needed or executed for this small preflight fix |
| [interrogate](../upstream/pstack/skills/interrogate/SKILL.md) | Advanced adversarial review when the actual host supports its reviewers/workspaces | Verified counterexample commands and findings, not a confidence score; our separate reviewer reproduced a journal defect and later verified the repair |

The first three principles directly inform this bounded example. The final three are advanced workflow entry points, not a claim that their complete procedures ran. Read the actual source and every reference/dependent workflow before invoking one. architect calls for grounding, multiple design candidates and synthesis through arena; interrogate calls for separate adversaries and rerun repros. blast-radius calls for broader dependency/history inspection and an executable safety fact. Do not relabel a single ordinary code review as any of those complete workflows.

The independent reviewer here is a real separate agent, using the same available model family; it is not a multi-vendor panel or a native P-Stack arena. It found and reproduced the torn-journal defect. Its concrete test, subsequent fix and rerun are stronger evidence for that defect than an unsupported assurance. Host-specific model defaults in upstream sources do not grant permission or availability to route models here.

## A manageable progression for Chad

Start by explaining preview output. Then make one synthetic behavior test fail, implement the narrow change and inspect the pass. Learn how the skill's approval wording and code's hash checks support different parts of the result. Use an instruction scenario to check whether the agent waits; do not claim a hash-check test proves it waits.

Later, use the public Clinical Skills trace to see a small dependency interface, synthetic status tests, instruction contract tests and durable ADR reasoning in a larger project. If Chad proposes a broader organizer, then discuss design alternatives and impact with the advanced P-Stack sources. Keep all work bounded to authorized practice inputs.

Done when Chad can identify requirements, agent instructions, the failing expectation, implementation decision, passing result, review challenge and remaining uncertainty without treating them as interchangeable.

## Practice the whole route

[Take one issue from triage to main](CHAD-ISSUE-TO-MAIN.md): clarify it with the actual skills, agree a brief, implement in an owned worktree, review the exact change and distinguish local rehearsal from an authorized real PR merge.
