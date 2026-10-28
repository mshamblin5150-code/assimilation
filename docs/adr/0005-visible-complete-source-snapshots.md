# ADR 0005: visible complete sources and atomic reviewed snapshot adoption

- Status: Accepted implementation; publication and live execution require verification
- Date: 2026-10-28
- Owner: Assimilation operator
- Supersedes: ADR 0004's one-file proposal and separate human lock-adoption step

## Context

The public repository contained doctrine and an installer but no browsable upstream skills. The operator requested the actual Matt Pocock and P-Stack sources. A plan-only monthly PR would leave visible sources stale unless a person performed another undocumented step.

## Decision

Keep the entire tracked Matt repository under `upstream/matt-pocock/`, and the complete `pstack/` subtree under `upstream/pstack/`. Preserve bytes, modes, binaries, file links, licenses, metadata, and dormant material. These are inert reference data, not host activation or authority to execute nested instructions/configuration. Keep optional local `vendor/` and `.agents/` installation separate and ignored.

A deterministic manifest binds each path/mode/blob hash/SHA-256/size to the exact scope tree, root tree, and commit, retaining raw public commit/root-tree proofs. Offline verification requires the exact complete file set and matching lock. Reject unsafe paths, unsupported objects, escaping links, changed license inventory, and recognized secret signatures; these checks do not certify arbitrary code or find every secret.

Snapshot refresh owns only the two source directories and manifest, preserves sibling files, shares the install guard, stages on each target filesystem, and retains backups when restoration fails. Preparing a proposal writes only a fresh output directory and a minimal pin lock, never fictitious installed times or bridge counts.

Monthly proposals include complete target snapshots, pin lock, provenance, and frozen plan together. Bind every publishable path/mode/byte to the generator's package digest in the same trusted job. The publisher requires clean committed target paths and verifies current remote baseline. It uses exact replacement source Git trees, which remove obsolete files; binary payloads use base64. Compare source tree SHAs plus all root and upstream entries to prove both completeness and preservation of unrelated files. Nested upstream workflows cannot become root workflows.

Retain default-branch event guards, minimal existing contents/PR write permissions, deterministic create-only refs, exact branch/PR reuse checks including human title/body edits, retained partial effects, and default-ref race detection. No new credentials/settings, automatic approval/merge, upstream code execution, or force-push. One reviewed merge adopts visible sources and matching pins/provenance atomically; local host installation remains explicit.

## Alternatives

- Links, ignored downloads, summaries, or archives only: rejected; the requested files must be browsable in GitHub.
- Publish only installed engineering bridges: rejected; that omits productivity, miscellaneous, in-progress, and dormant sources.
- Update snapshots after merge: rejected; review and adoption would no longer be one atomic commit.
- Stage the local worktree or replace all of `upstream/`: rejected; could publish unrelated files or discard user-owned siblings.
- Upload every blob on every run: rejected; reuse baseline Git objects, batch text changes, upload only new binary blobs.

## Consequences and verification

The repository is larger and contains dormant executable/host-specific material. Review remains necessary; copying files grants no compatibility or safety guarantee. Original source bytes remain untouched; supplemental upstream attribution belongs in root notices. Git SHA proofs establish content association to the pinned objects, not an independent signature by the upstream author.

Public CLI tests use synthetic Git repos and a separate fake GitHub API process. They cover full binary/link/mode preservation, source deletion, scope isolation, digest drift, committed-baseline checks, retries, human changes, and default-ref races. Source retrieval and live repository results need separate observed verification. Same-filesystem rollback is not a power-loss durability or hostile concurrent-writer guarantee.
