# Native Windows validation: seven findings and current boundaries

Matt directed investigation of all seven native findings and chose **fail closed
where equivalent guarantees cannot be verified**. Source installation/comparison,
snapshot verification/refresh/preparation, proposal generation and publication now
refuse on non-POSIX runtimes before source reads, writes or child processes. This
is a supported-runtime precondition, not a claim that any POSIX host is safe.
Actual file modes, types, reparse metadata, bytes, link spelling/containment,
Git-object proofs and ownership checks remain required. Help and browsing remain
available. See [ADR 0007](adr/0007-fail-closed-native-source-operations.md).

## Exact evidence identities

The parent's existing native verifier reports Windows 11 build 26100, Python
3.12.8 AMD64, Git 2.54.0.windows.1, against published head
`434de392f0fd57ea673e652177f8aae0c007fe64`, tree
`836b7c09fd1b69fbbb9f699fad8aaa95fd4b2f93`. It ran 157 tests, with 58 individually
passing, 78 failures and five errors including subtest outcomes, and 22 skips.
These are reported counts; subtraction cannot derive passing coverage. The full
list of passing native test names is unavailable in this cloud checkout.

Native evidence remains with that verifier at
`C:\codeing\assimilation\pr8-windows-evidence`. Reported SHA-256 values:

| File | Reported SHA-256 |
| --- | --- |
| `unittest.log` | `ae1386e8d9be2570110f32f46fc8a66a84f09490795bf0e8d842648a755d13f1` |
| `native-probe.json` | `4480d7e2ae1a7639cf2988e531793b291c0a64584b53713d09acfc50e600323b` |
| `REPORT.md` | `590c721323eae88ea4de2e7f27aadf15be9bf325b3bbb9efbebb5e9a63dfb850` |

This worker received the findings through the parent and did not independently
read or hash those native files. The reviewed fixture-only local candidate
`48ab9d6678558c980ccc77e10c34e4d8595dd691`, tree
`4a4aeeebdaa96ad6ffd5c43ab7055b9f27f4d949`, passed 157 Linux tests; its prior
receipt and the original candidate remain preserved. Native passing-after evidence
for that candidate has not been supplied. Final integration hashes and actual
checks belong in the publication receipt/PR; the native baseline above is never
silently replaced by a later Linux result.

## Finding-by-finding disposition

| Item | Diagnosis, corrective boundary and evidence limit |
| --- | --- |
| **1. Exact POSIX modes** | Native manifest 0666 and directory 0777 do not satisfy exact 0644/0755 requirements. Linux injection of the reported bits into unchanged source reproduces the manifest, lock, directory and source-file refusals. The new runtime precondition makes unsupported native operation explicit before staging. Exact supported-POSIX checks are retained; no chmod, ACL equivalence or integrity skip is introduced. |
| **2. Git/MSYS fetch denial** | The controlled native diagnostic reports local-file fetch invoking Git's MSYS `sh.exe`, with `NtCreateDirectoryObject` returning `0xC0000022 ACCESS_DENIED`, then fetch exit 128. Init/commit and sparse setup succeeded. The enforcing boundary remains unknown; no product fix is established. The existing native owner alone continues authorized read-only diagnosis. No denied operation is retried, alternate launcher/transport used, or policy relaxed. Shared Git error redaction remains tested on Linux. |
| **3. Symlink/encoding preservation** | Native symlink creation and destination refusal were reported passing, but `core.symlinks=false` leaves the source link as a placeholder and `core.autocrlf=true` permits byte conversion. Native multihop preservation tests stopped at fetch. Linux multihop/Unicode controls preserve exact UTF-8 link payloads and reject placeholders; they do not prove native round-trip. Literal link hashing, actual-link requirements and absolute/escaping/dangling/cyclic/directory-link refusal remain unchanged. No backslash normalization or Git-setting workaround is applied. |
| **4. Reserved-device fixture** | The reviewed fixture uses Git blobs/index entries for `COM¹.txt`, `LPT².md`, `com³`, `lpt¹.log`, resetting to a clean tree per alias. It never creates those filesystem names. Linux tests retain alias rejection before materialization and original-state assertions; native passing-after remains pending and may be blocked by the runtime precondition. |
| **5. Inaccessible Bash alias** | Three Ubuntu workflow shell tests now require Linux before checking executable availability. Linux retains shell/archive coverage; Windows skips are explicit. No Bash/WSL install, alternate launcher or bypass is introduced. |
| **6. Git-ignore CRLF protocol** | The recovery-path fixture now sends NUL-delimited bytes to `git check-ignore -z --stdin`, asserts exit zero and every exact returned path. Linux simulations expose the old CRLF failure and pass with the binary protocol. `.gitignore` is unchanged; native passing-after is pending. |
| **7. Skips and native limits** | All 22 baseline publication skips belong to the POSIX executable-script transport fixture; they are not successful native publication checks. The three Linux shell exclusions are separate. Reparse regressions inject metadata, not real junctions. Junction creation was denied and not retried. Native junction refusal, ACL-denied reads, concurrent substitution races and live host enforcement remain untested. Fetch-blocked tests provide no evidence for later rollback/link/metadata assertions. |

## Debugging and verification limits

Investigators read and applied the actual `diagnosing-bugs` workflow. Linux
synthetic mode and fixture feedback loops were exercised. The exact native MSYS
and link failures cannot be reproduced in this Linux executor; those dependent
diagnosis phases stop rather than manufacture a cause or run prohibited native
probes. The existing desktop owner remains the sole native execution owner.

Unsupported-runtime regression tests exercise public API refusals, nonzero CLI
diagnostics, no child processes/source reads, no guard/stage/output writes and
available help. They simulate runtime eligibility, not Windows ACL enforcement.
The Linux suite continues to exercise actual POSIX mode tamper refusal, exact
source bytes, regular-file/type checks, contained links, synthetic reparse
refusal, ownership and recovery. A new Linux result cannot clear native or live
installation holds. No upstream utilities, private data, live installation,
equipment, credentials, security settings or Windows environment are changed.
