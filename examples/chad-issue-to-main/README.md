# Local issue-to-main rehearsal

Use with [Chad's workflow lesson](../../docs/CHAD-ISSUE-TO-MAIN.md). This worksheet
changes only an owner-selected disposable repository and synthetic test files.
It neither publishes a GitHub issue/PR nor modifies the original repository's
main branch. Keep public publication and any existing teardown holds intact.

## Before running anything

Use already available trusted Git and Python 3.12+, a reviewed local Assimilation
checkout, and an empty approved local parent directory. No installation, real
personal files, network share or synchronized folder is needed. Review applicable
instructions and any executable hooks/filters before checking out/running a repo.
If the tools are unavailable, rehearse the prompts and mark commands **not run**.

Choose these absolute paths; every destination must be new:

- `SOURCE`: the authorized stable local source checkout.
- `LAB`: a disposable control clone, not SOURCE.
- `WT`: a sibling linked worktree, not inside LAB or SOURCE.
- `EVIDENCE`: a separate private folder for the local issue, brief, logs and PR
  draft; keep it outside WT so removing WT cannot destroy the only evidence.

Record the verified full starting commit as `BASE`. A branch name can move.
If learning against current main, first verify the intended remote/default branch
and fetch only with authority; record its observed commit, then use that exact
commit below. A local dirty file is not included in a clone's committed snapshot.
Coordinate a stable source while cloning.

The following commands are **templates**, not a paste-and-run script. Replace
every uppercase placeholder with the selected value, run one command at a time,
inspect its result and stop on failure. Quoted paths work with ordinary Git
commands in PowerShell or a POSIX shell; `BASE` is a full commit, not literal text.

```text
git clone --no-hardlinks --no-checkout "SOURCE" "LAB"
git -C "LAB" rev-parse --show-toplevel
git -C "LAB" remote -v
git -C "LAB" remote remove origin
git -C "LAB" switch --no-track -c rehearsal-main BASE
git -C "LAB" status --short --untracked-files=all
git -C "LAB" worktree list --porcelain
git -C "LAB" worktree add --no-track -b rehearsal-rst "WT" BASE
git -C "WT" rev-parse --show-toplevel
git -C "WT" branch --show-current
git -C "WT" rev-parse HEAD
git -C "WT" status --short --untracked-files=all
```

`--no-hardlinks` avoids local object hardlinks. Removing `origin` affects only
this new clone's remote configuration; it does not change SOURCE or make a
network request. These precautions are **not a security sandbox**. The control
branch is deliberately `rehearsal-main`, not the real main. Stop if the names or
paths exist; choose new ones instead of force-overwriting.
[Git clone](https://git-scm.com/docs/git-clone) and
[Git worktree](https://git-scm.com/docs/git-worktree) document the behavior.

## Make and triage one local issue

For this rehearsal, explicitly tell the agent the tracker is `EVIDENCE/issue.md`,
with category names `bug` / `enhancement` and states `needs-triage`, `needs-info`,
`ready-for-agent`, `ready-for-human`, `wontfix`. This is a supplied local convention,
not proof that the live repository's tracker or labels are configured.

Create the local request: “I keep reStructuredText notes. Can the practice
organizer recognize `.rst` files as text while leaving unknown files alone?”
Record the owner and local-only scope. Invoke the actual triage source against
that file, with the disclaimer required for its posts. Search existing source
and relevant issue history where accessible, and local rejection records. Record
the search limits: an offline rehearsal cannot establish that a live tracker has
no duplicates. Don't open a real issue for this exercise.

Follow lesson steps 1–3: recommendation and owner direction, observed baseline,
one-question grilling, preserved ADR 0008 and confirmed brief. The
[filled brief](AGENT-BRIEF.md) is a comparison, not a pretend record of your answer.
Confirm the public `preview(folder)` test seam and exact implementation scope.

## Implement in WT, with real red and green

Point the agent and terminal at WT and explicitly request the actual implement
skill. Permit the organizer code, its behavior tests, and matching organizer
instruction wording only. Keep the local tracker/evidence outside WT. The source
checkout, other worktrees, upstream snapshots and installer are not edit targets.

Use real temporary invented `.rst`, `.RST` and unknown `.bin` files. In the
existing `OrganizerTests` class, add one behavior test named
`test_preview_classifies_rst_without_changing_inputs` through `preview(folder)` that asserts the brief's literal
destinations and original bytes/entries. Derive expected values from the brief,
not the implementation's own category table. Run that test before code changes.
Inspect that exact test body, then move the terminal explicitly to
**WT/examples/chad-organizer** and run its fully qualified name:

```text
python -B -m unittest test_organizer.OrganizerTests.test_preview_classifies_rst_without_changing_inputs -v
```

Verify exactly the intended test ran and failed because `.rst` is Keep. If zero
tests run, discovery is broken; if the expected feature already passes, go back
to triage. Save real output and exit status in EVIDENCE. Do not reconstruct a red
log after implementing.

Make the smallest behavior change and rerun the new test. From that same directory,
run the existing pure-preview regression by its exact name; verify **one** test ran:

```text
python -B -m unittest test_organizer.OrganizerTests.test_preview_is_exact_and_read_only -v
```

Inspect named test bodies before running them. Substring filters are not an
authority boundary: `rst` also matches `first`, and `preview` matches tests that
invoke apply. Keep this rehearsal to the two exact pure-preview test names above.
Return the terminal to **WT's repository root** before the root-suite command below.
Ensure instructions
match code and observe the actual generated plan as well. Preview
does read bytes for fingerprints; extension-only means no content parsing, not
no reads. New classification can affect a later approved apply, so preserve
approval, fresh-plan and Windows move/undo limits. Run **no apply/undo** in this lab.

Read the project's workflows to select the available regression boundary. The
Linux root suite is `python -B -m unittest discover -s tests -v`; the existing
full organizer suite runs on Windows and includes synthetic moves/undo. Those
Windows operations are outside this preview-only rehearsal. Report that gap,
not an invented full-platform pass. A real candidate needs its actual applicable
checks/permissions before merge. No configured typechecker means report “none
configured,” not “typechecking passed.”

Inspect/stage only the intended files and make a local review checkpoint. Use the
actual code-review source with BASE and the local brief, including independent
Standards and Spec review when available. Resolve findings, rerun checks and
commit repairs. Record the final candidate SHA. The permitted new test creates
and removes its own synthetic temporary fixtures; no user data is involved.

## Draft the PR, then rehearse integration locally

Write `EVIDENCE/pr-draft.md`: the requested behavior, before/after evidence,
exact candidate, review, risk and unavailable checks. Label it **unpublished**.
Do not invent a GitHub PR number, hosted check run, approval or merged state.

After the owner accepts this bounded local rehearsal, verify LAB is still on
`rehearsal-main`, unchanged at BASE, and clean. Confirm no other owner/process
uses it. Then:

```text
git -C "LAB" branch --show-current
git -C "LAB" rev-parse HEAD
git -C "LAB" status --short --untracked-files=all --ignored
git -C "LAB" merge --ff-only rehearsal-rst
git -C "LAB" rev-parse HEAD
git -C "LAB" merge-base --is-ancestor rehearsal-rst rehearsal-main
```

Require the final control HEAD to equal the reviewed candidate and ancestry check
to return exit 0. Rerun the focused preview test from LAB and inspect the actual
result. If `--ff-only` refuses, stop and reconcile; don't switch to a forceful
command. This integrates only the disposable local branch. It is **not** a test
of GitHub PR permissions, required reviews, branch protection, hosted CI or the
real main branch. Use lesson step 7 only for separately authorized live work.

## Cleanup gate

Keep the rehearsal by default. Only with authority to remove that exact owned
worktree, and after all of these facts are established:

1. No agent, shell, test, server or watcher is using WT; uncertain operations are
   reconciled. Git does not establish process ownership for you.
2. The brief, decisions, logs, review and candidate identity survive in EVIDENCE;
   no only copy remains inside WT. No unrelated personal files are present.
3. Inspect `git -C "WT" status --short --untracked-files=all --ignored`. Review
   staged, modified, untracked **and ignored** files. An ordinary clean status
   can hide valuable ignored outputs. Preserve them or stop; don't sweep-delete.
4. Verify the exact accepted integration and branch tip. Check `git -C "LAB"
   branch -vv` and `git -C "LAB" merge-base --is-ancestor rehearsal-rst rehearsal-main`.
   For this fast-forward lab, require exit 0 and the expected reviewed HEAD.

Then, from outside WT, remove only that worktree and optionally its verified
merged local branch:

```text
git -C "LAB" worktree remove "WT"
git -C "LAB" branch -d rehearsal-rst
git -C "LAB" worktree list --porcelain
```

Recheck the worktree list and preserved evidence. `worktree remove` and branch
deletion are different operations. `branch -d` checks its configured upstream,
or HEAD when none is configured, which is **not necessarily main**. We used
`--no-track` and explicitly checked the intended target first. A real squash
merge can leave the old tip non-ancestral: retain that branch and verify the
accepted content/merge receipt; do not use `-D` to silence the warning.

On any refusal or unexpected file, keep the worktree and report what needs
reconciliation. Never substitute forced removal, blanket `git clean`, hard reset
or deletion of the whole clone. This worksheet does not require deleting LAB,
EVIDENCE or a remote branch.
[Git status](https://git-scm.com/docs/git-status),
[worktree removal](https://git-scm.com/docs/git-worktree),
[branch deletion](https://git-scm.com/docs/git-branch) and
[ancestry checks](https://git-scm.com/docs/git-merge-base) explain the commands.

**Pass:** you can trace the local issue → confirmed brief → observed red/green →
reviewed commit → verified local integration, identify every untested/live gate,
and either retain the worktree or clean up only with the stated evidence and
authority. The original source repository remains unchanged.
