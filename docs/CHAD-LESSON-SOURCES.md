# Blank-project and adversarial-review lesson sources

These notes distinguish inspected instructions from observed execution. They support [the blank-project walkthrough](CHAD-BLANK-PROJECT.md), [scope and monthly maintenance](CHAD-SKILLS-MAINTENANCE.md), and [adversarial prose review](CHAD-ADVERSARIAL-REVIEW.md).

## Inspected sources

| Source | Inspected revision | What it supports |
|---|---|---|
| [Assimilation](https://github.com/mshamblin5150-code/assimilation/tree/5acfeff5471c257488c1f445df0761083785e56d) | `5acfeff5471c257488c1f445df0761083785e56d` | Operator method, connected workflow, prior lessons, installer boundaries and existing monthly source-review process |
| [Matt Pocock](https://github.com/mattpocock/skills/tree/59db609eb1e18aaf59b63284d0e52255aff0c63c) | `59db609eb1e18aaf59b63284d0e52255aff0c63c` | Upstream README installation routes and actual engineering workflows |
| [P-Stack](https://github.com/cursor/plugins/tree/c742dd61706fbacc1b95f1a20b7b988cf096ce6c/pstack) | `c742dd61706fbacc1b95f1a20b7b988cf096ce6c` | Native plugin routes, full resource boundary, selected principles and interrogate |
| [Vercel skills CLI](https://github.com/vercel-labs/skills/tree/92a9a34ac3bf88e695e468b90c7bf32f163d32c8) | `92a9a34ac3bf88e695e468b90c7bf32f163d32c8` | Package version 1.7.4, Node >=22.20.0, source/agent/scope/copy/update options and destination behavior |
| [Clinical Skills public study](https://github.com/mshamblin5150-code/clinical-skills/tree/6fc9d32c32b246ef3dc022f3d7a8e677ad2f2e66) | `6fc9d32c32b246ef3dc022f3d7a8e677ad2f2e66` | Standing review rules, sourcing guidance, ADRs 0218 and 0262 |

The installation and maintenance pages link directly to the relevant upstream instructions. Host-specific behavior was checked against official [Codex skills](https://learn.chatgpt.com/docs/build-skills), [Codex CLI](https://learn.chatgpt.com/docs/cli/reference), [Claude Code skills](https://code.claude.com/docs/en/skills) and [Claude Code plugins](https://code.claude.com/docs/en/discover-plugins) documentation on 2026-10-31. Recheck current versions and host behavior before a later session.

The `@latest` examples and upstream `main` source URLs are live documented routes, not immutable installation receipts. A source pin in this table identifies what was inspected; it does not pin a command that still says `@latest` or prove an npm package was executed.

## What was observed before publication

- A bounded offline Linux preflight used existing Git 2.52.0, Node 24.22.1 and npm/npx 11.9.0. Twelve recorded commands checked versions, isolated npm-cache location, a blank-folder guard, Git initialization on `main`, exact root, clean unborn branch, no remote and nested-folder detection.
- That preflight created only its own disposable project and isolated home/cache/config directories. It did not run the skills CLI, download packages, install skills, invoke an agent or exercise a Windows host.
- The lesson's document/link checks concern published reader paths and static fixture structure. They do not prove an agent discovers or follows installed skills, that the learner succeeds, or that a generic CLI preserves all outside-folder P-Stack resources.

Exact final-candidate regression runs and independent Spec/Standards review are recorded in the delivering PR. Those reviews are separate from the synthetic teaching exercise. No test total in a training fixture is a real project test receipt.

## What remains unverified

No project-local or personal/global upstream installation, native plugin installation, monthly host update, actual skill discovery or bounded host invocation was performed for these lessons. The configured Assimilation monthly schedule is not proof of a successful live run. Linux Git preflight and Windows refusal-contract CI do not qualify native-Windows upstream installation or Assimilation's separate Windows installer.

The full P-Stack collection may require sibling resources, agents, scripts and host features beyond one copied skill directory. The lesson starts only with inspected self-contained principles or an actually supported native plugin; it does not claim a full Codex P-Stack adapter exists. Preserved archives stay pinned until deliberately replaced and verified.

The Clinical Skills adaptation uses public rules and invented training text. It imports no patient data, private corpus, clinical output or clinical workflow and makes no professional-validation claim.
