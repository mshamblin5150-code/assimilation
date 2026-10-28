# ADR 0006: Cold-start procedure with observable capability boundaries

Status: accepted for the requested onboarding implementation; publication and merge retain separate authority.

## Context

The operator requested something an unfamiliar agent can follow, not merely a collection of linked doctrines. A repository cannot provide tools, credentials, models or delegation that the consuming host lacks. Existing source snapshots must remain intact, and claims of successful onboarding need actual work evidence.

## Decision

Expose START_HERE from README and AGENTS as the single procedural entry. Use a proportionate target-project run record for context, authority, source-reading receipts, decisions, observed checks and handoff. Existing project equivalents take precedence. Significant decisions still use project ADRs; trivial fixes do not require artificial ceremony.

Provide an optional standard-library, read-only CLI index that verifies the existing snapshot manifest before returning original skill paths, pins and blob identities. It reports only locally observed interpreter/path facts and explicitly unknown host capabilities. The agent must classify its task, read original files and apply permitted relevant procedures itself. Manual file reading remains a supported path.

Validate via CLI boundary tests and a controlled practical synthetic task with fresh baseline/candidate agents. An independent grader checks actual output and protected files. Report agent-recorded traces separately from direct observations, and state untested capability limits.

## Alternatives

- A runtime that provisions tools, installs agents or grants broad authority: rejected as outside scope and misleading across hosts.
- Instructions alone with a self-reported doctrine quiz: insufficient evidence of actual behavior.
- Mandatory installation, swarms, ADRs and full process for every task: rejected as unnecessary friction and false capability assumptions.

## Consequences and verification

The cold-start path is usable with a readable repository and task-appropriate host tools, but cannot guarantee universal agent competence. Unknown capabilities remain unknown. Source verification fails closed; no source instructions run merely because files are copied. No new external permissions, automatic approval or merge behavior is introduced. See evals/cold-start for reproducible protocol and dated evidence; baseline and candidate both succeeded, so no causal performance improvement is claimed.

## Actual source methods

Matt Pocock writing-for-agents (including SKILL-MECHANICS), ask-matt, TDD and code-review; applicable P-Stack prove-it-works, boundary discipline, behavior testing and reader-load/context principles. Original source revisions are recorded in sources.lock.json and exposed by the helper. These were read as reference procedures, not represented as host-native skill invocations.
