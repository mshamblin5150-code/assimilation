# Instructor key — read after the blind review

Do not include this file in the reviewer's input packet. Candidate A deliberately overclaims; Candidate B is a clean control, not a real project report.

| Claim | Evidence | Why it fails |
|---|---|---|
| “recursively” | T1 | Scope is direct children only |
| “sorts every document” | T1 | Preview proposes destinations; it does not move files or promise every document type |
| “Windows and Linux” | T3 | No Linux move test was run; the packet does not establish that support |
| “tests prove … always recoverable” | T2–T3 | Conditional undo and finite synthetic tests do not establish a universal guarantee |
| “even after power loss” | T2 | That case is expressly outside the established evidence |
| “independent review approved the final fix” | T4 | The review concerns R1; the fix is R2, with no independent rereview |
| “merged” | T5 | The candidate is local with no PR or merge |
| “ready for use” | T2–T5 | The claimed breadth and completion exceed the packet; a release-readiness judgment needs defined criteria |


## Expected bounded repair / clean control

> The training organizer previews direct child files without moving them. The synthetic R1 receipt records 18 passing Windows tests; Linux moves and native host invocation were not tested. Undo has unchanged-file and vacant-path conditions, and power-loss recovery is unestablished. An independent reviewer found an R1 journal defect; R2 contains the author's repair but lacks a final independent rereview and test receipt in this packet. The candidate remains local and unmerged.

“No verified findings” is appropriate for Candidate B against the unchanged packet. A reviewer may suggest wording improvements, but must not label supported claims false merely to produce findings. Missing sources or unread inputs require an incomplete-coverage statement.
