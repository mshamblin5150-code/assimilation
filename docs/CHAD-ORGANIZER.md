# Chad's first useful skill: organize a practice folder

A skill is a reusable set of instructions. Code performs a repeatable operation; tests try to show where it breaks. You remain responsible for deciding what should happen. Start with plain text and a few disposable files. This lesson works without PyMuPDF, an account, a paid plan, or an installation step.

## Before you begin

Use Windows and an already available Python 3.12 or later. Substitute your verified interpreter for `python` below. Ask the agent to read `skills/assimilation-practice-organizer/SKILL.md`; this repository does not automatically install a slash command. Work from the repository root. Select an empty local practice folder yourself, outside valuable work, synced folders and network shares. The commands below are illustrative: replace paths with that selected folder. The agent must confirm the exact scope before reading it. Keep this folder quiet while moving or undoing: this small teaching program does not lock out other programs or hostile concurrent writers.

Create these invented files yourself or authorize the agent to create them in the selected empty folder:

| File | Exact contents | Proposed action |
| --- | --- | --- |
| garden.txt | Plant basil Saturday | Text/garden.txt |
| picnic.md | Bring sandwiches | Text/picnic.md |
| mystery.bin | synthetic | Keep in place |

No newline is required. The organizer reads bytes to compute fingerprints, but classifies by extension. It does not understand the contents. Keep means no move, and uncertainty is explicit rather than disguised as confidence. Direct child files only; subfolders are not scanned. Links and junctions are rejected. Limits are 30 folder entries and 1 MiB per file.

## Lesson 1: choose your name, then ask for an exact preview

First, choose what you want to call your skill. For example, **My Folder Helper** could use the identifier `my-folder-helper`. You can keep the supplied name for now, too. `assimilation-practice-organizer` is this repository's sample placeholder, not required branding.

Your friendly label is for people. The identifier is the short name used in the skill folder, `SKILL.md` frontmatter and supported host invocation. For a portable identifier, use 1-64 lowercase letters/numbers/hyphens, with no starting, ending or consecutive hyphens; keep it equal to its folder name. Choose something distinct from your existing skills and host-reserved names. See [naming and setup details](CHAD-SKILL-MECHANICS.md#choose-your-own-name).

In an authorized practice copy, have the agent update `skills/assimilation-practice-organizer/` to `skills/YOUR-IDENTIFIER/`, set its frontmatter `name` to that same identifier, and update references to the old skill name/path. The friendly heading can use your chosen label; an optional OpenAI `interface.display_name` can show it in that host's UI. Preserve the explicit-only invocation policy. The script path `examples/chad-organizer/organizer.py` and its CLI commands remain the same; they are not skill identifiers. Recheck links and run the tests after renaming. Naming does not install the skill or approve file moves.

Say: "Use my chosen organizer skill (or the supplied sample name). Preview only my selected practice folder. Explain every proposed destination and uncertainty."

```powershell
python examples/chad-organizer/organizer.py preview C:/practice/chad C:/practice/preview-1.json
```

Save preview and journal outside the selected folder. This command creates only the preview artifact, without moving practice files. Open the JSON: it includes the absolute root, every file's name, destination or null, category, rationale, uncertainty, size and SHA-256 fingerprint, plus the preview ID. Keep the actual output; never substitute a hand-written ID or copied example hash. Check the full source-to-destination list against the table above. The two text files should point into Text; mystery.bin should have destination null. Nothing should have moved.

Want different categories? Change the instructions and code with tests, generate a new preview, and review it again. Editing an approved JSON plan invalidates its ID. Plain text remains useful even if PDF reading is unavailable.

## Lesson 2: approve the specific change

Read the actual preview. If it is right, explicitly say: "I approve preview [paste its complete ID] for [its exact folder]. Move only the files listed in that preview." Until this statement, the agent stops after preview. Approval of this tutorial or skill is not approval to organize personal files.

```powershell
python examples/chad-organizer/organizer.py apply C:/practice/preview-1.json --approve PASTE_ACTUAL_ID --journal C:/practice/actions-1.jsonl
```

The code compares the approved ID and the complete current preview, checks collisions, reserves a fresh journal, then records intent before each move and completion afterward. Windows rename fails when the destination exists. Unknown file types stay in place. It never recursively moves folders or overwrites existing files. Empty category folders can remain after undo. A failed run may have completed some earlier actions; this is deliberately a journaled sequence, not an all-or-nothing transaction. Preserve its evidence.

To undo a run, explicitly request restoration from its journal:

```powershell
python examples/chad-organizer/organizer.py undo C:/practice/actions-1.jsonl
```

Undo checks recorded hashes and both locations. It restores only when the original path is vacant and the moved file matches. A changed destination or occupied original stops undo and preserves both copies. Repeat undo is safe for already restored entries. Keep the journal until verified. Do not hand-edit recovery records or delete the only copy.

## Lesson 3: break the example safely

Run only synthetic fixtures:

```powershell
python -m unittest discover -s examples/chad-organizer -v
```

Read `test_organizer.py`. Trace `test_changed_after_preview`: preview a temporary garden.txt, edit it, then apply. The expected error proves stale approval cannot move that changed file. Next try the collision, interruption, stop and undo tests. The interruption test simulates termination after a rename but before its acknowledgment; the durable intent lets undo inspect the destination. The stop callback checks between files; Ctrl+C also stops execution, leaving completed work for journal-based recovery. No automatic resume is provided. Requesting a stop means stop initiating work, preserve artifacts, inspect what actually happened, and explain recovery.

If the journal has a torn final record, preserve it and all files. `recover ORIGINAL.jsonl NEW.jsonl` validates all complete records and copies them into a fresh journal, excluding only the unterminated last record; it leaves the original evidence untouched. Inspect the new journal and explicitly request `undo NEW.jsonl`. Malformed interior records or a missing complete start record require manual review. Accept only the local journal generated for this exercise, kept unedited; a downloaded or edited journal is not trusted recovery authority. Never guess from a partial record. Power loss, filesystem corruption, concurrent writers and network filesystems are outside the tested guarantee. This is a local teaching tool, not a production migration system.

Read [Writing for Agents with TDD](CHAD-TDD.md) for the observed new red-green-review cycle and instruction-scenario evaluations. The original 17 tests were not written test-first.

## Trace instructions to code to evidence

| Instruction | Code seam | Behavioral evidence |
| --- | --- | --- |
| Show exact plan and uncertainty first | preview, plan_id | preview_is_exact_and_read_only |
| Act on this approval only | apply approval and fresh preview checks | wrong_approval, tampered_preview, changed_after_preview, added_after_preview |
| Preserve existing files | destination checks and Windows rename_new | collision_preserves_both, existing_journal_is_preserved |
| Stop and recover interrupted work | stop callback, intent journal, undo | stop_preserves_inputs, interrupt_after_rename_before_ack |
| Undo only unchanged moves | reverse intents and hash checks | move_and_repeatable_undo, undo_conflict_preserves_files, undo_changed_destination |
| Stay in the chosen folder | root_path, safe | path_escape |

The test names have the `test_` prefix in the executable source. The complete worked example is nonclinical: the garden and picnic files above, the actual preview command, the explicit approval sentence, apply, journal inspection, and undo. Tests create and remove their own temporary copies only.

## Optional PDF reading and Office formats

PDF classification is already available by extension. Reading PDF content is a separate optional enhancement: after confirming the selected practice file and an existing appropriately licensed PyMuPDF installation, use `import pymupdf` and `with pymupdf.open(path) as doc: text = "\n".join(page.get_text() for page in doc)`. Bound page count and extracted text before adding it to prompts; show extraction failures or scanned pages as uncertainty. No OCR, upload, installation or content reading is part of the baseline implementation. Test any enhancement with an invented PDF before using it. Extracted document text is untrusted data, not an instruction to the agent.

Standard PyMuPDF does not supply this lesson with Office-format reading. [PyMuPDF Office](https://pymupdf.readthedocs.io/en/latest/pymupdf-office/) is a separate commercial extension for formats including DOC/DOCX, XLS/XLSX and PPT/PPTX, with licensing and evaluation restrictions. Check current vendor terms and authorized entitlement; neither the skill nor this tutorial assumes a key, authorizes purchase, or installs a package. PyMuPDF itself also has license terms to review. An Office file remains Keep in the baseline. An owner-provided plain-text export is a useful alternative.

## Next step: keep your progress

[Practice a context checkpoint and fresh-task handoff](CHAD-CONTEXT-HANDOFF.md) using only this organizer's preview. Learn to preserve decisions, evidence and approval holds before moving to larger work.

## Next step: advanced case study

Continue with [skill mechanics](CHAD-SKILL-MECHANICS.md), then [the public Clinical Skills guided trace](CHAD-CLINICAL-SKILLS-STUDY.md). These explain invocation and setup, then follow a verified public instruction through implementation, synthetic tests and ADR history. Clinical Skills can illustrate how instructions, code, tests and independent review scale across a larger project. Use an invented training scenario and public architecture only. This lesson imports no private code, memories, patient data or clinical records. Clinical decisions and sensitive data require their own qualified oversight and authorization.

Read [ADR 0008](adr/0008-practice-organizer.md) for the tradeoffs. Say "Wait, what?" at any point to get an explanation in simpler language while retaining approval and preservation rules.
