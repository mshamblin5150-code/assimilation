# Choose where your skills live, then review them monthly

This is the setup and maintenance companion to [your blank-project walkthrough](CHAD-BLANK-PROJECT.md). Matt uses personal/global skills. You have **two scope choices**, not two installations you must perform:

1. **Per repository:** this project carries its skills. Choose this when teammates or future agents should use the project's selected versions.
2. **Personal/global:** your local coding clients find your skills across projects. Choose this when you want a personal toolkit like Matt's.

Global means your user on that machine, not every account, device, cloud session or AI website. Neither choice turns on a permanent AI mode or grants permission to act. The commands here are source-supported instructions; no upstream/global install or update was executed while preparing this lesson.

## 1. Choose project or personal scope

First complete the [folder, Git and prerequisite checks](CHAD-BLANK-PROJECT.md). Identify the actual clients: **Codex CLI/IDE** and **Claude Code** are coding clients; Claude's website is not Claude Code. This lesson does not establish account-wide installation into Claude web or ChatGPT web.

Inspect existing skills and plugins before adding anything. Choose one delivery method per client. Back up edited skill directories and their provenance to an approved location before replacing them. A same-name copied skill can be overwritten by an installer; an installed plugin plus copied skill can create a duplicate. Reading the full source and its dependencies remains necessary.

### Track A — install per repository

From the intended repository, choose the actual client. For example, for Codex:

```sh
npx skills@latest add mattpocock/skills -a codex --copy
npx skills@latest list -a codex
```

For Claude Code, substitute `claude-code` for `codex`. If both clients are genuinely intended, supply both selectors. Leave off `-g`; project scope is the CLI's default. Keep interactive selection and review the destination preview. Include `setup-matt-pocock-skills` and the workflow dependencies described in the blank-project lesson. Do not use `--all` or `-y` for this first guided setup.

### Track B — install personal/global skills

After explicitly choosing personal scope, this combines Matt's upstream installer with the CLI's documented global/agent/copy options:

```sh
npx skills@latest add mattpocock/skills -g -a codex -a claude-code --copy
npx skills@latest list -g -a codex -a claude-code
```

Omit a client you do not use. This is **instead of** Track A for those skills, not an instruction to make identical project and personal copies. The CLI can download and execute a package and fetch source even when listing; inspect package identity, permissions, existing content and exact destinations before confirming. `@latest` is moving, not a reproducible version pin.

| Client | Track A: repository directory | Track B: personal directory |
|---|---|---|
| Codex | `.agents/skills/` | `~/.agents/skills/` |
| Claude Code | `.claude/skills/` | `~/.claude/skills/` |

`~` means the installing user's home. Verify the actual paths, not only the printed success message. These commands and paths come from [Matt's installation instructions](https://github.com/mattpocock/skills/blob/59db609eb1e18aaf59b63284d0e52255aff0c63c/README.md), the [CLI reference](https://github.com/vercel-labs/skills/blob/92a9a34ac3bf88e695e468b90c7bf32f163d32c8/docs/commands.md), and [its agent paths](https://github.com/vercel-labs/skills/blob/92a9a34ac3bf88e695e468b90c7bf32f163d32c8/docs/agents.md).

**Done when:** your setup record names A or B, the actual clients, exact destinations, installer/source versions, selected skills, local edits/backups and remaining limitations. Neither a source listing nor an agent's summary establishes installation.

## 2. Verify discovery, collisions and project configuration

Open the actual client and check its skill selector. Explicitly invoke a bounded skill and compare its observed read/behavior with the real source. Codex detects skill changes automatically; restart if changes do not appear. Claude Code watches existing skill directories; if a new top-level directory was created during the session, use its documented `/reload-skills`. [Codex skills](https://learn.chatgpt.com/docs/build-skills), [Claude Code skills](https://code.claude.com/docs/en/skills).

Handle duplicate names deliberately:
- Codex can display both same-named skills; it does not merge their instructions.
- Claude Code documents enterprise, then personal, then project precedence. A personal skill can therefore hide a project skill of the same name. Do not assume the repository copy wins.
- Matt and P-Stack can both contain `tdd`; decide which source you mean before installing either over the other. Preserve any host namespacing and invocation restrictions.

The host behavior above is documented, not tested by this lesson. Global availability does not mean every skill is automatically invoked or that every host enforces all upstream metadata identically.

Still run **setup-matt-pocock-skills once in each new repository**, following [the project-configuration step](CHAD-BLANK-PROJECT.md#6-configure-this-repository-before-planning-the-product). Installing its files globally does not choose that project's tracker, glossary, ADR layout or owner.

### P-Stack and native plugins

Use the [P-Stack source/resource check](CHAD-BLANK-PROJECT.md#4e-add-the-p-stack-material-this-project-needs). For selected self-contained skills installed through the generic CLI, the same A/B scope distinction applies: omit `-g` for A, add it deliberately for B, and verify each actual destination. A copied skill folder does not necessarily include resources outside that folder.

If the client supports a complete native plugin, its delivery mechanism is separate from editable copies. Matt documents a Codex plugin route and a Claude Code plugin route; do not install these on top of identical copies:

```sh
codex plugin marketplace add mattpocock/skills
codex plugin add mattpocock-skills@mattpocock
```

or, in the shell for Claude Code:

```sh
claude plugin install mattpocock-skills@claude-plugins-official
```

Inspect Codex's installed plugin state with `codex plugin list --json`; do not invent a Codex `--scope` flag. Claude's CLI defaults to user scope; a fresh installation may first need the official marketplace registered. Load the plugin in a new session or with `/reload-plugins`. [Codex CLI reference](https://learn.chatgpt.com/docs/cli/reference), [Claude plugin instructions](https://code.claude.com/docs/en/discover-plugins).

P-Stack's [upstream README](https://github.com/cursor/plugins/blob/c742dd61706fbacc1b95f1a20b7b988cf096ce6c/pstack/README.md) documents `/plugin marketplace add cursor/plugins`, then `/plugin install pstack@cursor-plugins` inside Claude Code. For personal scope choose **Install for you**. Its `/pstack:setup-pstack` separately writes `~/.claude/rules/pstack-models.md`; that persistent configuration is an additional explicit choice, not part of merely copying skills. A complete native Codex P-Stack adapter is not established by that source.

## 3. Follow the existing monthly reviewed update process

Matt's Assimilation process is **configured** for the first day of each month at **09:00 UTC** (`0 9 1 * *`), with manual dispatch too. The committed [workflow](../.github/workflows/monthly-skill-review.yml) accepts scheduled/manual work only on the default branch. This documents the existing routine; it does not create a new schedule or prove a particular hosted run succeeded.

For an authorized manual run, open Assimilation's **Actions → Monthly reviewed skill update proposal → Run workflow**, choose the default branch, and inspect the actual run. Repository write access is needed. Reconcile any unresolved run before dispatching another. [GitHub's manual-run instructions](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow?tool=webui).

To prepare without publishing, from a suitable Assimilation checkout with permitted upstream access and a **new** output directory:

```sh
python3 scripts/propose_update.py --output-dir review-update
```

Exit `0` means current, `2` prepared proposal, `3` missing baseline lock, and `1` error. This is Assimilation's source-review tool, not the command that updates Chad's personal skills.

The proposal freezes exact `from_sha` and `to_sha` values. Only the two complete upstream trees, `sources.lock.json`, `sources.snapshot.json` and `sources.update.json` may change. Review source differences, licenses, scripts, dormant configuration and actual host compatibility. In an isolated proposal checkout:

```sh
python3 scripts/snapshot_sources.py verify
python3 -m unittest discover -s tests -v
```

Require checks and independent review for the exact commit plus operator acceptance. **One reviewed merge adopts the snapshots, lock and provenance together. Do not refresh the snapshot again after merging.** The bot never approves, merges, executes upstream code or installs host skills. Administrative settings and approval-required CI retain their separate authority. The [canonical update guide](UPDATES.md) owns the full procedure and recovery/retry rules.

## 4. Each month, update the installation you actually chose

An Assimilation source-snapshot merge does **not** refresh your repository copies, personal copies, native plugins or separately pinned archives. Review each actual installation through its own delivery method.

Before changing files:
1. Record client, scope, source revision/version, skill selection, installer version and relevant lock/provenance.
2. Preserve edited copies and the previous version in an approved backup or version-control snapshot. Inspect the upstream differences and changed resources/licenses; reconcile custom edits rather than assuming the updater merges them.
3. Confirm the actual destination and absence of competing writers. Keep the update bounded; updating all global skills may affect more projects than updating one repository.

For upstream/Vercel CLI copies, `check` reports available updates; exit `1` can mean updates exist, not a broken install. It is not proof that skills work:

```sh
npx skills@latest check
```

Then choose **one matching update track**:

| Your original choice | Monthly update | Which copies change |
|---|---|---|
| A: per repository | From that exact repository: `npx skills@latest update -p` | Its project installations; repeat separately for other repositories |
| B: personal/global | `npx skills@latest update -g` | This user's global installations; not independently copied project versions |

The CLI also supports a named skill, such as `npx skills@latest update wayfinder -g`, when a smaller approved update is appropriate. Re-run `add` deliberately to select newly introduced skills. The [CLI reference](https://github.com/vercel-labs/skills/blob/92a9a34ac3bf88e695e468b90c7bf32f163d32c8/docs/commands.md) defines these operations; do not substitute experimental sync/restore merely because it offers a dry-run flag. Ordinary `add` has no documented `--dry-run` in the inspected version.

For a chosen native Claude Code plugin installation, use its own updater instead of the copied-skills updater:

```sh
claude plugin update mattpocock-skills@claude-plugins-official
claude plugin update pstack@cursor-plugins
```

Run only the line for a plugin actually installed. Inspect automatic-update settings: the official marketplace normally auto-updates; third-party marketplaces do not by default. Do not silently enable automation. Reload plugins or start a new session and verify the loaded version. Refreshing a marketplace listing alone is not proof an installed plugin updated. Matt documents Codex plugin updates at startup; inspect `codex plugin list --json` and the loaded source rather than assuming a monthly review is its only refresh point.

A separately pinned P-Stack archive/source package stays pinned until an approved replacement. Its recorded archive and per-file hashes must match the selected revision; moving upstream `main` does not rewrite an existing archive. Do not mix a new router with stale references or call three copied principles the complete P-Stack workflow.

After any update, compare changed files with the intended scope; inspect all required references; list the chosen project/global scope; check collisions and host discovery; perform a bounded invocation and the project's relevant tests. Record the new resolved version and actual evidence. If something fails, stop using the changed candidate, preserve the failure and compare with the known-good backup. Restore only the chosen, unchanged installation scope with explicit authority; do not delete the only previous copy or use a broad reset/overwrite to erase unrelated work.

**Done when:** each chosen installation has either a reviewed, verified new version or a clearly retained previous version with the update deferred. Record a monthly review date using your existing planning system. This page creates no schedule, modifies no global configuration, and supplies no silent recurring-update authority.
