# Doctrine: from impossible-looking goal to verifiable progress

## Purpose

Transfer operational knowledge so a new operator can use AI as a **force multiplier** while retaining authorship and judgment. The evolution was: line-by-line micromanagement → unrestricted agents and collisions → **bounded autonomy** with clear task ownership, engineering skills, and proportional verification. Preserve the *lesson*, not retired administrative machinery.

## Operating loop

1. **Name the outcome.** Use the operator's language; ask only the decisions that really matter. Define success, constraints, scope, and observable tests.
2. **Find the route.** For an unclear project idea use `grill-with-docs` by default. For large work whose route is not yet visible across multiple sessions, use `wayfinder` to map decision tickets and the in-scope fog. Research can be delegated. Record settled hard-to-reverse decisions in ADRs.
3. **Declare zero blocking fog only with evidence.** Revisit the map's *not yet specified* frontier. Every decision necessary for the specified next phase is either resolved, supported by a stated assumption accepted within authority, or explicitly out of scope. Unknowns that still block it are reported, not hidden. Agents may make this assessment on their own; human-only choices remain human-only.
4. **Make work executable.** Use `to-spec`, then `to-tickets` when multiple independent slices are needed. Document task owner, dependencies, the verification surface, and stop conditions.
5. **Execute boundedly.** Use available skills (e.g., implement, TDD, diagnosis, P-Stack architecture/review) with one clear owner per file or slice. Parallelize independent work when available. Do not confuse more agents with better output.
6. **Challenge and verify.** Claim agent finds evidence for a conclusion; refutation agent looks for disconfirming evidence. Then review, test, compare against the spec, and record observed results without inflating claims.
7. **Deliver and learn.** Chief of Staff reconciles summaries; operator receives concise conclusion, changes made, checks performed, residual risks, and decisions required. Retrospectives improve future workflows, preferably by removing pointless complexity.

## Zero blocking fog is not omniscience

A valid `ZERO_BLOCKING_FOG` decision contains: named scope/destination; links to decided tickets or ADRs; explicit assumptions; summary of last frontier scan; list of known remaining risks; reviewer/agent name and timestamp. It means *the path to the specified next phase is clear enough to execute*. It never means safety, correctness, deployment authorization, or every conceivable uncertainty is resolved.

## Engineering rules

- Build small observable increments. Verify the behavior rather than implementation details.
- Prefer simple ownership boundaries, deep interfaces, and the Zen of Python where relevant.
- When a bug or review finding exposes a reproducible missing check, add a proportionate regression test rather than a permanent ceremonial rule.
- Every created process mechanism needs a reason to exist and a way to retire it. Avoid redundant sign-offs, mandatory role names, or rigid worker-count gates.
- Respect command authority: agent opinions are recommendations; consequential permissions are separate.
- No task is too large to **analyze and decompose**. Some tasks are impossible under current tools/resources. State those limits and show a workable path forward.

## High stakes

For clinical, financial, legal, life-safety, and load-bearing physical design, AI work is assistance. Qualified human professionals and physical tests may be required; do not convert an AI confidence score into professional verification.
