# Chad organizer verification and handoff

Date: 2026-10-31. Scope: synthetic local Windows practice files only.

## Isolation and ownership

Created a standalone Git snapshot from Assimilation `434de39` using `git archive`, inside the authorized task workspace. Root source contains active Windows onboarding and PR8 review workspaces; none was edited. Source Git status/worktree qualification could not be established: Git reported “must be run in a work tree” and an explicit source `git -C` inspection reported Permission denied. Read-only archive and file inspection succeeded. Therefore this deliverable is a separate snapshot/patch, not an integration into the active checkout; active owner status remains unqualified. Parent should reconcile current owners and base before integrating. No remote writes, installs, security changes, purchases, real-file processing or merges occurred.

Write fence: `skills/assimilation-practice-organizer/`, `docs/CHAD-ORGANIZER.md`, `docs/adr/0008-practice-organizer.md`, `examples/chad-organizer/`. No installer, root onboarding, upstream source or shared policy edits.

## Methods read and applied

Writing for Agents and SKILL-MECHANICS: explicit user invocation, ordered completion criteria, optional PDF branch disclosed in tutorial. Read through the installed skill source and corresponding repo files. Matt source pin `59db609eb1e18aaf59b63284d0e52255aff0c63c`.

P-Stack `upstream/pstack/skills/principle-prove-it-works/SKILL.md`: checked actual files, ran behavioral tests and CLI flow. P-Stack pin `c742dd61706fbacc1b95f1a20b7b988cf096ce6c`. Installed router compatibility guidance also read. These were source-guided procedures, not a claim of native slash-command invocation.

Matt code-review source was read for standards/spec review guidance. Independent reviewer received the bounded implementation and approved task requirements. This was a scoped independent adversarial review, not the native two-axis tracker workflow; no tracker publication or setup was performed.

## Observed verification

Interpreter: Python 3.14 (verified absolute interpreter path redacted) on Windows.

From the isolated repository root:

```powershell
& <verified-python.exe> -m unittest discover -s examples/chad-organizer -v
git diff --check
```

Final author run: 17 tests passed, exit 0; diff whitespace check passed. Tests cover exact read-only preview, wrong approval, plan tampering, changed/added files, initial and late collisions, existing journal preservation, interrupted rename acknowledgment, stop before work and after first move, repeatable undo, undo conflicts/edited destination, path escape, torn-tail recovery and malformed interior rejection. Test source names are the exact test inventory.

A separate subprocess CLI exercise created the three tutorial files in a disposable workspace folder, ran `preview`, approved that generated ID, ran `apply` and `undo`, and asserted file contents and locations. Passed, exit 0. This was synthetic test authorization, not approval to organize real user files.

Initial verification failures retained here: the default `python` alias was inaccessible; verified interpreter used instead. First discovery command used the parent directory and found no importable start directory. Corrected working directory/path. Initial fixture run hit sandbox-default temporary directory access failures; fixtures now allocate under current working directory. No security settings changed.

Independent review initially reproduced a torn-final-journal defect. Added explicit recovery into a fresh journal while preserving original evidence. Reviewer independently reran the then-current 15-test suite (all passed) and simulated a torn moved acknowledgment after rename, recovered and restored successfully. Reviewer inspected code, skill and tutorial and reported no blocking findings within Windows/synthetic/quiet-folder scope. Author subsequently added late-collision and partial-stop tests; final 17-test run passed. Review was an actual separate agent, with read-only scope.

## Limits and remaining gates

PDF extraction is documented optional guidance, not executed or installed. Office processing remains unsupported by baseline; current commercial extension distinction verified against primary vendor docs linked in tutorial. PyMuPDF/Office licensing, actual live files, cross-platform move semantics, filesystem corruption/power-loss durability and hostile concurrent writers were not tested. Journal is trusted local evidence; malformed interior records require manual review. Empty category folders remain after undo.

No product blocker within the bounded example. Integration with the active Vox/onboarding branch remains intentionally unperformed and owner qualification is unresolved. Human acceptance and applicable publication authorization remain separate gates.

## Advanced curriculum extension (2026-10-31)

After the initial commit, the independent reviewer reran all 17 tests, reviewed both added tests and the complete beginner candidate, and reported no blocking defects within its stated scope. The late-collision test preserves both source and racing destination; the partial-stop test restores the original preview through undo.

Added `docs/CHAD-SKILL-MECHANICS.md` and `docs/CHAD-CLINICAL-SKILLS-STUDY.md`, linked from the existing lesson and skill. Added the explicit-only Codex `agents/openai.yaml` sidecar so the intended user-invocation policy has the current host-specific representation as well as the source frontmatter. No installer or user configuration was changed.

Verified current official OpenAI skill documentation (the developers.openai.com/codex/skills URL redirected to https://learn.chatgpt.com/docs/build-skills) and official Claude Code skills documentation at https://code.claude.com/docs/en/skills. These explain host-specific discovery and invocation; Claude extensions for hooks, tool preapproval, model and forked execution are distinguished from portable bare Markdown. Inspected actual Assimilation bridge_policy/_install and named restriction tests; did not execute an installer.

Public Clinical Skills discovery first tried an underscore name and received 404. Public repository search confirmed `mshamblin5150-code/clinical-skills` and public visibility. Verified commit `6fc9d32c32b246ef3dc022f3d7a8e677ad2f2e66` through commits/main. Public tree and seven exact file/blob identities verified; provenance is recorded in `public-study-sources.json`. Representative trace covers setup step 0, pdf_engine acquire/engine_version/main, mocked status tests and text contract tests, ADR 0175 and implementation commit `3180c234d5d1fea5b34316fbe4eb476455536be8`. ADR 0001 supplies the external-observation test principle. No clinical workflow, dependency installation, patient data, local clinical checkout or private corpus was used. Upstream tests were read, not run. Optional clone commands are learner instructions, not actions performed here.

The eleven-skill rundown is a pinned orientation linked to the authoritative upstream catalog; Praeceptor's separately requested README refresh remains outside this candidate's write fence. No message to Chad or upstream README edit was performed. Integration should coordinate the catalog link/pin with that refresh, without copying its live inventory into a second maintained catalog.

Static verification: all seven public source paths/blob hashes matched the fetched tree; 11 relative documentation links resolved; provenance had seven entries; explicit-only Codex sidecar contained the documented false policy; git diff --check passed. Original 17 behavioral tests remain applicable because organizer.py and test_organizer.py were unchanged by this extension.

## Observed TDD and implementation extension

Loaded the installed Matt Pocock tdd skill plus tests.md/mocking.md, re-read Writing for Agents, and read the installed implement skill. The user explicitly requested preview/apply/undo/collision behavior interfaces; the new test uses those existing agreed public interfaces. The earlier 17 tests were not test-first.

New behavior: an existing file at a category path (Text) must refuse apply before reserving a journal and preserve both files. Added test_category_path_occupied_by_file_refuses_before_journal before changing implementation. Ran the full focused suite: 18 tests, 1 error, exit 1 (TDD-RED.txt). The actual failure reached mkdir after journal reservation and raised FileExistsError. Added the smallest preflight parent-type guard, ran again: 18 passed, exit 0 (TDD-GREEN.txt). Review-stage cleanup stored resolved destination once and skipped Keep early; reran: 18 passed, exit 0 (TDD-REFACTOR.txt). Logs are actual outputs, not reconstructed transcripts.

Independent reviewer reran all 18, exit 0, and reviewed the new test, code and TDD lesson with no blocking findings. It also ran four tool-free conversational scenarios against the skill: A requested exact preview/folder approval before moving; B stopped on changed fingerprint and requested fresh preview approval; C ceased moves and preserved evidence awaiting separate undo/resume; D proposed Text/garden.txt and Keep with rationale/uncertainty while declining to invent absent hashes or preview ID. No mismatch found under supplied facts. D had no bytes/root/generated ID, so exact preview-identity production was not evaluated. These are limited conversational source-reading evaluations, not tool-backed host enforcement or statistical model-obedience evidence.

CHAD-IMPLEMENTATION.md explains requirements, instructions, new failing test, smallest code change, passing test, review refactor, independent challenge and delivery with explicit inputs/outputs/done criteria. Only the new collision slice has observed TDD history.

P-Stack installed router/catalog read successfully; expanded actual-source resource lookup returned “failed to read skill resource.” No claim that its source archive was extracted or a native workflow ran. Complete actual sources under the isolated repo upstream/pstack were read at pin c742dd61706fbacc1b95f1a20b7b988cf096ce6c: foundational-thinking, test-behavior-not-implementation, prove-it-works, blast-radius, architect, interrogate, boundary-discipline, why and unslop. The lesson directly uses the first three principles, while architect/blast-radius/interrogate are explicitly future advanced entry points whose complete native procedures were not run. Installed router snapshot e43c7ee is distinguished from repo snapshot c742dd6. No global mode, native agent registration, unsupported model routing or installed configuration change occurred. Expanded installed-source access remains a limitation if the owner requires that exact snapshot rather than the verified repo sources.

Final independent review of CHAD-IMPLEMENTATION.md and linked sources found no blocking findings or unsupported workflow claims. Final author run: 18 tests passed (0.471s), exit 0; 28 curriculum relative links resolved; git diff --check passed. Public source identities and commit were verified through public GitHub; no existing source checkout was accessed during these extensions.

Packaging correction: cached diff check found extra blank EOF lines in four new lesson documents. Removed those blank lines and reran the cached check before finalizing. Earlier unstaged-only diff checks had not included the new untracked documents.

## Learner-chosen skill name

Added Lesson 1 choice of a friendly label and portable skill identifier, retaining the supplied source name only as a clearly labeled sample placeholder. Verified naming rules against the Agent Skills specification, official OpenAI skill/UI metadata documentation and Claude Code name/reserved-name documentation on 2026-10-31. The lesson explains parent-directory/frontmatter alignment, updating references, preserving invocation policy, optional display_name, host discovery and independent Python module names.

Observed disposable-copy substitution from assimilation-practice-organizer to my-folder-helper: folder, frontmatter, heading, UI label, explicit-only policy, tutorial reference and all six skill-local links passed. No live skill renamed or installed. Original curriculum now has 29 valid relative links; diff whitespace check passed. Python implementation/tests unchanged by naming edits, so prior 18-test behavioral evidence remains applicable.

Landing on main is not yet verified. Local source configuration denial remains respected. Discovery shows connected GitHub branch/commit/PR/merge tools exist, potentially an independent remote integration route, but this candidate has not established current Assimilation remote-main base/owner coordination or merged via that route. Parent coordination must reconcile Vox/Praeceptor ownership and the current base, run integrated checks/review and verify the resulting main commit before announcing landing. No denied local checkout access was retried or bypassed.

Independent naming review checked official rules and flagged reservation wording precision. Revised the Claude note to distinguish the managed synced directory from the reserved anthropic-skills namespace, with an explicit current-host verification pointer. No behavior change.

## Public evidence redaction

The public copy replaces personal interpreter/workspace paths with `<verified-python.exe>`, `<isolated-workspace>` and `<python-home>`. Test names, failures, line numbers and outcomes are unchanged; the original artifact is retained separately. The historical candidate and review entries above remain dated evidence, not current landing claims.

## Current-main integration checkpoint

The separate tutorial patch was reconciled onto public main
`69d0498990ef2628f7a2f12d2d0ff367dda77851`, whose complete tree identity is
`51fb3821857e951148d374e5278f8f09e56ab122`. The independent cloud verification
copy matched all 976 baseline blobs and the exact tree; no denied local
configuration read or original Windows checkout access was needed. The installer
owner confirmed non-overlap and no planned main update. Clinical Skills catalog
coordination confirmed the eleven canonical skills at the pinned revision; its
separate README refresh remains unpublished.

Integration preserves existing installer/onboarding changes. It adds a README
entry, uses ADR 0008 because 0007 is already occupied, pins the authoritative
Clinical Skills catalog, and redacts personal paths in the public evidence.
Independent Spec and Standards reviews both found that file-relative skill links
would break after installation. The correction uses six explicit repository-root
resource paths with missing-root/file refusal guidance; source, copied and renamed
layouts were checked without executing the installer. Both reviews verified the
correction with no remaining confirmed findings.

Cloud Linux/Python 3.12 verification: the standalone onboarding clean-checkout
harness passed; all 175 existing repository tests passed; complete pinned source
snapshot verification passed. These checks are not Windows organizer execution.
Organizer implementation and its 18 behavioral tests remain byte-for-byte equal
to the reviewed Windows candidate. A separate read-only exact-PR-head Windows CI
workflow now runs those disposable-fixture tests; inspect its actual result
before claiming integrated native validation or landing. No installer activation,
private clinical workflow or real-file organizing was performed.
