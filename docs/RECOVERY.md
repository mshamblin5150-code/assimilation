# Recover a stopped installation without losing files

If installation reports retained backups, unknown content, edited owned files, or a legacy ownership marker, stop. `--approve-update` does not override those protections. Do not delete a guard or stage merely to make the next install run.

## Preserve the evidence first

1. Confirm that no installer is still running in the checkout. A `.assimilation-install.lock` directory may belong to a live process or an abruptly stopped one.
2. Record the error and the paths it reports. Inspect, without executing files:
   - `.assimilation-stage-*/backup-vendor` and `backup-lock` under the project root.
   - `.agents/.assimilation-stage-*/backup-skills`.
   - Current `vendor/`, `.agents/skills/`, and `sources.lock.json`.
3. Copy all surviving originals, backups, local edits, and markers to separate private storage before changing their locations. Preserve file modes and directory names. Confirm the copies are readable and complete.
4. Keep recovery material out of Git and public artifacts. A stage may contain fetched `.git/config` files with mirror URLs, local private skills, or other user content. The ignore rules are a precaution, not proof that an arbitrary file is safe to publish.

## Reconcile the installation

Identify which paths contain the pre-install originals and which contain new candidates. The stage names `vendor`, `skills`, and `sources.lock.json` hold candidates during preparation. The `backup-*` names hold moved originals. After rollback, a candidate name may hold a removed replacement.

Compare surviving files with the saved ownership markers, lock, and your preserved copies. Restore a coherent original vendor tree, bridge tree, and lock only after that comparison. Never restore over an occupied target without preserving and identifying its contents first. If the origin of a file remains uncertain, keep every copy and ask for a focused review.

For a legacy marker or an intentional local edit, preserve the original tree and reconcile changes explicitly. Do not manufacture fingerprints to make modified content look installer-owned. A fresh isolated checkout can reproduce a valid trusted lock with `install --locked`; it does not replace the need to preserve local work.

After recovery is verified and no installer is active, the operator can remove the now-unneeded stages and empty guard. Keep the private backup until the restored installation has been checked. A retry must pass the normal ownership checks without bypasses.

## Limits

The installer attempts rollback for caught errors and retains failed-restore backups. It cannot guarantee an atomic update across three paths after power loss, a forced process kill, or a simultaneous unrelated writer. A clean test run does not establish crash durability. Report incomplete recovery rather than treating an empty error log or a removed guard as success.
