# Chad's next lesson: keep the work, refresh the conversation

**The goal:** stop at a clear checkpoint, write a useful handoff, and have a fresh
task continue from verified facts—not from a guess about what the old chat meant.
Start after the [practice-folder lesson](CHAD-ORGANIZER.md). You need no swarm,
paid plan, new package, or real personal files for this exercise.

Think of the conversation as a workbench and the project files as the work itself.
Clearing the workbench does not finish, undo, or cancel the work.

## 1. What fits on the workbench?

A **context window** is the limited amount of information a model can use in one
request. Your instructions, conversation, supplied file excerpts and tool results
consume space; generated output and, depending on the model, reasoning also count.
A long chat displayed on screen is not proof that every earlier detail is in the
current input. Limits and accounting depend on the model and host.
See [OpenAI's context-window explanation](https://developers.openai.com/api/docs/guides/conversation-state#managing-the-context-window).

**Compaction** reduces the context carried forward so work can continue. Depending
on the product, that can mean a summary or other compressed state; the Responses
API, for example, uses opaque compaction items, not a hand-editable handoff file.
See [OpenAI's compaction guide](https://developers.openai.com/api/docs/guides/compaction).
Useful details can be omitted or represented incompletely in a summary. That is a
reason to preserve decisions and evidence—not proof that compaction always makes
an agent worse. There is no universal percentage or number of messages at which
every model becomes unreliable.

These are different actions:

| Action | What it does for this lesson |
| --- | --- |
| Compact the current chat | Reduce carried conversation state; keep using that chat |
| Write a handoff | Create a readable checkpoint pointing to authoritative artifacts |
| Start a fresh task | Begin a new conversation and deliberately reload relevant context |
| Resume or fork a chat | Continue or copy its history; not the clean-context exercise here |

Some Codex surfaces provide `/compact` and `/new`; check the commands actually
available in your host. [OpenAI's command reference](https://learn.chatgpt.com/docs/developer-commands?surface=cli)
describes their current behavior. Neither command installs Assimilation's skills.
This lesson adds no automatic compaction, handoff, or turn-stop hook.

**Checkpoint:** explain the difference between changing the conversation and
changing the files. A new chat does not erase a running process or grant permission.

## 2. Notice missing context without guessing the cause

Pause to check the record if the agent:

- asks a settled question again or contradicts a recorded decision;
- forgets an approval hold, changes scope, or names the wrong branch;
- reports a test as passed without locating its actual result;
- proposes repeating an action whose outcome is still unknown;
- keeps restarting the same investigation without using its evidence.

These are warning signs, not a diagnosis of compaction. Stale files, ambiguous
instructions or an ordinary mistake can produce the same symptoms. Ask:

> Show the current goal, acceptance checks, recorded decisions, holds and next
> action. Point to the source for each. Mark anything you cannot verify as unknown.

**Checkpoint:** repair the specific missing fact. If the context is still hard to
trust, use the safe handoff below; do not deliberately fill the window with noise.

## 3. Stop starting work; find out what is still happening

Follow the [canonical fleet handoff rule](FLEET_HANDOFF.md). Before switching
tasks, record what has completed, what is running and what is uncertain. Preserve
the original task start/deadline and existing approval holds.

For example: a request to publish timed out after submission. That is **unknown**,
not “failed, retry.” Locate the operation ID and supported receipt/status first.
Keep it owned while reconciling. If no safe observation is available, hold that
operation and report the exact missing evidence; independent authorized work may
continue. A successor does not gain a fresh retry budget by receiving the task.

For local commands, use the host's supported process/task status. Let an authorized
operation reach a known safe boundary, or request a permitted cancellation and
verify the result. Closing a tab is not evidence that a process stopped. Preserve
partial files and logs; recovery or undo can itself require separate authorization.

**Checkpoint:** every pending operation has its ID (or an explicit missing-ID
note), actual known state, owner and next reconciliation action. “None” is a
checked observation, not a convenient default.

## 4. Use the actual `handoff` skill

Read [Matt Pocock's original handoff skill](../upstream/matt-pocock/skills/productivity/handoff/SKILL.md).
It is explicitly user-invoked. Where your host has registered it, ask:

```text
/handoff Continue the preview-only practice in a fresh task. Preserve the scope,
acceptance checks, verified state, unknowns, holds and next safe action.
```

If `/handoff` is unavailable, use this explicit request instead:

> Read and follow `upstream/matt-pocock/skills/productivity/handoff/SKILL.md` for
> this practice. Write the handoff to my OS temporary directory, tell me its exact
> path, and read it back. Do not claim a slash command ran.

The original skill saves outside the workspace: `$TMPDIR`, otherwise `/tmp`, or
`%TEMP%` on Windows. It calls for suggested skills, references instead of duplicated
artifacts, and redaction of secrets and sensitive personal information. Use a new
filename; preserve an existing record rather than overwrite it accidentally.

A useful handoff tells the successor:

- **Destination:** goal, acceptance checks, actual decision owner and allowed work.
- **Location:** repository/workspace, branch, commit, relevant files and uncommitted
  changes. A commit alone does not identify dirty working files.
- **Evidence:** what ran, exact commands/results and artifact references; distinguish
  verified facts, reported facts, failures, unknowns and untested claims.
- **Decisions and holds:** settled choices, relevant tickets/ADRs, open questions,
  required reviews and permissions still withheld.
- **Live state:** pending/uncertain operations, their owners and IDs, original
  timing/deadline, and any denial or retry restriction.
- **Continuation:** one next authorized action, its success/stop condition, and
  suggested skills with paths the successor can actually read.

Use the task's existing private run record as the source of truth; the temporary
handoff can point to it. Link the specification, diff and logs instead of pasting
the transcript. If using the optional fleet JSON checker, follow
[its instructions and limits](FLEET_HANDOFF.md#optional-structural-check): structural
success does not verify the claims or authorize execution.

**Checkpoint:** read the written file, not just the agent's promise to write it.
Make sure the next task can access it. A temporary file is not a durable backup,
and a local path is not automatically accessible in another cloud workspace.
Transfer only the authorized, redacted material using an available supported route.

## 5. Give a fresh task the checkpoint, not the whole transcript

Once ownership and pending work are reconciled, open a **new** task using your
host's actual controls. Keep the existing files and evidence. Give it this prompt,
replacing the bracketed paths:

> Continue from `[exact private handoff path]` in `[exact workspace]`. Read current
> project instructions, the canonical handoff rule and the actual suggested skills.
> Verify the branch, commit, dirty files, evidence and supported operation status
> before doing the recorded next action. Restate the goal, acceptance checks,
> decisions and holds. Resolve discrepancies rather than silently choosing a story.
> Keep uncertain actions held; do not duplicate existing work. Stay within the
> recorded authorization, and ask the actual decision owner about any missing scope.

The handoff is evidence to check, not higher authority than current instructions
or the operator. A changed branch, missing artifact or new instruction can make an
old next step unsafe. Read current files; a link does not update a stale checkout.

**Checkpoint:** the fresh task shows a matching or explicitly reconciled state
and a bounded next action. It has not copied all old chat history back into context.

## 6. Practice: preview, hand off, preview again

Use a quiet, empty, local practice folder you select, with no links/junctions,
valuable files, syncing or network share. Use an already available Python 3.12+
interpreter and the repository's organizer; do not install anything for this lesson.
This exercise uses **preview only**, not the Windows-only move/undo operations.
If files or a terminal are unavailable, rehearse the prompts on paper and label
the result **not executed**.

### Session A — leave a real checkpoint

1. Choose the exact practice and evidence locations. Create, or explicitly authorize
   creation of, only these three invented files (UTF-8, no trailing newline):

   | Name | Contents | Expected preview destination |
   | --- | --- | --- |
   | `garden.txt` | `Plant basil Saturday` | `Text/garden.txt` |
   | `picnic.md` | `Bring sandwiches` | `Text/picnic.md` |
   | `mystery.bin` | `synthetic` | `null` (Keep) |

2. Define acceptance **before running**: exactly those three entries and
   destinations; every original file stays in place with identical bytes; no
   category folder or action journal is created. Preview evidence goes outside
   the practice folder. No file move, apply, undo, publication or personal-file
   access is authorized.
3. From the repository root, run the commands below with your verified interpreter
   and selected paths. The Windows-style paths are examples, not defaults to use
   blindly; on another OS substitute that OS's paths. Output files must be new.

   ```powershell
   python -B examples/chad-organizer/organizer.py preview "C:/practice/context/files" "C:/practice/context/preview-before.json"
   python -B -m unittest discover -s examples/chad-organizer -p test_organizer.py -k preview_is_exact_and_read_only -v
   ```

   Check the actual JSON against the table, original bytes and acceptance rules.
   Save the command, exit status and test output outside the practice folder.
   The focused test should run **one** preview test; zero discovered tests is not
   success. It does not establish Windows move/undo behavior.
4. Use Step 4's actual handoff skill. Record the real preview path and full ID,
   repository state, observed checks, no move approval, and the next action:
   “In a fresh task, verify state and produce a second preview for comparison.”
   Verify no command remains running. Stop Session A's work; keep its artifacts.

### Session B — prove continuity

5. Start a genuinely fresh task with only Step 5's prompt and the accessible
   handoff/artifacts. Let it read the lesson and current instructions, reconcile
   state and report the same goal, acceptance checks and holds before continuing.
6. Have it produce `preview-after.json` in the same evidence location with the same
   command, changing only the output filename. Compare **parsed complete JSON**
   and IDs with `preview-before.json`, recheck the table and unchanged original
   bytes, and rerun the same focused test. For example, this comparison from the
   repository root is read-only; replace both paths:

   ```powershell
   python -B -c "import json,pathlib; a=json.loads(pathlib.Path('C:/practice/context/preview-before.json').read_text(encoding='utf-8')); b=json.loads(pathlib.Path('C:/practice/context/preview-after.json').read_text(encoding='utf-8')); assert a == b, 'Preview changed: stop and investigate'; print('Same complete preview')"
   ```

   If anything differs, preserve both outputs and investigate. Do not edit the old
   preview, move files, or treat the old ID as fresh approval. If the new task
   cannot access the same workspace, resolve that access/transfer first rather
   than pretend a different absolute root is identical.
7. Compare the before/after acceptance and test results. Ask the fresh task what
   remains unauthorized. **Pass:** identical verified preview, one focused test
   passing in each session, unchanged files, preserved holds, no pending operation.
   **Not established:** actual compaction quality, Windows moves, crash recovery,
   automatic hooks, or reliable behavior across every model/host.

This is a continuity check, not a new TDD implementation cycle. For a later code
change, agree the public behavior/test boundary and use the actual
[TDD lesson](CHAD-TDD.md). Do not invent red-before-green history for checks that
were merely rerun. The larger [interrupted-session evaluation](../evals/interrupted-handoff/README.md)
is an optional next exercise, with its own authorization and evidence limits.

## 7. Advanced: recycle a coordinator, not the whole team

Only use this when your host supports separate agents and the work permits them.
Read [SWARMS.md](SWARMS.md) and keep the [fleet rule](FLEET_HANDOFF.md) authoritative.
One agent is enough for the beginner exercise.

A coordinator's handoff needs a small map, not every child's transcript:

| Carry forward | What the successor verifies |
| --- | --- |
| Tickets, goal and acceptance | What remains and which human owns decisions |
| Child/task IDs and current state | Who is still working; last verified result vs a stale report |
| Branch/workspace/file ownership | One writer per artifact; no overlapping new assignment |
| Decisions, dependencies and blockers | Which choices are settled; what is held and why |
| Tests/reviews and evidence links | What was actually verified at which revision |
| Pending operations and original deadlines | What to observe, not reissue; who retains responsibility |

The old coordinator checkpoints and stops issuing new assignments. The successor
reads current state, reconciles active children through supported tools, and
accepts coordination explicitly. Record the transfer so **one accountable
coordinator** directs new work; existing children keep their bounded assignments
and operation ownership. An unavailable child status is unknown, not permission
to launch its replacement. If the host cannot transfer or observe child tasks,
keep the original owner or pause that dependent work and report the limitation.

Do not restart all children merely because the coordinator changed. Do not use a
new agent name, task or executor to evade a denial, approval hold or retry rule.
Preserve product, clinical, security/data, native, persistence and teardown holds.

**Checkpoint:** the successor can identify every active owner, held action and next
authorized step without resending uncertain work. The lesson is complete when you
can do that in plain language—not when you can quote a token limit.

If anything is unclear, say **“Wait, what?”** and ask for a simpler example while
keeping the scope and approval rules intact.

## Next lesson: take the work through integration

[Follow one issue from triage to main](CHAD-ISSUE-TO-MAIN.md), carrying its decisions, worktree ownership, evidence and holds through implementation, review and the actual integration gate.
