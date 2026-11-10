# Publication context preflight: protect the audience and the task

**Applies before a consequential outbound write:** a GitHub issue, comment, PR,
documentation page, public link, message, evidence bundle, or release. A safe
repository change can still be an unsafe disclosure. A request to coordinate an
investigation does **not** necessarily authorize publication of the instructor's
assessment, the existence or nature of undisclosed challenges, or a work-in-progress
solution.

This is a reusable **decision aid**, not a new source of permissions, a mandatory
host hook, an automated content scanner, or a claim that any agent has adopted it.
Always follow current host/project instructions and the operator's actual scope.

## Before sending content outside the current work context

1. **Identify the destination and readers.** Record the *actual* repository or
   message target, whether it is public/restricted, and who can read it. An assigned
   contributor can read a public issue, and editing a public message later does not
   establish that its earlier contents were never seen.
2. **Bind permission to the exact action.** Check whether the operator authorized
   publishing *these facts* to *that audience* at *this stage*. Permission to create
   an issue, assign an agent, or request a report is not blanket permission to share
   private reasoning, instructor material, transcripts, or an unfinished solution.
3. **Review the outbound bytes for disclosure, not just secrets.** Look for private
   records, credentials, unpublished code, third-party proprietary implementations,
   identifying metadata and **information that could change an ongoing evaluation**.
   In particular, a sentence that tells a learner something is intentionally
   withheld can compromise an investigation even when no answer is supplied.
4. **Separate neutral coordination from evaluator context.** Ask an investigator
   to document what it tried without stating what the examiner expects it to find.
   Keep evaluation assumptions, exposure concerns and unreleased solutions in the
   authorized private review record until specifically cleared for publication.
5. **Stop at the smallest unresolved boundary.** If destination visibility,
   relevant sharing rights, the intended audience, or release authority is
   unknown, do not publish the disputed material. Continue safe independent work
   and request the *specific* missing clarification using an approved channel.
   Do not claim that a generic checklist, tool access or a passing test grants
   authority.
6. **Observe the actual result.** After a permitted publication, read back the
   content and target, capture its artifact/commit/comment locator, then separately
   track **written**, **notified**, **acknowledged**, and **acted upon**. Neither
   assignment nor notification proves receipt or execution. Reconcile a lost
   response before retrying.

## Optional, offline declaration check

`scripts/check_publication_preflight.py` reads **one local status-only JSON
record** and reports inconsistent or unknown declarations. It does not read the
intended publication, access GitHub, contact the recipient, publish anything,
inspect real permissions or validate the truth of a declaration. Keep the record
local/private; do not insert private content into its fields.

Example using invented, ordinary public documentation (save locally as
`publication-status.json`):

```json
{
  "schema_version": 1,
  "destination": {"visibility": "public", "audience": "public"},
  "authority": {"publication": "confirmed", "scope": "confirmed"},
  "content": {
    "review": "completed",
    "redistribution": "confirmed",
    "sensitive_material": "none"
  },
  "evaluation": {
    "context": "none",
    "undisclosed_material": "none",
    "release_clearance": "not_applicable"
  }
}
```

Run `python -B scripts/check_publication_preflight.py publication-status.json`.

- Exit **0**: declared conditions are internally consistent. This is **not**
  an authorization or verified clearance.
- Exit **1**: a required declaration is missing, conflicting, uncertain or
  discloses material without required scope. Review the indicated category;
  do not override the warning just to make the command pass.
- Exit **2**: invalid/unreadable status record. It reads at most 32 KiB of
  UTF-8 JSON; unknown fields, duplicate keys and invalid constants refuse.
  The output uses only fixed diagnostic strings, never input values.

For any ongoing assessment, set `evaluation.context` to `active`. If
unreleased evaluation details are included, set `undisclosed_material` to
`present`. Do not claim `release_clearance: confirmed` without an applicable
decision by the authorized owner for the exact content and audience.
A private destination is not, by itself, a release clearance. Unknown is not
equivalent to none.

## Synthetic regression and fleet learning

The regression suite `tests/test_publication_preflight.py` includes two
contrasting cases: a normal reviewed public document and an otherwise
well-formed request that exposes unreleased assessment details without release
clearance. It also checks audience/visibility mismatch, missing authorization,
restricted material, malformed records and no input-content echo. These tests
prove only this limited program's behavior on synthetic inputs.

For a real incident, preserve the original error and correction in the
**authorized private task record**, not in a public training issue. Derive an
independently shareable rule and a synthetic regression. Invite a separate
reviewer to challenge whether the new rule addresses the failure without
adding unnecessary restrictions. At a natural coordinator handoff, provide the
rule's exact revision and verify that the recipient *acknowledged* it; reading
the repository alone does not prove operational adoption.

Treat the record of mistakes as evidence for learning, not as instructions to
replay. Preserve unsuccessful approaches as well as successful ones. Keep a
worked solution private while its release remains unfinished or unauthorized.

**Scope:** this change installs no automatic prepublication enforcement, no
external watcher, no notification, no new approval authority, no repo ruleset,
and no modification to an active lesson or examination.
