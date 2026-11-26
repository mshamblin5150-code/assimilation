# Native Windows handle verification: design and acceptance contract

Status: **proposal only** for Issue #11 / draft PR #12. No implementation, installation, privilege changes, or authorization to use this as a write gate.

## Threat and trust boundaries

String-based `Path.lstat()` checks in `windows_fixture_observer.py` are raceable. A link or parent can be substituted after inspection. A successful temporary-fixture test is not evidence that a destination is confined, owned, or safe for writes.

Before a native implementation, obtain an independent review of the following Windows API contract. Use Windows native APIs on test-owned disposable paths only; do not access real user destinations or elevate.

## Proposed observation sequence

1. Establish a test-owned absolute fixture root. Reject UNC/device/extended namespaces unless explicitly reviewed. Record volume/filesystem semantics and reject unsupported filesystems.
2. Open root and each ancestor using a native Windows handle with reparse traversal disabled, including `FILE_FLAG_OPEN_REPARSE_POINT` and `FILE_FLAG_BACKUP_SEMANTICS` as applicable. Treat API failure, unknown reparse tags, and access denial as refusal, never a retry with relaxed flags.
3. For each handle, query native file ID and volume serial, file attributes/reparse tag, and security descriptor (owner/DACL/inheritance). Define precisely which object is being inspected, whether the API follows a link, and how the result is tied to the opened handle.
4. Establish parent-to-child containment using a separately reviewed handle-relative opening strategy. **Do not assume** that opening an absolute path with `OPEN_REPARSE_POINT` prevents traversal of all intermediate components; it does not provide a proof of ancestry by itself.
5. Hold relevant handles and revalidate IDs, security descriptors, and expected content immediately before any future commit. Document Windows share modes, rename/delete semantics, and concurrency guarantees; handles alone do not automatically prevent swaps.
6. Refuse missing or ambiguous identity, junction/symlink/mount-point substitution, unrecognized tags, inherited ACL uncertainty, unexpected owner, or changed volume. No attempt to repair permissions.
7. On failure, preserve the user's data and a minimal non-sensitive evidence record. Fixture cleanup must be bounded to proven test-owned objects, with no link traversal.

## Negative test cases for a separately reviewed native implementation

- Regular file and directory: stable handle identity and expected attributes.
- File symlink, directory symlink, junction, and mount-point/reparse tag: explicit refusal, including when substituted at an ancestor.
- Unknown reparse tag, inaccessible object, unexpected owner/DACL, unsupported volume: refusal.
- Parent renamed/replaced between observations; leaf swapped before final revalidation; two writers: refusal without changing either target.
- Existing unmanaged sentinel: no reads of payload and no overwrite, rename, or delete.
- Explicitly distinguish test skips due to insufficient symlink/junction privileges from successful security tests.

## Evidence required before moving beyond design

- Security review of the exact Win32/NT API choices, handle-relative ancestry proof, share-mode contract, and race assumptions.
- Exact-head Windows and Ubuntu CI logs; tests on isolated disposable fixtures only.
- Demonstrated fail-closed behavior with negative cases, not only happy-path observations.
- Separate explicit approval for implementation and later installation. PR remains draft/unmerged until independent review and human merge authorization.

## Existing source and remaining contracts

This source inspection uses PR #12 head
`07aa4b5e60990d9d623b54634553af3d60986783`. It does not record a new test
run or native qualification. The existing observers and synthetic models do not
implement the installation contract above.

| Existing source | What it does | What remains unproved |
| --- | --- | --- |
| [`WindowsOpener.retained_file`](../scripts/windows_opener.py) | Holds one opener's operation lock during a query, requires owned file and ancestor objects, and checks file metadata and reader context before and after the query. | The lock does not exclude another opener, process, or external handle closure. Retained ancestor objects do not prove namespace confinement. |
| [`observe_file_streams`](../scripts/windows_stream_query.py) | Makes one bounded `FileStreamInfo` query through the supplied reader and compares endpoint metadata and context. | Equal snapshots do not exclude changes between observations, authenticate payload bytes, or establish a native writer-exclusion contract. |
| [`parse_proposal`](../scripts/windows_view_proposal.py) | Checks the create-only declaration and returns canonical bytes with matching view and plan digests. | A declared digest does not verify staged bytes. The parser requires destination and recovery bindings to remain `unqualified`. |
| [`SimulatedTransaction`](../scripts/windows_view_transaction_model.py) | Compares caller-supplied digest and identity tokens through in-memory transitions. | It has no durable journal, authenticated recovery owner, interruption recovery, or native write operation. |

[`test_windows_opener.py`](../tests/test_windows_opener.py) uses recorded API
completions. Its cases cover public lifecycle reentry, retained ancestry, observed
changes, and cleanup failures. Those cases do not instantiate a native opener.
They must not be reported as cross-process exclusion or native share-mode tests.

The next design work has three distinct contracts:

- Native acquisition and exclusion must name the actual access rights, share
  modes, handle-relative opening rules, and supported filesystem behavior.
  The contract must explain what prevents a competing writer or ancestor
  substitution throughout the operation, rather than relying on endpoint equality.
- Staged-byte custody must bind the reviewed proposal to verified source bytes,
  retained staging objects, and the destination immediately before an effect.
  A proposal digest alone supplies none of those bindings.
- Recovery must define an authenticated owner, durable journal transitions,
  replay refusal, and the treatment of missing or tampered artifacts. The
  in-memory model's `aborted` state does not describe crash recovery.

These contracts remain proposals for the issue's decision owner, Chad, with
independent security review. No choice of locking, journal format, or native
adapter is accepted here. The recorded local exact-plan consent requirement
still applies. Native adversarial execution, installer activation, and merge
remain subject to the existing gates.
