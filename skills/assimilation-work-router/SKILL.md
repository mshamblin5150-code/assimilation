---
name: assimilation-work-router
description: Choose relevant engineering and P-Stack skills for the current task; prioritize documented decisions and verifiable work.
---

Before routing, read `AGENTS.md`, `docs/WORKFLOW.md`, and the actual source `SKILL.md` for each selected upstream skill. In a repository with ambiguous substantial design, default to `grill-with-docs`; for an effort requiring several sessions and with an unclear route, suggest/invoke `wayfinder` only as supported by the host and permitted by the operator. Make ADRs for durable decisions. For resolved plans route to `to-spec`, `to-tickets`, and `implement`/`implement-spec` with actual TDD/review steps as relevant. For ordinary bugs and factual queries use appropriate dedicated workflows. Never claim a tool ran merely because it was mentioned. Do not invent source names, skip required references, or impose irrelevant ceremonies.

Before asking design questions, read `docs/OPERATOR_METHOD.md` and carry its one-question grilling and live ADR updates into authorized handoffs with the named decision owner. For Vox or Chad coordinator startup, read `docs/VOX_HANDOFF.md`.

For incoming ticket triage with unresolved design choices, follow `docs/TRIAGE_WORKFLOW.md`: preserve settled direction and decision ownership, interview one decision at a time with `grill-with-docs`, record significant decisions in ADRs, and produce a testable brief after confirming shared understanding. This route does not invoke restricted skills or grant implementation/publication authority by itself.
