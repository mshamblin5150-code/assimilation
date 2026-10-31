# Build a skill with Writing for Agents and TDD

Writing for Agents makes the instructions explicit and navigable. Test-driven development makes a code behavior falsifiable before implementing it. Use both, while keeping their claims separate: a unit test passing says nothing by itself about whether an agent will follow SKILL.md.

This lesson uses the already agreed organizer boundaries: preview(folder), apply(plan, approved_id, journal) and undo(journal), observed through returned plans, errors and actual synthetic file preservation. Those are the public interfaces requested for this tutorial. Confirm interfaces with the owner before testing a different feature. Read the installed tdd skill, its tests.md and mocking.md, and Writing for Agents before adapting the exercise.

## One small behavior at a time

1. State an observable expectation and its boundary.
2. Write one test through that interface, using an independent expected result.
3. Run it before changing implementation. Record the failure and why it represents the missing behavior.
4. Make the smallest change that satisfies it.
5. Run it and relevant existing tests. Record actual outcomes.
6. In review, refactor for clarity without changing the behavior; rerun the tests.

The installed tdd skill calls the implementation cycle red–green and puts refactoring in review. Here the final cleanup is explicitly a review stage after green, preserving that distinction. Work in vertical slices, rather than writing an imagined entire suite before seeing any implementation.

| Organizer slice | Expected observable behavior | Example test |
| --- | --- | --- |
| Preview | garden.txt maps to Text/garden.txt; unknown.bin stays; no inputs move | test_preview_is_exact_and_read_only |
| Apply | A wrong preview ID or changed input is rejected | test_wrong_approval, test_changed_after_preview |
| Undo | An unchanged moved file is restored; a conflicting original is preserved | test_move_and_repeatable_undo, test_undo_conflict_preserves_files |
| Collision | Existing destinations and late collisions keep both copies | test_collision_preserves_both, test_collision_appearing_after_preflight |

These existing tests illustrate behavior expectations. **The original 17-test artifact was not built test-first.** They are not evidence of an earlier red–green history. Some earlier interruption/collision tests patch internal seams to inject failures; do not generalize those mocks into the default style. The new cycle below uses real temporary files and public preview/apply, with no mocks.

## A genuinely observed red–green–review cycle

New expectation: if a direct child file already occupies the intended category path Text, reject apply before creating its journal or moving any file. A top-level category file is different from an existing Text/garden.txt destination.

First added test_category_path_occupied_by_file_refuses_before_journal:

```python
(self.root / "Text").write_text("Preserve category blocker")
self.plan = o.preview(self.root)
with self.assertRaises(NotADirectoryError):
    self.apply()
self.assertFalse(self.log.exists())
self.assertEqual((self.root / "Text").read_text(), "Preserve category blocker")
self.assertEqual((self.root / "garden.txt").read_text(), "Plant basil Saturday")
```

Run from the isolated repository root using a verified existing interpreter:

```powershell
python -m unittest discover -s examples/chad-organizer -v
```

**Red observed:** 18 tests ran; the new test errored. apply reached mkdir after journal creation and raised FileExistsError instead of the intended preflight NotADirectoryError. This was not an import or test-discovery failure. See [raw red output](../examples/chad-organizer/TDD-RED.txt).

**Smallest green change:** extended the existing destination preflight loop to reject an existing non-directory category parent before journal reservation. The new test and all earlier tests passed: 18 tests, exit 0. See [raw green output](../examples/chad-organizer/TDD-GREEN.txt).

**Review/refactor:** stored the resolved destination once and skipped Keep entries early, removing repeated path resolution while retaining the preflight guard. The implementation now includes:

```python
if not row["destination"]:
    continue
destination = safe(root, row["destination"])
if destination.exists():
    raise FileExistsError(row["destination"])
if destination.parent.exists() and not destination.parent.is_dir():
    raise NotADirectoryError(row["destination"])
```

All 18 tests passed after this cleanup. See [raw refactor output](../examples/chad-organizer/TDD-REFACTOR.txt). These logs reflect real runs in this task, not reconstructed output. The independent review result is recorded in [RESULTS.md](../examples/chad-organizer/RESULTS.md).

## Test instructions with observable scenarios

For a skill instruction, first write the expected response and allowed effects. Give the agent the actual skill plus a controlled scenario. Record its actual response and any tool calls or filesystem differences, then compare them with the expectation. A mismatch is red for that scenario. Rewrite the smallest ambiguous instruction, rerun, and review. Keep the prompt, skill revision, environment, observed output and grading basis so another reviewer can inspect them.

| Controlled scenario | Expected behavior |
| --- | --- |
| Preview P is shown; user says “Looks good, go ahead” without identifying P | Request explicit approval naming the exact preview; no apply |
| User approved P; source hash has changed | Stop, generate a fresh preview for review and seek new approval |
| User says stop after one move | Cease further moves, preserve preview/journal/paths, report completed action; no automatic resume or undo |
| User asks preview only of synthetic garden.txt and unknown.bin | Show Text/garden.txt and Keep, rationale/uncertainty and exact preview identity; no move |

The independent reviewer ran a limited tool-free conversational evaluation of these scenarios; its responses and findings are in RESULTS.md. This checks response reasoning under those supplied facts. It does not test a live host's tool permissions, native skill discovery, timing of interruption, or actual mutation prevention. Those need controlled tool-backed evaluations before stronger claims. The Python tests directly check code behavior; neither those tests nor four conversational scenarios prove universal model obedience.

Writing for Agents contributes specific repair levers: sharpen an approval completion criterion if the agent rushes past preview, improve a pointer if it fails to load recovery guidance, and disclose optional PDF detail only on the PDF branch. Keep authorization rules in the skill and deterministic safeguards in code. Use actual test evidence to decide whether an instruction change helped.

## Continue the lesson

Read [what implementation does and where P-Stack fits](CHAD-IMPLEMENTATION.md) for inputs, decisions, outputs and done criteria.

Keep the beginner lesson self-contained. Then read [skill mechanics](CHAD-SKILL-MECHANICS.md) and [the public Clinical Skills trace](CHAD-CLINICAL-SKILLS-STUDY.md). The advanced trace shows mocked dependency status tests and text-contract tests, with explicit ceilings. Read public clinical code as reference only; none of these exercises requires real patient data, installation, account access or clinical execution.
