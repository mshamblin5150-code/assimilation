# ADR 0003: transactional installation with explicit ownership

- Status: Accepted for the repaired installer
- Date: 2026-10-28
- Owner: Assimilation coordinator within the operator-approved repair

## Context

The original installer replaced whole directories and deleted live targets during rollback, even when their backup move had failed. System temporary directories could be on another filesystem. Vendor contents had no ownership check, and edited generated wrappers could be overwritten.

## Decision

Stage each replacement beside its destination: `vendor/` and the lock under a root `.assimilation-stage-*` directory, and bridges under `.agents/.assimilation-stage-*`. Backups remain on the same filesystem as their targets. An exclusive `.assimilation-install.lock` directory serializes cooperating installers.

Record backup and install intent before each filesystem move. After an exception, reconcile the observed candidate, target, and backup paths. Rollback moves installed candidates aside and restores backed-up originals. An original whose backup move did not complete stays untouched. Failed restoration retains the backup and reports its location. Retained staging blocks another install until an operator inspects and recovers it.

Schema 2 ownership markers fingerprint complete owned trees, including names, entry types, modes, and file bytes. Updates reject unknown vendor entries, changed owned content, legacy markers without fingerprints, symlinks, and special files. Unowned, nonconflicting bridge entries are preserved, including their nested metadata. Destination fingerprints are checked again before replacement.

Ignore installer guards and stages in Git. They can contain recovered private skill copies or fetched Git configuration with mirror URLs. Use the [recovery procedure](../RECOVERY.md) before removing retained state.

## Alternatives considered

- Delete every live target on any failure: rejected because an original might never have moved.
- Stage in the system temporary directory: rejected because rename may cross filesystems.
- Replace unknown or edited content after `--approve-update`: rejected because approval to adopt sources is not permission to erase unrelated work.
- Automatically upgrade legacy ownership markers: rejected because there is no trusted fingerprint to distinguish original content from edits.
- Delete retained stages on the next run: rejected because a backup might be the only remaining original.

## Consequences

Installation may stop for manual reconciliation where the previous implementation silently replaced files. Fingerprinting has a cost proportional to the trees being protected. Existing legacy installations require explicit recovery rather than a force flag.

This is rollback for caught failures, not a crash-safe database transaction. Multiple directory moves are not globally atomic. The guard does not stop unrelated editors, and there is no power-loss durability guarantee. An abrupt process termination can leave a guard, stages, and a partially moved installation for manual recovery.

## Verification

The offline installer suite injects failures at backup, installation, lock replacement, and restoration boundaries. It checks preserved originals and recoverable backups, plus ownership and exact-SHA installation. Proposal tests check that Git ignores retained root and bridge staging. No installer test uses a live project or executes upstream code.
