# Use or publish an Assimilation copy

The standalone repository is public at [mshamblin5150-code/assimilation](https://github.com/mshamblin5150-code/assimilation). Reading or copying it does not grant access to the originating projects, install upstream tools, or enable GitHub Actions settings.

## Use the public repository

With Git and Python 3.10+:

```sh
git clone https://github.com/mshamblin5150-code/assimilation.git
cd assimilation
python3 scripts/snapshot_sources.py verify
# Optional host bridges in a fresh checkout:
python3 scripts/skills.py install --locked
python3 -m unittest discover -s tests -v
```

The complete upstream source files are already browsable under `upstream/`. Offline verification checks their pin association and exact bytes. The optional locked install reproduces the committed source pins for host bridges. It creates locally ignored `vendor/` and `.agents/skills/` directories without executing upstream setup scripts. On Windows, use `py -3` instead of `python3` if needed. Review installed instructions before granting tools or agents permission to use them.

If your own fresh copy has no `sources.lock.json`, plain `install` records an initial baseline from current upstream `main`. Before enabling monthly comparisons, review that lock and use `snapshot_sources.py refresh` to create its complete visible snapshot and provenance. Commit all three together. Do not substitute historical pins from prose for an actual baseline.

## Publish your own copy

Repository creation, branch pushes, and public uploads need the owner's authorization. Use your own repository name and existing approved authentication. Inspect staged changes with `git status` and `git diff --cached` before publication.

Keep `.assimilation-stage-*`, `.assimilation-snapshot-stage-*` at both staging locations, `.assimilation-install.lock`, `vendor/`, and `.agents/` out of commits and uploads. The managed `upstream/` source files and root provenance are intentionally public. Never include private project code, personal files, patient data, credentials, or retained recovery backups. Preserve the MIT license and upstream attribution. Publication must retain the directory structure, binary bytes, executable modes, and symlinks. Verify the committed tree, not just a file-count summary.

## Configure reviewed updates

The monthly workflow can publish frozen proposals as draft PRs using its approved job permissions. Each PR contains complete proposed source trees, updated pins, provenance, and the plan. It never installs host skills, executes upstream code, approves, or merges. One reviewed merge adopts the visible snapshot and matching lock. The repository must separately allow Actions to create PRs. Follow [the update guide](UPDATES.md) for repository settings, exact-SHA adoption, retries, and verification of live results.
