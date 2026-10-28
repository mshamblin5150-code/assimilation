# Assimilation

> **New agent with only this URL? [Start here and perform one real task](START_HERE.md).** Establish actual capabilities, read relevant original skills, act within authority, and deliver evidence—not a doctrine recital.

**A portable, public-ready, language-independent AI engineering doctrine.**

Assimilation helps a person turn ordinary-language ideas into specified, reviewable work using the complete **Matt Pocock source collection** and **Lauren Tan's P-Stack skills**, combined with a lightweight Chief of Staff / swarm coordination pattern. Its name describes learning and distributing useful methods—not surrendering control to a machine.

**Operator remains in command.** A user with one ChatGPT conversation can benefit from the documentation; a compatible coding agent with filesystem and Git access can install and use the complete source skills. Multi-agent execution is optional and dependent on available tools and account limits. Assimilation does not grant special AI abilities or magically install tools when a model reads a GitHub URL.

> **Browse the actual skills:** [Matt Pocock — complete repository](upstream/matt-pocock/) · [P-Stack — complete subtree](upstream/pstack/) · [source index and authority boundary](upstream/README.md).
>
> This repository includes four local Assimilation skills, full upstream reference sources, their pinned lock/provenance, and an optional host installer. The initial visible baseline contains **38 Matt skill files** (20 engineering, 7 productivity, 4 miscellaneous, 7 in-progress) and **61 P-Stack skill files** (including 3 dormant Benny skills). Browsable source is not automatic host activation.

## For Chad: five-minute orientation

1. **Give the agent a concrete goal and [Start here](START_HERE.md).** It should inspect its actual capabilities and project, select and read original skills, then perform a bounded task. [Operating instructions](AGENTS.md) preserve the authority boundaries.
2. **Using ChatGPT without coding tools?** Follow [the ChatGPT-only start](docs/CHATGPT.md). You can use the thinking and documentation practices without paying for a particular plan; access to tools and projects may vary.
3. **Using a coding agent with a local terminal?** Clone this repository. You can already read the complete sources under `upstream/`; verify them offline with `python3 scripts/snapshot_sources.py verify`. If you also want generated host-discoverable bridges, run from a fresh checkout:

   ```sh
   python3 scripts/skills.py install --locked
   ```

   On Windows, `py -3 scripts/skills.py install --locked` is an alternative. **Git and Python 3.10+ are required**; no TypeScript is required. The command fetches the **exact commits in `sources.lock.json`**, saves its declared source scope locally under `vendor/`, and creates engineering/P-Stack bridge skills under `.agents/skills/` without hiding upstream references. For a fresh copy without a lock, use `python3 scripts/skills.py install` once to record the initial upstream revisions. The installer refuses unknown vendor content, edited managed content, and unmanaged skill-name collisions. Review source code before installing; don't execute unknown tools blindly.
4. **Ask the agent to read `AGENTS.md`.** Give it a concrete goal in your own words. For nontrivial design ambiguity it should use **`grill-with-docs`** (interview plus documentation). For a large, multi-session effort whose path remains uncertain it should use **`wayfinder`** (map decisions/fog, resolve, then hand off to specification). It can use **all** the installed engineering and P-Stack skills as appropriate, but should not run unrelated skills on every task.
5. **Remain in charge.** The AI may declare *zero blocking fog* with evidence when all in-scope decisions are settled; that is **not** approval to deploy, merge, spend money, publish, or perform other sensitive actions.

**Copyable start:** “Use this repository’s `START_HERE.md` for this task: [my outcome]. Work in [my project or supplied files], within [my authorized scope]. Read the applicable original skills and produce the result with verification evidence. Report unavailable capabilities rather than simulating them.” If repository files are inaccessible, supply the specific Markdown files requested; a link alone is insufficient.

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

The operator chose **monthly reviewed update PRs**, with no automatic approval or merge. The committed `sources.lock.json` pins the visible source baseline; `sources.snapshot.json` verifies its complete trees. Each proposal freezes both baseline and target commits, so adoption does not race a moving `main` branch.

The scheduled workflow runs only on the default branch. It prepares complete proposed source trees, an updated pin lock, provenance, and a frozen plan on a deterministic update branch, then opens a draft PR. One reviewed merge adopts them together. It never installs host skills or executes upstream code. Repeated runs reuse an unchanged draft; human edits, promoted PRs, closed PRs, and stale baselines stop publication rather than being overwritten.

The implementation uses the approved `contents: write` and `pull-requests: write` job permissions, not an issues grant or a personal access token. Repository policy must also permit Actions PR creation. See [the update guide](docs/UPDATES.md) for activation requirements, review steps, and retry behavior. Configuration in this repository is not evidence that a live workflow run has succeeded.

Without a committed lock, the workflow reports setup needed and skips upstream comparison and publication. It never invents an installed baseline.

## Public by design

This repository contains **no live Open Brain access**, no personal memory archive, no DAVID 2 private source, no credentials, no patient data, and no access delegation to the originating projects. It transfers ideas, not private records. Visible source collections preserve their publishers' licenses, attribution, and metadata. Nested workflows, agent instructions, plugins, and scripts remain reference data, not execution or activation authority. [Security and attribution](docs/SAFETY.md); [third-party notices](THIRD_PARTY_NOTICES.md).

## Credits

Portable doctrine assembled from engineering lessons of **Matt Shamblin** (GitHub: `mshamblin5150-code`), with upstream skills authored by **Matt Pocock** and **Lauren Tan**. This is an independent starter package and is not an official upstream distribution or a substitute for reading each skill's complete source.
