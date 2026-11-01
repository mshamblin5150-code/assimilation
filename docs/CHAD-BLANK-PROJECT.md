# Build your own project, one step at a time

**A guided lesson.** This is a guided series of sessions, not a script to paste into a terminal all at once. A person makes the product decisions; the agent investigates, explains, records and implements within the agreed scope.

We will start where a beginner actually starts: **What do I want to make? Where do I put it? How does that folder become a project? How do I give the agent the right skills?**

Then we will walk the whole route:

**Choose project → choose folder → initialize Git → install or explicitly load skills → configure the project → Wayfinder → resolve decision tickets with grill-with-docs and appropriate investigation → land the decision records → to-spec → to-tickets → implement with selected P-Stack methods → review → verified delivery.**

Say **“Wait, what? Show me using my project.”** whenever an explanation stops making sense.

## Before the first session

Use a small, nonclinical project with invented data. A possible example is **My Reading Shelf**: enter invented book titles, see a list and mark a title as finished. This is an example, not a requirement Chad has already accepted.

You need an agent that can read your chosen files. Creating files, running Git and tests, or installing skills also needs a suitable terminal and permissions. A browser-only conversation can rehearse the decisions, but cannot honestly claim it created the repository or installed anything.

The agent should first establish the actual host and operating system. “Windows computer,” “Linux terminal,” “Codex,” “Claude Code,” and “ChatGPT conversation” are not interchangeable. Ask which environment Chad intends to use rather than assuming his setup matches Matt's.

**Choose one installation scope:** **A — per repository**, so this project carries its skills; or **B — personal/global**, as Matt uses, so your local coding clients can find them across projects. You do not need both. Assimilation is the teaching reference, not a required installer. Both tracks use upstream-supported installation methods and have their own monthly update step. The exact host and installed tool versions still need verification; these are source-supported instructions, not a completed installation on your host.

### The teaching rhythm

For every step, the guide should:
1. Explain what the step changes in plain language.
2. Show the exact proposed folder, command or document.
3. Check that the necessary authority and prerequisites exist.
4. Perform one step, then inspect its actual result.
5. State what is proved and what remains undone.

Do not ask again for permission already granted. Do pause when a new operation changes the scope—for example installing missing software, changing security settings, publishing a repository or accessing personal documents. If interactive computer work needs the owner's clicks, arrange that availability before starting the dependent work.

## 1. Pick your project and give it a name

Ask:

> What is one small thing you would like your project to help you do?

Let Chad answer. Then distinguish:
- The friendly name, such as **My Reading Shelf**.
- A simple folder name, such as `my-reading-shelf`.
- The first useful outcome, such as “I can list invented book titles.”
- What is outside this first release, such as accounts, payments, synchronization or real personal files.

A project name is not necessarily a skill name. We are building a project that uses engineering skills; we are not required to author a new custom skill in this first step.

Write a short project note only after its content and location are agreed. A proposal remains a proposal until Chad chooses it.

**Done when:** Chad can describe the outcome in one sentence, name its owner, and give one example of success.

## 2. Pick a safe folder

Choose an ordinary local directory under a location Chad controls. Use a new, dedicated folder outside an existing repository, synced/cloud folders, network shares and valuable work. The agent needs the exact absolute path; “somewhere in Documents” is not enough.

Before creating anything:
- Confirm the parent location and the intended new folder.
- Confirm the new folder does not already hold work.
- Check whether the location is already inside another Git repository.
- Stop on an unexpected link, junction, occupied name, denied location or competing writer.
- Keep source downloads and temporary packages out of personal-document folders.

The following are **illustrations**. Replace the path with the selected path, and use only the block matching the actual shell.

PowerShell, with an existing trusted terminal:

```powershell
$Project = 'C:\Projects\my-reading-shelf'
New-Item -ItemType Directory -Path $Project
Set-Location -LiteralPath $Project
Get-Location
Get-ChildItem -Force
```

POSIX shell:

```sh
PROJECT='/home/learner/Projects/my-reading-shelf'
mkdir "$PROJECT"
cd "$PROJECT"
pwd
ls -la
```

The parent folder must already exist and be approved. A directory-creation failure is a stop to inspect, not a reason to add a force/overwrite option. Do not continue in the previous directory if changing location fails.

**Done when:** the displayed absolute location is the intended new empty folder. Nothing elsewhere was moved or changed.

## 3. Make that folder a Git repository

Explain:

> Git keeps snapshots of changes in this folder. GitHub is an optional online place to share them. Making a local Git repository does not upload anything.

Use an already installed, trusted Git. If Git is missing, unavailable or has a known access denial, stop and explain the exact missing prerequisite. Installing Git, changing PATH or switching launch mechanisms is a separate setup decision. A previous denial is not repaired by trying another shell.

Before initialization, check that Git does not identify an enclosing repository. A command reporting an existing parent repository is a reason to choose another location, not permission to initialize inside it. Unexpected `GIT_DIR`/`GIT_WORK_TREE` overrides also need reconciliation before proceeding.

Run this inspection **before** initialization, from the selected empty folder:

```sh
git rev-parse --show-toplevel
```

If it prints an existing repository root, stop and choose a folder outside that repository. For a genuinely uninitialized folder, Git reports that it is not a repository; that expected result differs from a permission, executable or configuration failure, which needs investigation.

After the location and existing Git are verified:

```sh
git init --initial-branch=main
git rev-parse --show-toplevel
git status
git remote -v
```

These Git arguments work in either shell when `git` is the verified executable. Read each result:
- The repository root must be exactly the selected project folder.
- The initial branch should be `main`, with no commits yet.
- A new local repository should have no remote unless one was deliberately configured.

Do not set a global Git identity as a convenience. Before the first commit, inspect the applicable identity and ask for the learner's chosen identity if missing; any approved adjustment should be scoped appropriately to this project. Never invent an author name or email.

[Git's init documentation](https://git-scm.com/docs/git-init) describes the new repository and initial branch. [Cloning](https://git-scm.com/docs/git-clone) is a different operation: it already creates a Git repository and brings existing history. A clone does not need another `git init`.

**Done when:** the correct folder is a local Git repository, and Chad can explain that nothing has been published.

## 4. Choose one scope and install the upstream skills

We are equipping Chad's new project with **Matt Pocock's upstream skills**, not installing Assimilation or copying an Assimilation checkout. Choose A for project files or B for personal/global availability. Matt can guide either route.

Matt's [upstream README](https://github.com/mattpocock/skills/blob/59db609eb1e18aaf59b63284d0e52255aff0c63c/README.md) documents editable project files through the `skills` CLI. The [CLI's own documentation](https://github.com/vercel-labs/skills/blob/92a9a34ac3bf88e695e468b90c7bf32f163d32c8/docs/commands.md) confirms project-local installation is the default. For this project-local route, omit `-g`. If you intentionally want skills available across your repositories instead, follow [the personal/global setup option](CHAD-SKILLS-MAINTENANCE.md#1-choose-project-or-personal-scope), then return here. Choose one delivery method per client and resolve duplicate names before mixing scopes.

This is independent of Assimilation's optional Python installer. Its native-Windows restriction does not establish that these upstream installation routes are blocked.

### 4A. Check the tools before downloading anything

Keep the terminal in the repository created in step 3. Verify its location again:

```sh
git rev-parse --show-toplevel
git status --short
```

Use already installed, trusted Git, Node.js and npm. The inspected `skills` CLI source, version 1.7.4, currently declares **Node.js 22.20 or later**. Check the actual chosen package/version before teaching; an older cached CLI can have different requirements.

```sh
git --version
node --version
npm --version
```

If a tool is missing, explain which prerequisite is missing and arrange its approved installation. Do not install software, change PATH, elevate, disable security controls or switch launchers merely to make a command run. Windows PowerShell may report an execution-policy problem; preserve that exact result instead of prescribing a blanket policy change.

The first `npx` call may download and execute a package and use npm's cache outside the repository. It is not a purely read-only version probe. Confirm authority for that dependency download/execution and the public upstream reads before running it. Do not ask the learner for a token to install a public collection.

For the teaching run, the instructor should record the selected CLI version, source revision, installation method and destination. The commands below mirror the publisher's current `@latest` instruction; do not call them reproducibly pinned. Before a repeatable classroom run, freeze and verify the intended package/source versions using supported options and retain the actual output.

### 4B. Preview Matt's available skills

After the permitted npm execution and source fetch are established:

```sh
npx skills@latest add mattpocock/skills --list
```

This lists source skills without installing them into the project; it can still fetch source and execute the CLI. Read the actual list. Do not substitute a hard-coded count.

For this workflow include:
- setup-matt-pocock-skills
- wayfinder
- grill-with-docs, grilling and domain-modeling
- to-spec and to-tickets
- implement, tdd and code-review
- codebase-design, research and prototype where their workflows need them
- pr, handoff, writing-for-agents and wait-what as useful companions

Use the actual source dependencies as the final selection authority. Installing only a thin orchestrator without the primitives it calls is not complete setup.

Inspect existing project skills and available plugins first. Matt's README says to pick one delivery method per agent; a plugin plus identical copied skills can produce duplicates. The CLI is not assumed to preserve an edited same-name destination: stop on existing/colliding content and reconcile it before installation.

### 4C. Track A — install per repository

The publisher's installation entry is:

```sh
npx skills@latest add mattpocock/skills
```

Its interactive choices let Chad select skills, the actual coding agent and installation method. Choose **project** scope. For a beginner who wants ordinary editable files, especially when link privileges are uncertain, the CLI documents an explicit copy method:

```sh
npx skills@latest add mattpocock/skills --copy
```

**Run one of those alternatives, not both.** Copy is a supported method of this CLI, not a claim that Assimilation's source-preservation installer now supports flattened links.

If the actual host is already known, use its documented agent selector. Examples:

```sh
npx skills@latest add mattpocock/skills -a codex --copy
```

or:

```sh
npx skills@latest add mattpocock/skills -a claude-code --copy
```

Again, choose the single correct command. Do not paste both. Omit `-a` when the chooser is useful. Do not use `--all`: the inspected CLI defines it as all skills to all agents without prompts, not just “everything relevant to my project.” Do not use `-y` during this first guided setup.

Before accepting the install preview:
1. Read the selected skills.
2. Check the selected host.
3. Check every shown destination belongs to the intended project.
4. Check that no existing skill or edited file would be replaced.
5. Confirm the requested copy/project scope.
6. Stop if the preview differs from the agreed setup.

The documented project paths include `.agents/skills/` for Codex and Cursor and `.claude/skills/` for Claude Code. Inspect what this actual CLI version created rather than assuming all hosts share one directory.

The CLI documents telemetry and security-audit requests. The instructor should explain that choice; its documented session opt-outs are `DISABLE_TELEMETRY=1` or `DO_NOT_TRACK=1`. Set one only using the actual shell's syntax and retain the learner's preference. Do not describe an install as network-free.

**Done when:** the install reports the chosen project destinations, those files are actually present, and their full required references are readable. If you chose A, skip Track B. Host discovery and behavior are checked in step 5, not inferred from the installer exit.

### 4D. Track B — install personal/global skills

Choose this **instead of Track A** when you want skills available across your local projects, as Matt does. Global means this user on this machine, not every device, account, cloud task or AI website.

For the actual clients you use, the upstream installer and CLI support:

```sh
npx skills@latest add mattpocock/skills -g -a codex -a claude-code --copy
```

Omit a client you do not use. Keep interactive skill selection and include the same workflow dependencies. Review every destination before confirming: Codex's documented personal directory is `~/.agents/skills/`; Claude Code's is `~/.claude/skills/`. `~` means your home directory. These commands install for **Codex and Claude Code**, not Claude's website. Read [the full scope and host guidance](CHAD-SKILLS-MAINTENANCE.md#1-choose-project-or-personal-scope) before installing.

Inspect existing copies and plugins first. Codex can expose both same-named skills; Claude Code documents enterprise, then personal, then project precedence, so a personal copy can hide a repository copy. Choose one delivery method per client and reconcile collisions rather than assuming project files always win.

Global availability is not automatic invocation or project configuration. Preserve explicit-only metadata and still run `setup-matt-pocock-skills` once in each new repository. The global command is documented, not executed during this lesson's preparation.

**Done when:** the chosen personal destinations and sources are verified and no unintended project copy was also installed. Continue with P-Stack selection and step 5, using the global listing command there.

### 4E. Add the P-Stack material this project needs

P-Stack is a separate collection, not a hidden part of Matt's installation. Start with the small principles used in implementation; add broader workflows when their dependencies and host requirements are understood.

The generic CLI supports a direct repository-subdirectory URL. Scope discovery to P-Stack instead of the entire Cursor plugin marketplace:

```sh
npx skills@latest add https://github.com/cursor/plugins/tree/main/pstack --list
```

This is a source-listing command built from the CLI's documented subdirectory source format. It was not executed during preparation of this lesson. Inspect the returned list before constructing the actual install selection.

For the initial setup, select the actual listed entries:
- principle-test-behavior-not-implementation
- principle-prove-it-works
- principle-foundational-thinking

After preview/source review, the corresponding project-copy selection is:

```sh
npx skills@latest add https://github.com/cursor/plugins/tree/main/pstack --copy --skill principle-test-behavior-not-implementation --skill principle-prove-it-works --skill principle-foundational-thinking
```

Choose only the intended agent and your selected A/B scope in the prompts. The displayed command omits `-g` for Track A; for Track B add `-g` deliberately and verify the personal destinations. These three inspected principle sources are self-contained prose; this is **not** an installation of every P-Stack runtime capability. Verify the returned names, files, sidecars and license/attribution preservation. If discovery or references differ, stop and inspect rather than broadening to the entire repository.

For complete workflows such as `architect`, `arena`, `interrogate` or `poteto-mode`, inspect the entire referenced resource closure. They can need sibling skills, role briefs, playbooks, scripts and host features outside an individual skill folder. A copied SKILL.md alone is not proof those resources were installed. Both collections contain a skill named `tdd`; do not overwrite Matt's TDD or create an ambiguous duplicate by bulk-installing both collections.

P-Stack's own README also documents native plugin routes:
- Cursor: `/add-plugin pstack`.
- Claude Code: `/plugin marketplace add cursor/plugins`, then `/plugin install pstack@cursor-plugins`.

Those are host/plugin choices, not evidence that all source files live inside this repository. Confirm the host's actual install scope before using them, and choose one method rather than duplicate copies. The Claude adapter's `setup-pstack` writes a user-level model-rules file, so it is **not automatically authorized by a project-local setup request**. Do not run it or enable automatic updates as a hidden side effect.

In this project, Matt's workflow remains the backbone. The drone chooses relevant available P-Stack methods inside each authorized ticket. Installation is not permission to activate every mode, automation, model route or external tool.

### 4F. If installation is unavailable, label the fallback honestly

An agent can read pinned upstream files and follow permitted instructions without installing a native skill. That is a useful temporary route, but record it as **explicit source loading**, not installation.

Likewise, Assimilation's documented `python3 scripts/skills.py install --locked` is a separate option for a fresh Assimilation checkout on its qualified POSIX path. It is not the command for this new-repository lesson, and its Windows qualification work is not a prerequisite for Matt installing upstream skills.

**Done when:** the setup record states the chosen A/B scope, which skills were installed there, which were only source-loaded, and which remain unavailable. For a generic CLI P-Stack install, omit `-g` for A or add it deliberately for B; verify the complete destination/resource set before confirming.

## 5. Verify that the agent can find and use the right skill

1. Inspect the actual generated skill directories and any installer lock/provenance file. Do not assume Vercel's `skills-lock.json` is Assimilation's `sources.lock.json`; they belong to different tools.
2. Run the listing command for your chosen scope, not both as an installation requirement:

```sh
# Track A: from this repository
npx skills@latest list
# Track B: personal/global inventory
npx skills@latest list -g
```

Listing does not establish host invocation. Verify the actual selected client and source.

3. Inspect the local `setup-matt-pocock-skills/SKILL.md` and all its required templates. Upstream installation uses this original name; it does not automatically create Assimilation's `matt-` bridge names.
4. In the actual host, open the skill selector and select the installed source. For Codex CLI/IDE, the [official skills documentation](https://learn.chatgpt.com/docs/build-skills) describes `/skills` or a `$setup-matt-pocock-skills` mention. Other hosts have their own invocation syntax.
5. Ask the agent to identify the exact file/revision it loaded and summarize its setup steps before writing.
6. Verify the response against the source: tracker choice, label vocabulary when applicable, document layout, draft review and owner confirmation must be visible.
7. Check the relevant host's invocation restrictions. Copying frontmatter does not prove every host enforces it identically. Preserve explicit-only intent; if a needed sidecar or host adaptation is absent, record and resolve that limitation rather than pretending compatibility.
8. Use `git status --short` and inspect the actual diff. Confirm no unrelated files, global configuration, credentials or publication changed.

Project-local upstream skills may intentionally be checked in with the project, after license/privacy review. Do not copy Assimilation's blanket ignore for its generated `.agents/` into Chad's new repo without deciding whether these upstream project files should be versioned.

An installed name is not a successful invocation. A successful invocation is not proof that all future behavior will be correct. If a skill does not appear, use the host's documented refresh/restart behavior, verify its path and inspect the exact failure.

**Done when:** the intended source, chosen project or personal scope, invocation route, observed read/behavior and remaining limitations are recorded.

## 6. Configure this repository before planning the product

Now explicitly request the actual **setup-matt-pocock-skills** procedure. It is a prompt-driven setup interview, not a package-install command.

The agent inspects what already exists and explains:
- Where tickets will live.
- Which triage labels apply, if triage is available.
- Where the glossary and ADRs belong.
- Which existing agent-instruction file it will update.

For a first private project without a remote, **local Markdown** is a valid tracker choice. This avoids pretending a GitHub repository already exists. If Chad chooses GitHub, use his verified repository and authorized connection; do not reuse Matt's repository, account or permissions.

The real skill presents drafts, lets the owner revise them, then writes the chosen configuration. Preserve an existing project's conventions. In an Assimilation-derived project, its operator method explicitly uses `CONTEXT.md` as the glossary; do not automatically rename that convention merely because upstream defaults to `GLOSSARY.md`.

An empty project needs a decision about which agent-instruction file to create. Do not generate competing `AGENTS.md` and `CLAUDE.md` files.

Before committing starter/setup changes, inspect the exact staged paths and diff. Keep credentials, personal data, installed vendor directories and retained recovery stages out. Configure publication separately later.

**Done when:** a fresh agent can find the chosen tracker, label vocabulary, glossary/ADR locations and project authority without asking Chad to repeat them.

## 7. Use Wayfinder when you do not yet know the route

Say:

> Use Wayfinder to find the route to an agreed first release of my project. Read the real skill and this project's instructions. We are deciding what to build, not building it yet.

Do not force a large map on a tiny well-understood task. If the first useful project fits one design session, explain the simpler route. A broad reading-list idea might need a map if storage, offline use, imports and recovery span several sessions.

A map has:
- **Destination:** the point this planning effort must reach.
- **Notes:** the applicable workflow, owner and standing boundaries.
- **Decisions so far:** short links to resolved decision records.
- **Not yet specified:** in-scope questions not yet sharp enough to ticket.
- **Out of scope:** work excluded from this destination.

Create precise decision questions, not premature build tasks. “Where should the first release keep its list?” is a decision ticket. “Write storage code” is implementation work.

The frontier contains open, unblocked, unclaimed decision tickets. Claim one before working it. Charting is its own session; it does not also pretend to resolve all the questions. Work one nonresearch ticket per session; authorized research is the parallel exception.

**Done when:** the map names the destination, present questions, real dependencies and remaining fog. It is an honest map, not a completed product.

## 8. Resolve decision tickets with grill-with-docs

The agent investigates discoverable facts first. Chad answers consequential product questions.

For a grilling ticket, read **grill-with-docs**, **grilling**, **domain-modeling** and required references. Follow the operator method: one decision at a time, credible options and costs, a recommendation, then wait.

Example, not an answer supplied for Chad:

> We need to decide whether the first release works only on this computer or synchronizes between computers.
>
> A. Local only. Cost: the list does not automatically follow you to another computer.
>
> B. Synchronize between computers. Cost: accounts or another sharing mechanism, more failure cases and additional data/security decisions.
>
> ❓ Which boundary should the first release use: A or B?
>
> ➡️ Recommend A for the first learning project, because it gives us a useful behavior with fewer moving parts.
>
> Held for later: the storage format and backup/recovery experience.

Record the actual answer when it arrives. A short “A” settles only that question. It does not approve every future design or action.

As significant decisions land, create or update the relevant ADR with the decision, owner, alternatives, consequences, supporting evidence and remaining questions. Use the canonical glossary for agreed domain terms. Keep one source of truth for each decision rather than copying competing versions into every handoff.

Not every Wayfinder ticket is a grilling ticket:
- Research finds a fact with evidence.
- A prototype creates something for Chad to react to; the reaction is required.
- A prerequisite task unblocks a decision.
- Grilling resolves a human choice.

Record the resolution on its ticket, close it within authority, link it from the map and recompute the frontier. New information can expose new tickets. Do not hide newly discovered uncertainty to make the map look finished.

**Done when:** this ticket's question is actually resolved, its evidence/decision is durable and the map reflects what changed.

## 9. Land the decisions and finish the map

Matt's “closed and merged” checkpoint means the decisions are settled and the relevant decision-document changes have landed through the project's review process.

Use precise terms:
- A ticket is resolved or closed.
- A branch contains commits.
- A pull request proposes merging those commits.
- A map is a tracker artifact or its configured local equivalent.

The upstream Wayfinder research route uses throwaway research branches with no PR and no merge. Do not invent a merge requirement for those research branches.

Before specification:
1. Inspect every required decision's actual resolution.
2. Verify that any required ADR/document PRs are merged at the intended revision.
3. Recheck `Not yet specified`; no unresolved question may still block this destination.
4. Distinguish excluded/rejected/duplicate tickets from decisions actually delivered.
5. List residual risks and accepted assumptions without calling them proven facts.
6. Summarize the agreement and ask for shared-understanding confirmation.

Use the operator method's closing line:

**Frontier empty — confirm shared understanding.**

A local-only learning route can land reviewed decision commits locally, but must not call that a hosted GitHub PR merge. Decide whether the capstone includes real remote publication; it is not automatic.

**Done when:** the route to specification is clear, actual records support that conclusion, and the owner confirms shared understanding. This is not proof that software works.

## 10. Turn the resolved map into a specification

Say:

> Use to-spec to synthesize this resolved map, its decision tickets, ADRs and glossary into our specification. Read the actual sources. Do not reopen settled choices without new evidence or silently fill an unresolved choice.

The specification covers:
- The user's problem and proposed experience.
- User stories, including failures and edge cases.
- Agreed implementation contracts and boundaries.
- Testing decisions.
- Out-of-scope work.

The agent proposes the highest useful observable testing seam and confirms it with Chad. In a genuinely blank project there may be no existing seam. Say that plainly; choose an interface to observe rather than inventing prior art.

For example, testing the public command's input/output and saved state may be better than testing every private helper. That example is not the owner's agreement.

If synthesis uncovers a real blocking decision, return to the affected question. A full set of headings does not make an unresolved specification complete.

**Done when:** each important requirement traces to an accepted decision or evidence, the test seam is agreed and remaining holds are explicit.

## 11. Turn the specification into implementation tickets

Say:

> Use to-tickets on our current specification. Propose small complete behaviors with acceptance criteria and genuine blocking edges. Show me the breakdown before publishing it.

These are a second population of tickets. Wayfinder tickets asked **what should we decide?** Implementation tickets ask **what behavior should now work?**

A hypothetical reading-list breakdown, only after its contracts are agreed:
- Add one invented title and list it back.
- Mark an existing title finished and show its status.
- Export the list in the agreed format.

Each slice includes all the layers it needs and its tests. The second ticket may depend on the first's list contract. Export may or may not; inspect the actual design rather than drawing dependencies for appearance.

Review granularity, blockers and opportunities to merge/split. A parent/sub-issue relationship is not itself a blocker. The original skill does not close or modify the parent simply because children were created.

**Done when:** the owner accepts the breakdown, the tickets have verifiable behavior and their dependencies reflect necessary outcomes.

## 12. Use implement; let the drone select relevant P-Stack methods

Before starting, verify:
- The ticket is sufficiently specified.
- Required prerequisite outcomes are actually satisfied.
- Its owner and workspace are clear.
- The testing seam and synthetic-data boundary are agreed.
- The code/test work is authorized.
- Publication, deployment, sensitive-data and other separate holds remain visible.

Then say:

> Use implement for this exact ticket in this exact workspace. Read its full current body and state its title. Use TDD at our agreed seam where possible. Choose and read the appropriate P-Stack sources for this work; explain briefly why each applies. Deliver the implementation, observed verification, code-review findings and a local commit. Preserve the recorded publication and other holds.

The drone chooses appropriate tools inside the workflow, rather than replacing the workflow or invoking every skill.

| Need | Relevant source family |
|---|---|
| Writing a behavioral test | Test behavior, not implementation |
| Making a completion claim | Prove it works |
| Understanding unfamiliar code or constraints | how / why |
| A meaningful architecture choice | architect, with design-only scope during planning |
| A bug or refactor | Applicable Bug fix or Refactoring playbook |
| A broad impact assumption | blast-radius |
| Performance claims | benchmark-checklist |
| Consequential executable adversarial review | interrogate, if its required reviewers and repro execution are supported |

Read the actual source and required dependencies. Namespaced bridges are not proof of native Cursor capabilities, model families or arenas. User-invocation restrictions remain in force.

Implement's core loop is:
1. Write one meaningful behavior test.
2. Observe it fail for the missing behavior, not a broken test harness.
3. Make the smallest change that passes.
4. Repeat for the next behavior.
5. Run focused tests and typechecking regularly where applicable.
6. Run the full relevant suite at the end.
7. Use code-review, address findings and rerun affected checks.
8. Commit the reviewed work to the intended branch.

Do not claim TDD for tests written after the code. Do not claim “all tests passed” if discovery found none or a required suite was not run.

**Done when:** the actual ticket behavior is demonstrated against acceptance criteria, checks/review are recorded and unresolved limitations remain explicit.

## 13. Review, integrate and verify the delivered state

Give an independent reviewer the exact candidate, its intent/specification, acceptance criteria and reproducible evidence. A reviewer who only reads the author's summary has not independently inspected the implementation.

For a real authorized PR:
- Verify repository, base and exact head.
- Inspect the actual diff and required checks/reviews.
- Address findings without bypassing holds.
- Merge only through the permitted normal route.
- Read back the merged commit and establish the relevant post-merge outcome.
- Close the owning ticket only when its acceptance is satisfied.

For a local rehearsal, label the result local. A local merge does not establish hosted checks or remote publication.

Finish with a short evidence report:
- What now works.
- Which exact revision was checked.
- What tests/reviews actually ran.
- What did not run.
- Remaining risks or decisions.
- The next authorized action, if any.

**Done when:** the delivered state—not only a branch or status message—matches the claimed outcome.

## 14. Keep your progress and challenge the prose

Give a fresh task the canonical map/spec/ticket, ADRs, glossary, current revision, test evidence, unresolved findings and holds. Ask it to reconstruct the current stage and next allowed action without inventing missing decisions.

Then use [the adversarial-review lesson](CHAD-ADVERSARIAL-REVIEW.md) to audit the final project summary against that evidence. Code tests do not automatically validate statements such as “cross-platform,” “fully recovered,” “independently reviewed” or “finished.”

## 15. Review and update your chosen skills monthly

Matt's existing Assimilation source-review workflow is configured for the first day of each month at 09:00 UTC, with manual dispatch available. It proposes exact upstream versions in a draft PR; reviewed adoption is separate from updating installed skills. Configuration is not proof a live run succeeded.

For your own skills, preserve local edits and the previous version, inspect upstream differences and the intended scope, then check for available updates:

```sh
npx skills@latest check
```

An exit code of 1 can mean an update is available. Choose the update matching the scope you originally selected:

- **Track A — per repository:** from the correct repository, run `npx skills@latest update -p`. This updates its project installations; repeat separately for other repositories when appropriate.
- **Track B — personal/global:** run `npx skills@latest update -g`. This updates your global installations, not separately copied repository versions.

These commands are documented, not tested installations in this lesson. For a native plugin, use its own supported updater instead of the copied-skills updater. After any update, inspect changed files and required references, check collisions, list the chosen scope and verify actual host discovery and a bounded invocation. Preserve failures; restore only the intended installation from its known-good backup with authority, not by deleting unrelated work.

Use [the monthly skill-maintenance walkthrough](CHAD-SKILLS-MAINTENANCE.md#3-follow-the-existing-monthly-reviewed-update-process). It shows Matt's configured Assimilation source-review process and the separate update steps for project files, personal/global skills and native plugins. Preserve edited copies, review exact changes, and recheck the real host; installing skills does not create a monthly schedule.

**Done when:** the setup record says which update process owns each installation, where the previous version can be recovered, and which checks must run after a deliberate update.

## Completion checklist

The learner can explain:
- Which folder is the project, and what Git changed.
- Whether skills were installed, explicitly loaded or unavailable.
- Which host/revision actually used them.
- Why Wayfinder decisions are not implementation tickets.
- How accepted decisions became a spec and then verifiable slices.
- What implement and selected P-Stack methods contributed.
- What the evidence proves and does not prove.
- Which work remains held or unfinished.

**Verification status:** the upstream project-local and personal/global installation routes are documented and their relevant CLI/source behavior was inspected. Neither has been executed on Chad's host as part of this lesson. The guided installation and real-host acceptance checks must run before claiming his setup is complete; there is no need to wait for Assimilation's separate native-Windows installer.

## Sources

Source baseline: [Assimilation at 5acfeff5](https://github.com/mshamblin5150-code/assimilation/tree/5acfeff5471c257488c1f445df0761083785e56d).

- [Installer and real CLI/root behavior](https://github.com/mshamblin5150-code/assimilation/blob/5acfeff5471c257488c1f445df0761083785e56d/scripts/skills.py).
- [Source scopes, pins and documented platform evidence](https://github.com/mshamblin5150-code/assimilation/blob/5acfeff5471c257488c1f445df0761083785e56d/docs/SOURCES.md).
- [Safety, invocation and recovery boundaries](https://github.com/mshamblin5150-code/assimilation/blob/5acfeff5471c257488c1f445df0761083785e56d/docs/SAFETY.md).
- [Project configuration skill](https://github.com/mshamblin5150-code/assimilation/blob/5acfeff5471c257488c1f445df0761083785e56d/upstream/matt-pocock/skills/engineering/setup-matt-pocock-skills/SKILL.md).
- [Wayfinder](https://github.com/mshamblin5150-code/assimilation/blob/5acfeff5471c257488c1f445df0761083785e56d/upstream/matt-pocock/skills/engineering/wayfinder/SKILL.md), [operator method](https://github.com/mshamblin5150-code/assimilation/blob/5acfeff5471c257488c1f445df0761083785e56d/docs/OPERATOR_METHOD.md), [planning lesson](https://github.com/mshamblin5150-code/assimilation/blob/5acfeff5471c257488c1f445df0761083785e56d/docs/CHAD-PLANNING.md).
- [Implement](https://github.com/mshamblin5150-code/assimilation/blob/5acfeff5471c257488c1f445df0761083785e56d/upstream/matt-pocock/skills/engineering/implement/SKILL.md), [existing implementation lesson](https://github.com/mshamblin5150-code/assimilation/blob/5acfeff5471c257488c1f445df0761083785e56d/docs/CHAD-IMPLEMENTATION.md), [issue-to-main lesson](https://github.com/mshamblin5150-code/assimilation/blob/5acfeff5471c257488c1f445df0761083785e56d/docs/CHAD-ISSUE-TO-MAIN.md).

These were read as source, not invoked operationally to install or update skills during lesson preparation. The source and verification notes below record inspected revisions and unrun capabilities.



## Source and verification record

Read [the source and verification notes](CHAD-LESSON-SOURCES.md) for the inspected upstream pins and the distinction between source inspection, offline Git preflight, documentation checks and unrun host installation.
