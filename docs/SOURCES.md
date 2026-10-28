# Complete upstream skills and provenance

Assimilation links to and can install the **complete published source trees**, not shortened interpretations. Upstream metadata, references, and licenses remain intact under `vendor/` after installation. Upstream changes are not automatically trusted or merged.

| Collection | Upstream | Scope installed | License | Original historical pin |
| --- | --- | --- | --- | --- |
| Matt Pocock | https://github.com/mattpocock/skills | Entire `skills/` tree, supporting `docs/`, README and LICENSE | MIT (source LICENSE) | `49dd158d1076134a641b33efb035946536778336` |
| P-Stack (Lauren Tan) | https://github.com/cursor/plugins/tree/main/pstack | Entire `pstack/` subtree, including its `skills/`, `agents/`, references, assets and plugin metadata | MIT (pstack/LICENSE) | `ccb5507cec1546dc88135c1139c811e6c59115ba`, historical version `0.15.15` |

These historical reference pins are retained from the original starter. They are provenance notes, not an installed baseline or a claim about current upstream versions. The installer obtains `main` at setup, saves actual SHA and time in `sources.lock.json`, and creates local wrappers pointing to each upstream skill's complete `SKILL.md`. It preserves unrelated skills already in a previously managed local skills directory, and refuses an unrecognized occupied directory rather than overwriting it. Edited owned content and legacy ownership markers without fingerprints stop updates. Follow [the recovery procedure](RECOVERY.md) instead of forcing replacement. The presence of a wrapper alone does not prove its instructions were read or executed.

The upstream collections are not bundled in Git. The committed `sources.lock.json` is the actual installed baseline; the historical table above is not. The initial reviewed baseline contains Matt commit `59db609eb1e18aaf59b63284d0e52255aff0c63c` and P-Stack commit `c742dd61706fbacc1b95f1a20b7b988cf096ce6c`. Their declared scopes contain 148 and 573 Git blobs, with 20 engineering and 58 P-Stack bridges. Read `vendor/pstack/.cursor-plugin/plugin.json` after installation for the installed version.

### Installer design

```sh
python3 scripts/skills.py install --locked  # reproduce the committed baseline
# Only when no lock exists: python3 scripts/skills.py install
python3 scripts/skills.py check    # compare current sources with lock
python3 scripts/propose_update.py --output-dir review-update  # freeze proposed commits
# Review review-update/PULL_REQUEST.md and the upstream diffs before adoption.
python3 scripts/skills.py install --approve-update --update-plan review-update/sources.update.json
python3 -m unittest discover -s tests -v
```

For a clean checkout with a committed lock, `python3 scripts/skills.py install --locked` installs those exact SHAs instead of latest `main`. It does not authorize replacing an existing installation. See [reviewed updates](UPDATES.md).

The installer requires **Git** and Python ≥3.10. It deliberately avoids npm, TypeScript, provider credentials, external plug-in execution and direct network access to private projects. The local `vendor/` tree and `.agents/skills/` generated bridges are ignored by Git; commit `sources.lock.json` after a successful install if you want automated monthly comparison. On some hosts the original publisher's native plugin installer is a better option; do **not** install duplicate copies of identical skills into one agent.

P-Stack can use Cursor-native features and model routing; those do not automatically become available in Codex or ChatGPT. When a tool is missing, adapt using supported capabilities or report the limitation.
