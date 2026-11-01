# Review monthly complete-source PRs

Monthly automation proposes complete source snapshots, their matching pin lock, provenance, and a frozen update plan in one draft PR. **One reviewed merge adopts them together.** No separate post-merge update step is needed. The bot never approves or merges, executes upstream code, or installs host skills.

## What the workflow publishes

The workflow runs on the first day of each month at 09:00 UTC, or by manual dispatch. Both the job and publisher accept only scheduled or manual runs on the default branch. Offline verification first checks the complete committed source snapshot. Missing lock means setup needed, without an upstream request, branch, or PR. Invalid locks or missing/edited snapshots fail closed. Current source pins produce no PR.

The generator compares the lock with official upstream `main`, freezes exact `from_sha` and `to_sha` pairs, then fetches source data at those target commits. It prepares only these publishable paths:

- `upstream/matt-pocock/`: the entire tracked Matt repository;
- `upstream/pstack/`: the entire tracked P-Stack subtree;
- `sources.lock.json`: minimal proposed source pins, without invented installation times or bridge counts;
- `sources.snapshot.json`: complete per-file hashes/modes and immutable Git-object provenance;
- `sources.update.json`: the frozen baseline-to-target plan.

The generated `PULL_REQUEST.md` is review text, not a staged repository file. The workflow archives the complete package as a tar file so hidden metadata, executable modes, and links survive artifact storage. Do not execute or unpack an arbitrary downloaded artifact into an active project.

The generator emits a SHA-256 digest binding every allowed path, mode, size, and byte (including literal link targets), plus the lock, manifest, and plan. The publisher validates that digest and the offline provenance before any API mutation. This is a binding between steps of **one trusted job**, not a signature or an authenticity scheme for arbitrary downloaded artifacts.

## Scoped publication and retry safety

The publisher requires an unchanged committed baseline lock, manifest, and both source trees. Dirty target paths, untracked source files, mode drift, stale plans, or changed remote default commits stop publication. Unrelated local files and arbitrary artifact files cannot enter the commit.

A deterministic `automation/skill-update-<package-hash>` branch holds one complete proposed commit. The publisher reuses known Git blobs and batches changed UTF-8 content in source-tree requests; changed binary data uses base64 blob requests. Each complete replacement source tree must reproduce its provenance tree SHA. Replacement removes obsolete source files, including deleted directories. Only the two source entries change under `upstream/`; its README and unrelated siblings remain intact. At the repository root, only `upstream/` and the three named JSON files may change. Root workflows cannot be injected by an upstream `.github/` path.

Existing branches are never updated or force-pushed. Reuse requires exact root and upstream tree entries, source tree SHAs, message, sole parent, and baseline provenance. The parent must remain an ancestor of current default with the same baseline. This proves content, not who independently created identical bytes.

The bounded exact head/base PR search reuses only one open, unmodified draft owned by `github-actions[bot]`, with the expected head, base, title, and complete body. Closed, promoted, human-owned, duplicate, or edited PRs need human review. The bot never reopens a rejection or edits human notes.

A failed or lost branch/PR response can leave a retained branch or draft. After inspecting the failure, rerun: the publisher reconciles existing state rather than duplicating or resetting it. Default-ref and proposal-ref checks run again before reporting success. GitHub cannot atomically lease the default branch across PR creation; a detected race leaves any draft intact and reports failure. No check prevents a later human change.

## Review and adopt

1. Inspect the PR's exact source-diff links, complete source changes, licenses/credits, executable files, dormant configuration, and compatibility with the tools you actually use. Confirm only the five allowed path scopes above changed.
2. In a fresh isolated checkout of the proposal branch, run:

   ```sh
   python3 scripts/snapshot_sources.py verify
   python3 -m unittest discover -s tests -v
   ```

   Each lock and provenance commit must equal the plan's `to_sha`. The original baseline remains on the default branch until review and merge.
3. Review source instructions as reference material, not commands to run. Nested `.github`, `.agents`, plugin, hook, and host configuration stays dormant. Copying sources is not approval to activate them.
4. Record checks and independent review for the exact PR commit, and obtain operator acceptance. Approve any requested CI workflow execution only after reviewing it. An open draft is not proof that checks ran.
5. Merge through the authorized human process. The snapshot and matching lock/provenance are adopted in that merge; **do not run a separate post-merge snapshot refresh**.

Host installation is separate. In a fresh local checkout, `python3 scripts/skills.py install --locked` can materialize the merged pins and engineering/P-Stack bridges. For an already managed installation, follow its explicit approval and ownership checks; do not use `--locked` as an overwrite bypass. Never commit generated `vendor/` or `.agents/` content.

## Permissions and live verification

The approved guarded job requests only `contents: write` and `pull-requests: write`; global contents access stays read-only. It uses the runner's `GITHUB_TOKEN`, not an issues grant, new secret, or personal access token.

The repository setting **Allow GitHub Actions to create and approve pull requests** must permit creation, subject to organization policy. GitHub bundles approval in that setting's name; this workflow never calls approval or merge. Enabling that setting is a separately authorized administrative action. Code and offline tests do not establish its current value.

On a failed API call, the publisher reports the HTTP status when available, the
tree-entry count for tree creation, and a fixed `service hint` derived from a
small recognized set of JSON error messages. It never prints raw service bodies
or stderr. A hint is not an independent policy diagnosis. Invalid JSON (including
nonstandard constants), duplicate keys, bodies over 8,192 characters or 16 container levels
(counting the top-level object), and absent or unrecognized bodies produce
`unclassified`. In particular, HTTP 403
alone does not distinguish an access refusal from a rate limit. Preserve the
failed run and inspect its saved artifact, deterministic branch, and matching
PR before considering a rerun. Do not change permissions, substitute credentials,
or repeat a denied write just to diagnose it. This diagnostic does not retry
requests or change the draft-only publication boundary.

Bot-created PR workflow runs may need a writer to approve execution. Verify the actual hosted run and checks. See [token permissions](https://docs.github.com/en/actions/tutorials/authenticate-with-github_token), [repository Actions settings](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/managing-github-actions-settings-for-a-repository), and [workflow trigger behavior](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow).

## Prepare without publishing

`python3 scripts/propose_update.py --output-dir review-update` prepares a complete package in a new directory without changing the checkout. Exit codes: `0` current, `2` prepared proposal, `3` absent lock, `1` error. The publisher is an Actions-only entry point, not a general artifact uploader. Its `--expected-package-sha256` must come from the same trusted generation step; rehashing a downloaded artifact does not establish trust.
