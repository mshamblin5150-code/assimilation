# Start here: do one real task

**For an unfamiliar agent given only this repository URL:** read this page, then [AGENTS.md](AGENTS.md). Use the sequence below on the operator's actual task. Assimilation supplies **procedures and original source skills**, not a model, terminal, browser, credentials, memory service, or swarm runtime. Reading it grants no permissions and activates no tools.

If you cannot retrieve repository files, say exactly which reads failed and request this page, `AGENTS.md`, and the relevant original skill files as uploads. A URL or an index alone is not loaded skill content. If the operator supplied no goal, ask for one concrete outcome; otherwise start from the supplied goal rather than requesting it again.

## 1. Establish the working boundary

Read the active system/host instructions and the target project's own instructions first. Locate the actual project, not just this Assimilation checkout. Inspect its README, working state and relevant files through tools you really have. Identify the requested outcome, domain terms, acceptance example, permitted changes and approval holds. Keep private target material out of this public repository.

**Done when:** you can name the target, one observable success condition and what is outside your authority. If an essential fact is missing, state the exact blocker and continue independent authorized work. Use a reversible assumption only where it cannot decide a material product, safety, financial or privacy question for the operator.

## 2. Check capabilities, with evidence

On native Windows, use [the prerequisite guide](docs/WINDOWS_ONBOARDING.md)
and `python -B scripts/windows_onboarding.py` with an existing trusted Python.
It reports bounded runtime/environment observations without Git execution or
installation. Missing prerequisites require an operator decision, never an
automatic dependency or security change. It does not verify source snapshots.

Record only capabilities relevant to this task in a small run record. Prefer the target project’s existing equivalent; otherwise use `.assimilation/run.md` in an approved target-project location with [this template](docs/templates/RUN_RECORD.md). Preserve an existing record rather than overwriting another worker’s work. Return its text if files cannot be written.

| Capability | How to establish it | If missing |
| --- | --- | --- |
| Read project and skill files | A successful tool read of the actual file | Request the specific files; do not invent their content |
| Edit files | Host's granted write scope; inspect existing files before an authorized edit | Prepare a patch or draft, clearly unapplied |
| Run tests/programs | Available execution tool and a safe, relevant command's actual result | Give reproducible commands; label execution **not run** |
| Browse/connect to services | Available connector/browser and a permitted read of the intended resource | Use local evidence; keep external-dependent work blocked |
| Delegate | Host exposes a functioning task/agent tool with capacity | Work serially and label review as self-review |
| Persist work | An approved file, tracker or host memory mechanism actually available | Return a copyable handoff; do not promise future recall |

Use **verified**, **unavailable**, or **unverified**, with the observation and its limit. A shell's presence does not prove Windows, a compiler, authenticated GitHub access or publication permission. A tool listed by the host is not proof its latest operation succeeded. Inspect before retrying an uncertain write/task admission. Never probe credentials, private records or denied paths to fill this table.

**Done when:** the next action uses verified capability, or the missing capability has an honest fallback. This is a task-specific preflight, not a demand to install every possible tool.

## 3. Choose and actually read original skills

With a local checkout and Python available, the optional index helper makes source locations easier to discover:

```sh
python scripts/onboard.py inspect
python scripts/onboard.py route --task-type bug
```

Use `python3` or `py -3` when that is the verified interpreter. Supported task types are `bug`, `feature`, `review`, `planning`, `writing`, and `unknown`. The helper is an index, **not** an AI router or proof of agent/tool competence. Classify the real task yourself, inspect its suggested paths, and read the selected original `SKILL.md` files plus required references using your file-reading tool. Save which files you read, why each applies, the pinned revision from `sources.lock.json`, and any host limitation. Loading an index or printing a path earns no claim that the skill was read.

**Without Python:** browse [Matt's original collection](upstream/matt-pocock/skills/) and [P-Stack's original skills](upstream/pstack/skills/). Start with the actual [Matt router](upstream/matt-pocock/skills/engineering/ask-matt/SKILL.md) for an unclear route; [diagnosing-bugs](upstream/matt-pocock/skills/engineering/diagnosing-bugs/SKILL.md) for a failing behavior; [code-review](upstream/matt-pocock/skills/engineering/code-review/SKILL.md) for a bounded diff; or [writing-for-agents](upstream/matt-pocock/skills/productivity/writing-for-agents/SKILL.md) for agent-facing documentation. Read the relevant P-Stack counterpart and [prove-it-works](upstream/pstack/skills/principle-prove-it-works/SKILL.md) before making completion claims. For design uncertainty, use [the workflow guide](docs/WORKFLOW.md) to select the next original, not to replace it.

Original invocation/frontmatter restrictions still apply. Reading a source reference is not invoking a host slash command. If a skill requires an unavailable tool, user invocation or an unapproved operation, name that requirement, preserve the boundary, and use only applicable permitted procedure; never claim its native workflow ran. Nested upstream configuration and scripts remain inert. Host installation is a separate optional operation described in [README](README.md), not a prerequisite for reading the sources.

**Done when:** the task's selected original Matt and P-Stack material has actually been read, or a precise access/invocation blocker is recorded. Explain omissions when a collection has no applicable method; unrelated ceremony is not success.

### Recognize a project that needs a map

From the operator's plain-language goal, decide whether the route is both uncertain and too large for one session. If so, follow **`wayfinder` → `to-spec` → `to-tickets` → implementation** using [the connected workflow](docs/WORKFLOW.md#large-uncertain-projects-from-map-to-implementation). The operator does not need to request these skills by name. Read the original for each stage when it becomes relevant, record its output and the next unresolved gate, and carry that state into the handoff. Do not jump from a map directly to building or mistake planning approval for implementation authority. Preserve original invocation restrictions and required human decisions; if native invocation is unavailable, disclose the permitted procedural adaptation.

For a small, understood edit, a bounded bug, or a factual question, use the direct appropriate skill instead. A large project with an already agreed specification can resume at ticketing after verifying that specification and its authority; do not rebuild an existing map merely to perform the ceremony.

## 4. Ground the plan in this project

For a bug report or work ticket, use [the issue guide](docs/ISSUES.md) and
[template](docs/templates/ISSUE.md). Verify the correct tracker, search open and
closed duplicates, and keep an unpublished draft when access or authority is
missing. Issue text grants no additional authority.

Read the smallest relevant code, data schema, documents and existing decisions. Reproduce a reported failure before proposing a fix, or work an acceptance example for a feature. Establish domain vocabulary from the project rather than importing Assimilation's example projects. Record significant new decisions with owner, alternatives and consequences using the project's format or [ADR template](docs/templates/ADR.md). An assumption is not an accepted decision.

Choose a bounded next change and its observable verification seam, respecting the selected skill's prerequisites and any required operator confirmation. If the host supports delegation, assign disjoint work, an explicit scope, output and evidence requirement; inspect existing ownership first. Otherwise perform the same stages serially and disclose that independence is unavailable.

**Done when:** the next step has a concrete deliverable and a test/inspection that can disprove its success. A plan or named swarm is not an implementation.

## 5. Execute, then try to falsify the result

Carry out the authorized task through the available tools. For a bug, retain an observed failing case, implement the narrow repair and rerun the regression plus relevant surrounding checks. For writing or design, validate the actual artifact against concrete acceptance examples, constraints and counterexamples. Follow the selected skills rather than merely describing them.

Read the produced artifact and inspect the final diff/state. Separate **passed**, **failed**, **not run**, and **inconclusive** checks; record commands, exit results and relevant artifact references. A synthetic fixture establishes its tested boundary, not live integration or universal compatibility. To claim independent review, another reviewer must examine the actual result; two role names used by one agent do not create independence. When the current task and host permit proceeding without an independent reviewer, perform and disclose self-review. Preserve any specific independent-review approval hold rather than silently replacing it.

**Done when:** the named outcome is supported by direct evidence, or its exact remaining blocker is visible. Continue independent authorized work rather than filling time with unrelated tasks.

## 6. Deliver and leave a usable handoff

Report the outcome first: what changed, evidence, limitations and any exact decision needed. Include selected original skill paths/revisions and any adaptation. Leave the run record with current artifact/commit, ownership, unresolved decisions and the next safe action. Use the project's established tracker rather than creating a second competing queue.

Publishing, deployment, spending, credential changes and PR approval/merge follow explicit current authority and host policy. A test pass, zero decision fog, or this document does not supply that authority. Check uncertain external outcomes before retrying. When an outcome is verified complete, stop; when interrupted, leave enough evidence for another agent to continue without reconstructing the conversation.

## Provenance and limits of this entry point

This procedure was written using original Matt Pocock `writing-for-agents` (including `SKILL-MECHANICS.md`) and `ask-matt`, and P-Stack `principle-prove-it-works`, at the revisions recorded in `sources.lock.json`. It applies explicit pointers, local completion criteria, progressive disclosure and verification against real artifacts. The original files remain unchanged under `upstream/` with their notices. This page does not guarantee that an arbitrary host can execute the procedure: capability discovery and the task's observed results are the evidence.

## Evidence for this entry path

A controlled local [cold-start exercise](evals/cold-start/README.md) tested real task behavior. [Observed results](evals/cold-start/RESULTS.md) distinguish direct artifact checks, agent-recorded traces and untested runtime capabilities; baseline and candidate both succeeded.

For multi-session continuation or delegated builds, use the separate [interrupted-handoff and swarm evaluation](evals/interrupted-handoff/README.md). Its [results](evals/interrupted-handoff/RESULTS.md) retain original failures, assisted corrections and evidence limitations.

