# ADR 0002: frozen source updates with reviewed PRs

- Status: Proposal format accepted; publication hold superseded by [ADR 0004](0004-monthly-draft-pr-publication.md)
- Date: 2026-10-28
- Owner: Assimilation operator

## Context

The starter checked upstream `main` and opened an issue. It could report changes without an installed lock, and a later install fetched a moving branch rather than the commits reviewed. The operator selected monthly reviewed update PRs and retained MIT. Existing workflow permissions cannot create branches or PRs.

## Decision

Freeze both source baselines and target SHAs in `sources.update.json`. Reject missing, malformed, partial, or stale baselines. Install a reviewed plan only with `--approve-update --update-plan`; fetch its exact commits. A clean checkout can reproduce its existing lock with `--locked`.

At this repair stage, the workflow prepared a plan and draft PR body, uploaded the artifact, and recorded an issue handoff using existing permissions. Automatic PR publication remained held pending a separately reviewed permission change. Initial public publication also required its before-publish review. These historical holds are superseded by the follow-on decision below; automatic approval and merge remain forbidden.

## Alternatives considered

- Fetch latest `main` after review: rejected because the installed source could differ from the reviewed source.
- Treat historical documentation pins as the installed baseline: rejected because they do not prove installation.
- Add write permissions or a personal access token silently: rejected because desired behavior does not authorize new credentials or privilege expansion.
- Automatically merge passing update PRs: rejected because synthetic tests do not establish trust in upstream instructions.

## Consequences

Review is tied to immutable source commits. A changed baseline requires a new proposal. Monthly PR creation remains incomplete until permission activation is separately authorized and verified. Generated source trees remain local and ignored by Git.

## Verification

`tests/test_update_proposal.py` exercises the proposal CLI with isolated synthetic Git repositories and file-only Git transport. It covers absent and invalid baselines, frozen SHAs, unchanged locks, current sources, output preservation, and unavailable upstreams. The installer suite covers exact-plan adoption separately. Live GitHub workflow execution and PR publication are not claimed.

## Follow-on decision

On 2026-10-28 the operator explicitly approved workflow authority to write update branches and open draft PRs. ADR 0004 records that implementation and its remaining repository-setting verification. This decision never authorizes automatic approval or merge.
