# Assimilation

**A portable, public-ready, language-independent AI engineering doctrine.**

Assimilation helps a person turn ordinary-language ideas into specified, reviewable work using the complete **Matt Pocock engineering skill collection** and **Lauren Tan's P-Stack skills**, combined with a lightweight Chief of Staff / swarm coordination pattern. Its name describes learning and distributing useful methods—not surrendering control to a machine.

**Operator remains in command.** A user with one ChatGPT conversation can benefit from the documentation; a compatible coding agent with filesystem and Git access can install and use the complete source skills. Multi-agent execution is optional and dependent on available tools and account limits. Assimilation does not grant special AI abilities or magically install tools when a model reads a GitHub URL.

> **Package contents:** This standalone public repository includes four local Assimilation skills, the installer, and a committed source baseline. The upstream collections are fetched separately; they are not bundled in Git.

## For Chad: five-minute orientation

1. **Read this page** and [the operating instructions](AGENTS.md). They say what the system is and how the AI should work.
2. **Using ChatGPT without coding tools?** Follow [the ChatGPT-only start](docs/CHATGPT.md). You can use the thinking and documentation practices without paying for a particular plan; access to tools and projects may vary.
3. **Using a coding agent with a local terminal?** Copy this repository into your own project and run from its root:

   ```sh
   python3 scripts/skills.py install --locked
   ```

   On Windows, `py -3 scripts/skills.py install --locked` is an alternative. **Git and Python 3.10+ are required**; no TypeScript is required. The command fetches the **exact commits in `sources.lock.json`**, saves the full source skill trees locally under `vendor/`, and creates discoverable bridge skills under `.agents/skills/` without hiding upstream references. For a fresh copy without a lock, use `python3 scripts/skills.py install` once to record the initial upstream revisions. The installer refuses unknown vendor content, edited managed content, and unmanaged skill-name collisions. Review source code before installing; don't execute unknown tools blindly.
4. **Ask the agent to read `AGENTS.md`.** Give it a concrete goal in your own words. For nontrivial design ambiguity it should use **`grill-with-docs`** (interview plus documentation). For a large, multi-session effort whose path remains uncertain it should use **`wayfinder`** (map decisions/fog, resolve, then hand off to specification). It can use **all** the installed engineering and P-Stack skills as appropriate, but should not run unrelated skills on every task.
5. **Remain in charge.** The AI may declare *zero blocking fog* with evidence when all in-scope decisions are settled; that is **not** approval to deploy, merge, spend money, publish, or perform other sensitive actions.

**If you only want to tell ChatGPT what to read:** “Read this repository’s `README.md`, `AGENTS.md`, and the linked doctrine, then explain what capabilities you can actually use. Do not claim you installed skills unless you did.” Where ChatGPT cannot access a GitHub repository or its files directly, upload the Markdown files; a link alone is insufficient.

## How it works

**Human operator → Chief of Staff → coordination drones → bounded child agents.** The Chief of Staff gathers results and reports upward. A coordinator has no fixed doctrine-imposed limit on child agents, but concurrency is bounded by actual platform limits, authorization, budget, and avoiding overlapping edits. One of the independent checks is a **claim-and-refutation pair**: one agent develops a supported claim, another independently tries to disprove it, and the coordinator reconciles the evidence.

The original system uses **Number One** as Chief of Staff and **Nexus** (DAVID), **Praeceptor** (Clinical Skills), and **Q-Tos** (department role to be defined by its operator) as coordinating agents. These are examples; Chad names his own coordinators and never needs access to the original projects.

The philosophy: no challenge is dismissed merely as “too big.” Break it down, identify unknowns, investigate alternatives, and report genuine blockers candidly. An agent must not claim work is done without verifiable evidence, invent decisions, or exceed its authorization.

## Where to look

- [How to publish Assimilation publicly](docs/PUBLISH.md) — create the GitHub repository with the current package.

- [Engineering doctrine](docs/DOCTRINE.md) — decision boundaries, autonomy, ADRs, quality and completion.
- [Skill source manifest](docs/SOURCES.md) — precise upstream repositories, licenses, provenance, install choices.
- [Routing skills](docs/WORKFLOW.md) — default grilling, Wayfinder, specs, tickets, implementation, review.
- [Chief of Staff and swarms](docs/SWARMS.md) — reporting tree, unlimited-in-principle children, claim/refutation.
- [GitHub, tool, and privacy safeguards](docs/SAFETY.md).
- [Recover a stopped installation](docs/RECOVERY.md) without deleting the only backup.
- [3D-printing example](docs/THREE-D-PRINTING.md) — CAD model from ordinary-language requirements.
- [For sharing with Chad](docs/HANDOFF.md).
- [ADRs](docs/adr/0001-doctrine-and-authority.md) — recorded rationale; new decisions use [the ADR template](docs/templates/ADR.md).

## Update cadence

The operator chose **monthly reviewed update PRs**, with no automatic approval or merge. The committed `sources.lock.json` records the installed baseline. Each proposal freezes both installed and target commits, so adoption does not race a moving `main` branch.

The scheduled workflow runs only on the default branch. It prepares a plan, publishes only `sources.update.json` on a deterministic update branch, and opens a draft PR. It never installs sources or changes the lock. Repeated runs reuse an unchanged draft; human edits, promoted PRs, closed PRs, and stale baselines stop publication rather than being overwritten.

The implementation uses the approved `contents: write` and `pull-requests: write` job permissions, not an issues grant or a personal access token. Repository policy must also permit Actions PR creation. See [the update guide](docs/UPDATES.md) for activation requirements, review steps, and retry behavior. Configuration in this repository is not evidence that a live workflow run has succeeded.

Without a committed lock, the workflow reports setup needed and skips upstream comparison and publication. It never invents an installed baseline.

## Public by design

This repository contains **no live Open Brain access**, no personal memory archive, no DAVID 2 private source, no credentials, no patient data, and no access delegation to the originating projects. It transfers ideas, not private records. External source collections are fetched directly from their publishers, keeping their own licenses and metadata. [Security and attribution](docs/SAFETY.md).

## Credits

Portable doctrine assembled from engineering lessons of **Matt Shamblin** (GitHub: `mshamblin5150-code`), with upstream skills authored by **Matt Pocock** and **Lauren Tan**. This is an independent starter package and is not an official upstream distribution or a substitute for reading each skill's complete source.
