# ADR 0010: explicitly selected Git prerequisite check

- Status: Accepted design and agent brief; implementation and native verification pending
- Date: 2026-10-30
- Owner: Matt Shamblin

## Context

[Issue 9](https://github.com/mshamblin5150-code/assimilation/issues/9) retains an
unfinished Git availability/version diagnostic requirement. Current onboarding
deliberately reports Git as unverified without discovery or execution. Automatic
search can reach network or redirected filesystem locations. Existing project
requirements name Git but establish no numeric minimum supported Git version.

## Decision

Matt selected option A: an explicit, optional check of a trusted Git executable
chosen by the operator, using a separately reviewed bounded version observation.
Default reporting stays passive and performs no automatic Git discovery.

Matt also selected option A for an untested Git version: report the observed
version and mark compatibility unverified. There is no invented minimum-version
threshold or rejection solely because a version is absent from a tested list.
An observed version does not establish that any Git source operation will work.

Matt selected option B for a failed explicit Git check: return an error status
while retaining the diagnostic report. This covers failure to start, timeout
and unusable output. Passive default reporting retains its existing behavior.

Matt agreed to option A for executable trust: rely on the operator-selected,
trusted Git installation. This diagnostic does not add publisher-signature or
approved-hash verification. The executable, its dependencies, their containing
paths and the runtime are trusted prerequisites, not properties established by
the check. It is not protection against malicious or concurrently replaced Git.

This settles intended behavior only. A path supplied by an operator is not by
itself evidence of executable identity, confinement or trustworthy behavior.
Native probe execution, installer support and merge retain their separate gates.

## Alternatives considered

- Operator-supplied version report only: avoids new execution but cannot independently
  establish current executable availability and would narrow the diagnostic requirement.
- Automatic discovery: reduces manual selection but expands filesystem/network
  exposure and conflicts with the current no-discovery boundary.
- Accept only explicitly tested versions: would require a maintained support
  list and reject potentially working versions; not selected for this observation.
- Overall success with a failed-check field: forces automated callers to inspect
  report fields to notice the failed request; rejected in favor of an error status.
- Mandatory signature/hash admission: adds a platform-specific trust policy and
  ongoing maintenance; not selected for this diagnostic scope.

## Consequences

The operator must select a trusted executable for an optional observation. The
design must establish admission/refusal cases, bounded execution and output
handling before implementation. A successful version response cannot silently
become proof that source operations or installation are safe.

Matt confirmed shared understanding of the complete
[issue 9 agent brief](../ISSUE_9_AGENT_BRIEF.md), including the invocation,
error-code and test details and the five-second/4-KiB resource defaults. The
bounded authoring task is ready for an agent. The separate native-probe,
independent-review, publication and merge gates remain as stated in the brief.

## Verification and references

Source inspection confirmed passive Git reporting in the current onboarding
command and guide; ADR 0007 on the current remote tree preserves native source
refusal. No new Git version probe or native acceptance test has run in this
interview. Existing reports and CI evidence do not establish this future check.
See [the triage workflow](../TRIAGE_WORKFLOW.md) for continuation.

The confirmed self-contained brief was published to
[issue 9](https://github.com/mshamblin5150-code/assimilation/issues/9#issuecomment-6538185667)
and its complete text read back. The ticket was moved to enhancement /
ready-for-agent while retaining open state and its verification/acceptance holds.
That earlier issue-comment publication did not publish the local ADR or method
files; those become available remotely through their own documentation merge.
