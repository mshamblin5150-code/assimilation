# ADR 0009: document the ticket-to-brief decision workflow

- Status: Workflow and issue 9 design accepted; issue 11 remains with Chad
- Date: 2026-10-30
- Owner: Matt Shamblin

## Context

Triaging issues 9 and 11 initially stopped at category/state labels. The remaining
design choices needed an interview, and the operator explicitly requested
`grill-with-docs`, an ADR and a reusable repository mechanism for this process.
The operator subsequently left issue 11 with Chad and retained issue 9 in this
interview.

## Decision

Connect triage to a documented, one-question-at-a-time design interview. Carry
forward settled direction, verify factual claims, explain options and costs,
record durable decisions in ADRs and agreed domain terms in the glossary, then
produce a testable brief after shared-understanding confirmation. Route agents
to [TRIAGE_WORKFLOW.md](../TRIAGE_WORKFLOW.md) from the project instructions and
workflow index. Respect the original skills' invocation and authority boundaries.

Matt subsequently explicitly required this interaction method to be discoverable
by Chad's coordinators and drones for design interviews generally. Each substantive
interview has an ADR record updated as decisions land; related decisions can share
an ADR. [OPERATOR_METHOD.md](../OPERATOR_METHOD.md) is the canonical interaction
method, linked from README, START_HERE, AGENTS and the router. The
[Vox handoff](../VOX_HANDOFF.md) supplies a reading order and copyable chat.
This makes the method available to readers of the updated checkout; it does not
claim that remote drones have received or followed it. This repository adopts
`CONTEXT.md` as its canonical glossary, explicitly overriding the bundled skill's
`GLOSSARY.md` naming; other projects retain their established conventions.

Issue 11's decisions are left with Chad, without inferring an account assignment
or sending him a message. Issue 9 continues with Matt.

## Alternatives considered

- Labels alone: preserve classification but leave the implementation contract unresolved.
- Chat-only interview: loses the rationale and makes resumption depend on chat history.
- Ask all questions together: conflicts with the operator's binding one-question format.
- Treat triage as implementation approval: exceeds the decisions actually made.

## Consequences

The process becomes discoverable in the repository and resumable from its
documents. Documentation must distinguish accepted choices from unanswered
questions. Small, understood requests retain direct triage without a forced
interview or ADR for every trivial choice.

## Verification and references

Read installed triage and its brief/out-of-scope references, grill-with-docs,
grilling, domain-modeling and its formats, and writing-for-agents. Read the
project authority and workflow documents. This is a documentation change;
runtime behavior and native Git checking have not been implemented or tested.
The operator's one-question override takes precedence over the upstream batch
format. Existing source snapshots remain unchanged.
