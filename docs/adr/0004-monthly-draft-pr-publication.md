# ADR 0004: create-only monthly draft PRs

- Status: Accepted implementation; live activation requires separate verification
- Date: 2026-10-28
- Owner: Assimilation operator
- Proposal scope superseded by: ADR 0005 (complete snapshots, lock, provenance, and plan in one PR)
- Supersedes: The automated-publication permission hold in ADR 0002

## Context

The initial repaired workflow produced a frozen plan but had no authority to create branches or PRs. The operator explicitly approved `contents: write`, `pull-requests: write`, and Actions PR creation. Approval and merge remain human decisions. A live repository setting may need a separate administrator action.

## Decision

Run only on default-branch schedule or manual events. Pass the exact generator-byte digest through the same trusted job. Reject modified artifacts, invalid baselines, and stale checkout state before mutation. Prove the committed lock mode and blob hash, not just the bytes returned by GitHub Contents, which can dereference a link. Create a one-file proposal commit from the remote base tree and a deterministic plan-hash branch through create-only Git APIs. Never update an existing ref.

Reuse only an exact one-file proposal tree and an unchanged open bot-owned draft PR. Compare every root tree entry and subtree SHA, not a truncated file summary. Reject closed, promoted, human-owned, or modified PRs. Partial failures retain their branch or draft for inspection and safe rerun. Post-publication checks report a detected default-branch race without deleting the draft.

Use the runner token with only contents and pull-request write permissions in the guarded job. Remove the obsolete issue grant. Pin third-party actions to verified immutable commits. Never add a personal access token, install sources, execute upstream code, approve, or merge in automation.

## Alternatives considered

- Force-push one reusable branch: rejected because it could erase human review work.
- Change the lock before source review: rejected because a proposal is not adopted source.
- Trust any artifact with valid-looking SHAs: rejected. The same-job digest binds publication to the generator's original bytes.
- Re-fetch moving upstream heads during publication: rejected because it changes the review target.
- Treat branch creation as proof of PR creation or CI success: rejected. Each result needs its own observed evidence.

## Consequences and limits

A human-edited branch stops automatic reuse. The bot leaves rejected or closed proposals closed. Branch names expose public source commit pairs, not credentials. Content checks establish the proposal tree, not the identity of a person who might independently create identical bytes.

API calls cannot make the default branch and PR creation one atomic operation. A race may leave a draft requiring inspection. Repository settings and approval-required CI runs must be verified on GitHub after publication. Offline fixtures prove supported behavior, not live token policy.

## Verification

`tests/test_publish_update.py` drives the real publisher CLI through a separate `gh` process backed by synthetic local Git objects and persisted PR state. It covers normal publication, one-file commits, digest transfer, repeats, lost responses, partial failure, human edits, stale baselines, default-branch races, and event restrictions. All tests use file-only Git transport and no live GitHub requests.
