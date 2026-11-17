# ADR 0014: local approval of one exact installation plan

- Status: Proposed record of the selected design requirement; implementation acceptance remains open
- Date: 2026-11-17
- Owner: Chad owns issue 11 design decisions; the linked discussion attributes the selection to the operator

## Context

Issue 11 and draft PR 12 explore a Windows generated-file view. Their prototypes
do not authorize writes or establish native confinement. The issue discussion
records a local-only approval choice, but the PR did not retain that choice in
an ADR or specify its observable consent behavior.

This record preserves the published choice. A GitHub display name or this ADR
does not authenticate a person or authorize an operation.

## Decision

The [issue 11 decision](https://github.com/mshamblin5150-code/assimilation/issues/11#issuecomment-6607225033)
selects an interactive, first-party local session for human approval of one
immutable installation plan and one attempt. The plan presents verified source
and payload identities, the destination, planned effects, conflicts, activation
effects, and recovery limits.

Changes to source, payload, destination identities, or effects invalidate approval.
Cancellation, refusal, missing approval, and replay cannot authorize a write.
Another attempt needs fresh local approval. Agents cannot approve on the
operator's behalf.

The [design contract](../WINDOWS_GENERATED_VIEW_DESIGN.md#local-approval-contract)
defines the required behavior. It does not implement a consent interface.

## Alternatives considered

Remote, chat, GitHub-comment, coordinator, and delegated approval are rejected by
the recorded decision. They do not bind a human at the Windows machine to the
displayed plan. Implicit approval from OS login, process launch, unattended flags,
environment values, or token possession is also insufficient.

Local approval adds an interactive step for every attempt. No unattended
installation mode is part of this design.

## Consequences

Repository publication and merge do not authorize installation or activation.
Existing Windows refusal remains unchanged. No elevation, permission repair,
network approval service, or telemetry is introduced.

The approving account/session binding, spoofed-UI and automation assumptions,
exact serialized plan schema, native handle custody, authenticated recovery, and
writer exclusion remain unresolved. These are design work, not claims of
implementation or security acceptance.

## Verification and references

The current prototype has no consent implementation or consent acceptance tests.
Future tests must exercise refusal, cancellation, missing approval, replay,
changed plans, changed identities, and unattended or remote approval. Native
adversarial qualification remains separately scoped and authorized.

- [Issue 11 recorded decision](https://github.com/mshamblin5150-code/assimilation/issues/11#issuecomment-6607225033)
- [PR 12 bounded design brief](https://github.com/mshamblin5150-code/assimilation/pull/12#issuecomment-6614615153)
- [ADR 0007: native source refusal](0007-fail-closed-native-source-operations.md)
- [Native handle verification plan](../WINDOWS_NATIVE_HANDLE_VERIFICATION_PLAN.md)

