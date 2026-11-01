# Skill routing: make the complete upstream collections available

Before a design interview, read [the operator method](OPERATOR_METHOD.md): grilling with ADRs, one decision question at a time. Coordinators pass that method into authorized drone handoffs; [the Vox directive](VOX_HANDOFF.md) provides a concrete startup instruction.

First inspect the **actual** applicable source `SKILL.md` and its reference files. The manifest in `docs/SOURCES.md` is an index, not an alternate implementation. After `scripts/skills.py install --locked` for a committed baseline, upstream files are in `vendor/matt/` and `vendor/pstack/`; bridge entries are in `.agents/skills/`.

| Situation | Default route | End product |
| --- | --- | --- |
| Idea with meaningful unknowns, in a repo, resolvable in one session | Matt Pocock `grill-with-docs` and `domain-modeling` | Decisions, ADRs where durable, glossary |
| Multi-session idea with obscure route | Matt Pocock `wayfinder` | Decision map → `to-spec` → `to-tickets` → authorized implementation |
| No repo | Matt Pocock `grill-me` | Clarified requirements |
| Incoming ticket with unresolved design choices | `triage` → `grill-with-docs`, one decision at a time; [ticket-to-brief workflow](TRIAGE_WORKFLOW.md) | Recorded decisions and glossary, confirmed scope, testable brief and directed tracker state |
| Known substantial feature | `to-spec` → `to-tickets` → `implement` or `implement-spec` | Reviewed, tested change |
| Bug | `diagnosing-bugs` and applicable P-Stack investigation | Reproduction, fix, regression proof |
| Architecture | `codebase-design`, P-Stack `how` / `architect` / boundary discipline | Compared options, ADR, test seams |
| Code changes | Relevant `tdd`, `code-review`, and P-Stack verification | Tests, reviewed diff |
| Material conclusion | Claim-and-refutation | Claims, counterevidence, reconciled conclusion |
| CAD fabrication | `assimilation-cad` plus relevant design/test skills | Parametric source + STL where tools exist, validated prototype |

## Issues, specifications and tickets

Use [the issue guide](ISSUES.md) and [template](templates/ISSUE.md) for actionable
problem reports, duplicate searches and evidence. An issue describes an outcome;
a PR proposes a change. Ordinary bugs can use the direct diagnosis route.
Larger work follows the stages below, including their seam and ticket-review
requirements. Verify the intended project tracker before an authorized write;
without access, keep an explicitly unpublished draft. A closed duplicate does
not establish that a blocking outcome was delivered. To-tickets does not close
or modify its parent issue.

## Large, uncertain projects: from map to implementation

For a beginner-friendly practice, follow [From a foggy idea to agent-ready work](CHAD-PLANNING.md).
It distinguishes decision maps, specifications, implementation tickets and the
separate gates of readiness, dependencies and authorization using unpublished
organizer examples.

Recognize the need from the operator's ordinary-language goal, not from whether they know a command name. When the route is unclear and spans multiple sessions, select this connected sequence:

**`wayfinder` → `to-spec` → `to-tickets` → implementation**

| Stage and original source | Output and transition condition |
| --- | --- |
| [Wayfinder](../upstream/matt-pocock/skills/engineering/wayfinder/SKILL.md) | A named destination and decision/dependency map. Resolve in-scope blocking decision fog with evidence and the operator's actual decisions. Record why the map is ready for specification; do not substitute implementation tickets for unresolved design questions. |
| [To spec](../upstream/matt-pocock/skills/engineering/to-spec/SKILL.md) | Synthesize the resolved decisions into requirements, design, scope and observable acceptance/testing seams. Preserve required user confirmation of those seams; do not invent agreement or restart the whole interview. |
| [To tickets](../upstream/matt-pocock/skills/engineering/to-tickets/SKILL.md) | Derive bounded, independently verifiable work and explicit blocking edges from the specification. Obtain the original skill's required review of granularity and dependencies before publication. Follow its wide-refactor exception where vertical slices cannot remain green. |
| [Implement](../upstream/matt-pocock/skills/engineering/implement/SKILL.md) or [implement-spec](../upstream/matt-pocock/skills/engineering/implement-spec/SKILL.md) | Work authorized, unblocked tickets with ownership, tests and review. Deliver evidence against acceptance criteria, not merely a completed plan. |

Read each actual original and its required references at that stage. Respect original invocation restrictions: route selection does not automatically invoke a user-only host command. If the host cannot invoke it, explain the limitation and use only its permitted procedures, without claiming native execution. Keep human-in-the-loop decisions with the operator. Publishing maps, specifications or tickets, implementing changes, merging and deploying each require the applicable authority; completing one stage grants none of the next stage's missing permissions.

In the existing run record or handoff, keep the current stage, its canonical artifact, resolved decisions, remaining gates and the next authorized action. If later evidence invalidates a decision, return to the affected planning stage and reconcile downstream artifacts rather than building on a stale plan. Use the configured tracker when supported and authorized; otherwise provide a clearly unpublished local draft or text handoff rather than inventing tracker writes.

**Apply proportionately.** A small well-understood fix or factual question uses its direct skill, not this whole chain. A known substantial feature may start at `to-spec`; an existing trustworthy specification or ticket set may resume at its next incomplete stage after checking freshness, decisions and authority. Do not duplicate already verified planning artifacts.

For example, “I want a printable 3D scepter” may be a short design task when dimensions and printing constraints are known. If it expands into a multi-session fabrication project with unresolved joints, materials and safety decisions, map those decisions first, specify the agreed design, derive verifiable modeling/fit-test tickets, then build only with available tools and approval. The subject alone does not force Wayfinder.

**ADRs are highly valuable:** record significant decisions as they are resolved, with alternatives and consequences. Avoid the opposite mistake of adding endless process files that prevent engineering.

**All skills ≠ use all skills on every task.** Never run irrelevant P-Stack, multi-provider review, Cursor-specific tool, or external plugins on another host merely because their files exist. Report unsupported capabilities and host-specific adaptations. Respect original skill invocation constraints where the host does.

