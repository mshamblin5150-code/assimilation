# Practice Agent Brief: recognize reStructuredText notes

**Training artifact, not a live issue or approval.** Use only after the practice
owner confirms this behavior, test seam and local implementation scope. The
learner's local issue is the canonical tracker for the exercise. This filled
example shows the output of triage; it does not replace the interview when the
owner wants different behavior.

**Category:** enhancement

**Summary:** Classify reStructuredText filename extensions as Text in the practice
organizer's preview while retaining its existing safety and approval boundaries.

**Current behavior:** The organizer recognizes text and Markdown suffixes, while
`.rst` is unknown and therefore Keep. Verify that at the selected base; if already
implemented, report it and choose another exercise rather than manufacture a bug.

**Desired behavior:** A direct child file whose suffix is `.rst`, in any letter
case, receives category `Text` and destination `Text/<unchanged original name>`.
Classification remains extension-only; content is not parsed or interpreted.
The existing fingerprint read remains; this is not a claim of zero byte reads.

**Key interfaces:**

- `preview(folder)` returns the proposed plan; reading that plan is not an apply.
- Preview file rows retain their source name, category, destination, size,
  fingerprint, rationale and uncertainty semantics.
- The approved plan remains the input to apply. A new category result can change
  a preview ID and a later approved move destination; preserve fresh approval.

**Acceptance criteria:**

- [ ] Lowercase `.rst` and uppercase `.RST` examples classify as Text with their
  original filename case preserved in the destination.
- [ ] An unknown `.bin` example remains Keep with destination `null`; existing
  text/Markdown/PDF behavior is not intentionally changed.
- [ ] Preview leaves the exact synthetic source bytes and folder entries intact,
  creates no category directory, and repeated unchanged preview is identical.
- [ ] New behavior is checked through the owner-agreed public `preview(folder)`
  seam using real temporary files; record a meaningful failing-before result
  before the smallest implementation, then passing-after results.
- [ ] Existing relevant tests, available platform checks and independent review
  are reported with failures, unavailable checks and remaining approval holds.
- [ ] Code and instructions agree that `.rst` is extension-classified, not parsed.

**Out of scope:**

- Real personal files, recursive scanning, parsers, third-party packages or installs.
- Changing links/junctions, size/count limits, collision handling, approval checks,
  journal/recovery behavior, or the Windows-only move/undo boundary.
- Executing apply/undo, public issues/PRs/pushes, main-branch changes in the source
  repository, production activation, or treating lesson approval as those permissions.

**Existing decision:** Preserve [ADR 0008](../../docs/adr/0008-practice-organizer.md)'s
extension-only classification and separate exact-plan approval. This small suffix
addition is reversible; it does not by itself require a new ADR. If the owner
changes a durable boundary, record that decision as it lands and revise this brief
before implementation.

**Readiness:** The owner has confirmed the intended behavior and test seam, the
brief is current, dependencies are satisfied, the implementation worktree has one
owner, and local code/test changes are authorized. A `ready-for-agent` label alone
does not establish those facts. Missing confirmation keeps the exercise paused.
