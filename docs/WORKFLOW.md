# Skill routing: make the complete upstream collections available

First inspect the **actual** applicable source `SKILL.md` and its reference files. The manifest in `docs/SOURCES.md` is an index, not an alternate implementation. After `scripts/skills.py install`, upstream files are in `vendor/matt/` and `vendor/pstack/`; bridge entries are in `.agents/skills/`.

| Situation | Default route | End product |
| --- | --- | --- |
| Idea with meaningful unknowns, in a repo, resolvable in one session | Matt Pocock `grill-with-docs` and `domain-modeling` | Decisions, ADRs where durable, glossary |
| Multi-session idea with obscure route | Matt Pocock `wayfinder` | Decision map → zero blocking fog → `to-spec` |
| No repo | Matt Pocock `grill-me` | Clarified requirements |
| Known substantial feature | `to-spec` → `to-tickets` → `implement` or `implement-spec` | Reviewed, tested change |
| Bug | `diagnosing-bugs` and applicable P-Stack investigation | Reproduction, fix, regression proof |
| Architecture | `codebase-design`, P-Stack `how` / `architect` / boundary discipline | Compared options, ADR, test seams |
| Code changes | Relevant `tdd`, `code-review`, and P-Stack verification | Tests, reviewed diff |
| Material conclusion | Claim-and-refutation | Claims, counterevidence, reconciled conclusion |
| CAD fabrication | `assimilation-cad` plus relevant design/test skills | Parametric source + STL where tools exist, validated prototype |

**Wayfinder maps; it does not build by default.** Its map is complete when the route to the named destination has no unresolved *blocking decision fog*. The agent may declare that state when supported by the tracker, without waiting for a human to utter the phrase. If the operator still must decide dimensions, acceptable risk or functional requirements, report that as fog rather than forge answers. Once clear, hand off to specification and implementation tasks.

**ADRs are highly valuable:** record significant decisions as they are resolved, with alternatives and consequences. Avoid the opposite mistake of adding endless process files that prevent engineering.

**All skills ≠ use all skills on every task.** Never run irrelevant P-Stack, multi-provider review, Cursor-specific tool, or external plugins on another host merely because their files exist. Report unsupported capabilities and host-specific adaptations. Respect original skill invocation constraints where the host does.
