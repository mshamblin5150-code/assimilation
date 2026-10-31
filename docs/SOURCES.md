# Complete upstream sources and provenance

The actual source collections are browsable in this repository, not summaries or installer stubs:

| Collection | Visible scope | Initial pinned commit | Initial source count |
| --- | --- | --- | --- |
| [Matt Pocock](../upstream/matt-pocock/) | Entire tracked [mattpocock/skills](https://github.com/mattpocock/skills) repository | `59db609eb1e18aaf59b63284d0e52255aff0c63c` | 194 blobs; 38 SKILL.md files |
| [P-Stack / Lauren Tan](../upstream/pstack/) | Entire [cursor/plugins/pstack](https://github.com/cursor/plugins/tree/main/pstack) subtree | `c742dd61706fbacc1b95f1a20b7b988cf096ce6c` | 573 blobs; 61 SKILL.md files, including 3 dormant Benny skills |

Matt's initial skill breakdown is 20 engineering, 7 productivity, 4 miscellaneous, and 7 in-progress. Both collections retain their original MIT licenses and copyright notices. See [supplemental third-party attribution](../THIRD_PARTY_NOTICES.md), including HumanLayer material credited by Matt's PR skill. Preserve source bytes and adjacent credits; place supplemental notices outside managed snapshots.

`sources.lock.json` is the current pin authority. `sources.snapshot.json` records each scope's commit and Git tree hashes, each file's Git mode/blob SHA/SHA-256/size, and base64 raw public commit/root-tree proofs. Verification rebuilds the exact scope tree, associates it with its pinned commit, and rejects missing, extra, or edited files. These content proofs are not upstream signatures or safety certification.

```sh
python3 scripts/snapshot_sources.py verify  # offline; no source execution
```

Exact snapshot verification has been tested on Linux with Python 3.12. Source operations require a POSIX runtime and preserved exact file modes and literal file symlinks. Native Windows operations explicitly refuse before starting: reported permission metadata and link materialization do not establish equivalent guarantees. POSIX eligibility alone is insufficient; the existing per-file mode, type, content, link and provenance checks still apply. See [native validation findings and remaining limits](WINDOWS_VALIDATION.md) and [ADR 0007](adr/0007-fail-closed-native-source-operations.md). Browsing the source files does not require that verifier.

Do not hand-edit managed source snapshots. Monthly reviewed PRs contain the full proposed snapshots, minimal updated pin lock, provenance, and frozen plan together. A reviewed merge adopts the files and matching metadata atomically. Proposed pins do not invent installation timestamps or bridge counts. See [monthly updates](UPDATES.md).

## Visible sources versus local host installation

Browsing `upstream/` does not install a plugin, execute scripts, activate nested workflows, or make host-specific capabilities available. Choose appropriate skill instructions explicitly under the current project/operator authority. Dormant or in-progress material is preserved because the collection is complete, not because its use was approved.

The optional existing installer remains separate:

```sh
python3 scripts/skills.py install --locked  # fresh checkout: materialize current pinned host sources
python3 scripts/skills.py check             # compare source heads with lock
```

The installer requires Git and Python 3.10+. Its Matt sparse scope contains the full `skills/` and `docs/` trees plus root files, while its P-Stack scope is the whole `pstack/` subtree. At the initial baseline those installer scopes contained 148 and 573 blobs, exposing 20 engineering and 58 P-Stack bridge skills. Those counts are not the larger visible-source count above. Generated `vendor/` and `.agents/skills/` stay local and ignored. P-Stack's initial version is `0.15.36`; consult the pinned `.cursor-plugin/plugin.json`, not a claim about current upstream.

For a fresh installation without a lock, plain `install` records actual SHAs/time. With a committed lock use `--locked`, which does not authorize replacing an existing installation. Existing managed installations require explicit update approval and intact ownership; changed owned files, unknown vendor content, and conflicting unmanaged skills fail closed. The installer supports `--approve-update --update-plan PATH` for an explicitly reviewed plan whose `from_sha` still matches the local lock. It is not a post-merge snapshot step. Follow [recovery](RECOVERY.md), rather than forcing a mismatch.

On some hosts a publisher's native plugin installer may be preferable. Avoid duplicate identical skills. Cursor-native features and model routing do not automatically exist in Codex or ChatGPT; use supported alternatives or report the limitation.

## Maintainer snapshot preparation

The snapshot CLI is separate from host installation:

- `refresh`: retrieve the exact current lock pins into initially absent managed snapshot directories. Existing intact snapshots require `refresh --approve-update`.
- `prepare --update-plan PATH --output-dir NEW`: validate the existing baseline and prepare a complete target snapshot package in a new directory; never change the checkout's lock or sources.
- `verify [--root DIR]`: offline complete-file, mode, link, license, content, and provenance checks.

Fetches read public source Git objects only and never check out or execute upstream hooks/scripts. Unexpected license inventory/bytes or recognized private-key/GitHub-token signatures stop preparation. These narrow signatures do not find every secret or establish semantic code safety. Snapshot limits are 10,000 files per collection, 16 MiB per blob, 128 MiB of combined source bytes, a 32 MiB manifest, and 2,000,000 bytes for each proof or lock metadata input. Git objects may be fetched before size inspection; these limits bound source materialization, not all network transfer. Oversized inputs fail closed for review rather than silently truncating a collection. Snapshot stages and retained backups must never be published; see [recovery](RECOVERY.md).

## Historical starter references

The original starter retained Matt commit `49dd158d1076134a641b33efb035946536778336` and P-Stack commit `ccb5507cec1546dc88135c1139c811e6c59115ba` (historical version `0.15.15`) as planning references. They are historical provenance, not the current lock or claims that those versions were installed here.
