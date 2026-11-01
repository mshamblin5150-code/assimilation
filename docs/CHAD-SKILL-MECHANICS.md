# Skill mechanics: several independent choices

Use this reference before [the advanced Clinical Skills trace](CHAD-CLINICAL-SKILLS-STUDY.md). “Kind of skill” is useful shorthand, but there is no universal, exhaustive list shared by every agent host. Classify each real skill along the following axes. One skill can occupy a position on every axis.

| Axis | Choices to inspect | Concrete example |
| --- | --- | --- |
| Discovery and scope | Project, personal, managed/system, or plugin-provided; registered versus merely browsable source | Assimilation keeps originals under upstream; its optional installer creates discoverable bridges |
| Invocation | User-selected, model-selected, or both, subject to host policy | The organizer and public setup skill declare explicit-only intent; the Assimilation work router has a matching description |
| Content | Task instructions, reference guidance, or a router to other material; any can use supporting resources | Organizer steps link a tutorial; Python supplies the deterministic move operation |
| Execution context | Current conversation or a supported separate agent context | A request to delegate is only actionable when the host actually provides delegation |
| Lifecycle | Authored, discovered, selected, loaded, executed, verified, updated, disabled/removed | A downloaded folder has not yet demonstrated that a selector can find it or that its tests pass |

These are descriptions of independent properties, not five plugin types or five magic file extensions. A model-selected skill may provide reference knowledge or perform a multi-step task. A user-selected skill may still need explicit approval immediately before a file move. Discovery and authorization are separate.

## Verified host mechanics, as of 2026-10-31

**OpenAI:** Explicit invocation uses @ selection in ChatGPT or /skills and $ mentions in Codex CLI/IDE; implicit selection matches the description. Codex local discovery includes repository .agents/skills and user/admin/system locations. Optional agents/openai.yaml can set policy.allow_implicit_invocation to false while retaining explicit invocation. Plugins distribute reusable skills and optional connectors. These are host mechanisms, not guarantees for every application that reads Markdown. See [official OpenAI documentation](https://learn.chatgpt.com/docs/build-skills). The older developers.openai.com/codex/skills URL redirected there during verification.

A Codex example, stored beside SKILL.md rather than inside its Markdown body:

```yaml
# agents/openai.yaml
policy:
  allow_implicit_invocation: false
```

**Claude Code:** Default invocation allows both user and model. disable-model-invocation: true makes a skill user-invoked; user-invocable: false makes it model-only. Project discovery uses .claude/skills; personal discovery uses ~/.claude/skills. The body loads on invocation and persists subject to context management. Host extensions can interpret context: fork, model, hooks and allowed-tools. In particular, allowed-tools can pre-approve listed tools for the invoking turn; it is not a restrictive tool list. See [official Claude Code documentation](https://code.claude.com/docs/en/skills).

The public Clinical Skills setup frontmatter demonstrates the first restriction:

```yaml
---
name: setup-clinical-skills
description: Configure this repo for one clinician's account and program.
disable-model-invocation: true
---
```

This is an abbreviated illustration; the [verified canonical file](https://github.com/mshamblin5150-code/clinical-skills/blob/6fc9d32c32b246ef3dc022f3d7a8e677ad2f2e66/skills/setup-clinical-skills/SKILL.md) contains the actual description and instructions. Do not invoke it for the reading lesson.

Model-selection illustration: a hypothetical reading-list-reference skill can describe “Explain the reading-list folder schema when editing its metadata.” That description offers a matching condition; it does not promise the model will select correctly. Test both a matching prompt and a nearby unrelated prompt. To make a Claude-only model-only reference, user-invocable: false is the documented field; do not copy it into another host and assume identical behavior.

## Instructions, references, scripts and assets

A minimal skill has identifying frontmatter and a Markdown body. The body tells the agent the outcome and completion criteria. References carry conditional detail; scripts perform repeatable operations; assets are material used in output. These roles concern content, not invocation.

For example, this candidate's SKILL.md says when to preview, when to wait for approval and when to recover. The tutorial explains the lessons. organizer.py computes fingerprints and uses Windows rename. test_organizer.py checks preserved files. Merely naming a script does not execute it. Resources need working pointers, and a script needs a runtime and tools.

Writing for Agents informed this structure: keep ordered steps and clear done conditions in the entry point; disclose optional PDF details through a pointer; keep one authoritative definition of each rule. Its invocation guidance is a source-authoring convention; host configuration must express the same intent.

## Real workflow evidence in this environment

Read [scripts/skills.py](../scripts/skills.py), functions bridge_policy and the bridge generation in _install. They inspect upstream frontmatter and the OpenAI sidecar, retain restrictions and refuse unsupported or conflicting policy. Restricted bridges receive both the frontmatter declaration and the OpenAI sidecar. Tests in [tests/test_skills.py](../tests/test_skills.py) include test_bridge_preserves_invocation_restrictions_for_both_hosts and test_sidecar_only_and_frontmatter_only_restrictions_cross_host_boundary. These were inspected, not executed during this lesson; no installer ran.

The supplied environment exposes personal filesystem skills and plugin skill packages through an actual skill reader. Writing for Agents and the P-Stack router were read that way. That observed capability does not prove Chad has the same plugins, paths, runtime, models or permissions.

The public Clinical Skills README describes its own canonical skills and Claude mirror, while source-reading agents can be given the actual SKILL.md. A README pointer is useful instruction, but differs from host-native discovery. The advanced trace shows this distinction without installing the mirror.

## What a skill file does not establish

A bare SKILL.md does not create an operating-system hook, background schedule, API permission, native agent type, connector, or model router. Text such as “run hourly” or “delegate to reviewer” is an instruction, not evidence those facilities exist. Host-specific parsed configuration may explicitly register hooks, pre-approve tools or choose an execution context/model, as Claude Code documents above. That is a host feature with its own scope and controls, not a portable property or blanket authorization.

Assimilation's public-source snapshots are deliberately inert reference material. Its installer refuses policy it cannot safely translate rather than pretending it is equivalent. A P-Stack source's role/model language must be adapted to actual supported tools; it does not install an agent or change a model by being read. This lesson configures none of those facilities.

## A small lifecycle exercise

1. Author an invented read-only reading-list preview skill in a separate practice copy, with a precise description and a linked example.
2. Inspect the target host's supported discovery location and policy; make it discoverable only within authorized setup scope.
3. Explicitly select it and confirm which file was loaded. If model-selection is enabled, try a matching request and an unrelated request; record misses and false triggers.
4. Verify actual output against the example, including uncertainty and a no-mutation check.
5. Edit one instruction, verify the host loads the intended revision, and retest. Disable or remove it through that host's documented mechanism when finished; confirm it is no longer offered. Do not assume an already loaded conversation forgets it.

This is a proposed exercise, not setup performed in this session. Done when Chad can name a skill's scope, invocation policy, resources, execution context and lifecycle evidence independently, and can distinguish instructions from capabilities and permissions.

## Choose your own name

A friendly label such as "My Folder Helper" can have spaces. The portable skill identifier `my-folder-helper` is different. The [Agent Skills specification](https://agentskills.io/specification#name-field) requires a 1-64 character lowercase alphanumeric/hyphen identifier matching its parent directory, with no leading/trailing or consecutive hyphens. Use the simple ASCII subset shown here. This is a portable convention, not a claim that every host accepts exactly the same syntax.

Claude Code derives invocation names from its directory/frontmatter rules and has host-specific reserved namespaces and managed storage. Avoid repurposing its `synced` directory or using the reserved `anthropic-skills` namespace; plugins add namespaces. Verify [current host naming rules](https://code.claude.com/docs/en/skills#how-a-skill-gets-its-command-name), avoid collisions and inspect the actual selector. OpenAI's [official skill documentation](https://learn.chatgpt.com/docs/build-skills) separates required frontmatter `name` from optional `interface.display_name` in `agents/openai.yaml`. A display label does not rename the identifier or create a command.

For a practice-copy rename, update these together:

| Item | Sample placeholder | Learner example |
| --- | --- | --- |
| Source folder | skills/assimilation-practice-organizer/ | skills/my-folder-helper/ |
| SKILL.md frontmatter | name: assimilation-practice-organizer | name: my-folder-helper |
| Human heading | Practice organizer | My Folder Helper |
| Optional OpenAI UI label | Unset | interface.display_name: My Folder Helper |
| References and supported explicit invocation | Old name/path | New name/path; Codex $my-folder-helper or Claude /my-folder-helper after verified discovery |

Keep `policy.allow_implicit_invocation: false` in the OpenAI sidecar and `disable-model-invocation: true` in the supplied source. Do not overwrite an existing same-name skill. Keep directory depth unchanged for this simple rename, then check all relative pointers and search the practice copy for the old name. Preserve quoted upstream skill names and historical evidence; rename only references to this sample. The organizer Python module, test imports, file categories, preview hashes and approval protocol do not depend on the skill name.

This candidate retains its sample source path for review. The substitution example was checked with the learner identifier above, without installing or renaming a live skill. Host discovery/invocation after a learner's rename still needs its own verification.
