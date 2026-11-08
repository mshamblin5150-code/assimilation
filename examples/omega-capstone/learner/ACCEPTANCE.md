# Frozen acceptance contract OMEGA-1

This document and the packet MANIFEST.json are disclosed before admission. Every
graded requirement is here. Case values may vary; no hidden requirement or preferred
algorithm, language, framework, design pattern, skill sequence or architecture is
graded. Request clarification of ambiguities before beginning. An examiner change
creates a new version and receipt; it cannot retroactively change a running attempt.

## New engineering challenge: an offline reservation evidence ledger

R01. Investigate the supplied legacy artifact. Retain at least four dated
predictions and actual observations covering a boundary, invalid input, and
reordered input. Bind observations to the artifact hash, command, input, output
and exit. Explain one capability/principle accurately, separating observation,
inference and uncertainty. Source inspection is legitimate; fresh decompilation
and proprietary tooling are not required. Correctly admitting an untested claim
is preferable to claiming execution that did not happen.

R02. Evaluate applicability to the ledger below. Document an evidence-based
adoption/adaptation OR rejection of an unsuitable capability with a suitable
original alternative. Either route receives equal credit under identical behavior
and evidence requirements. State the benefit, limitation, alternative and reason.
The legacy utility's behavior is not the new ledger's specification.

R03. Supply one documented, offline command that reads one UTF-8 JSON request
from stdin and produces one response, then exits. Invocation and language are your
choice. No network, real waits, device calls, credential access, installer, shell
side effects or input-file mutation. Output goes only to stdout/stderr. Tests may
create their own synthetic temporary files. The request schema is exactly:
`{"window":[start,end],"capacity":integer,"events":[event,...]}`.
An event has exactly `id`, `revision`, `start`, `end`, `units`, `state`.

- Integers are JSON integers, excluding booleans and floating-point notation.
  Window bounds satisfy 0 <= start < end <= 1000000; capacity is 1..1000.
- Each id matches ASCII `[A-Za-z0-9_-]{1,16}`. Revision is 0..1000000,
  units 1..1000, and window.start <= event.start < event.end <= window.end.
  State is exactly `active` or `cancel`. Cancel events still contain all fields.
- Input size is at most 65536 bytes and at most 256 events. Duplicate JSON keys,
  missing/extra keys, invalid UTF-8/JSON and nonfinite numbers are invalid.
  Validate every supplied event, including historical revisions and cancellations.
- Identical semantic copies of an id/revision record count once, independent of
  object key order. Different records with the same id and revision are a conflict,
  including historical revisions. For each id, the highest revision wins,
  independent of input order. A winning cancel removes that id from coverage.
- All time ranges are half-open [start,end). Endpoints are exact integers:
  touching ranges do not overlap. Never fill a gap without evidence.
- On success, return exactly `{"segments":[...],"uncovered":[[start,end],...],
  "status":"OK"}` or the same with status `CONFLICT`. Each segment has exactly
  `start`, `end`, `used`, `ids`, `over`. Include only nonempty covered spans.
  `ids` is the ascending ASCII code-point lexicographically sorted list of active winning event ids covering the entire span;
  `used` is their units sum; `over` is the boolean used > capacity.
  Segments are maximal contiguous spans with the same ids, ordered by start.
  Uncovered ranges are the maximal complement of coverage within window, ordered
  by start. Status is CONFLICT iff any segment is over capacity; oversubscription
  is valid evidence to report, not malformed input. Empty events means no segments
  and the entire window uncovered. Record ordering must not change the response.
- Exit 0 for success, with empty stderr. On failure exit 2, with empty stdout and exactly one JSON
  object `{"error":"CODE"}` on stderr. Error precedence: bytes over 65536 =>
  LIMIT_EXCEEDED; then parsing/root/window/capacity/events-list structural errors
  => INVALID_INPUT; then more than 256 events => LIMIT_EXCEEDED; then any invalid
  event => INVALID_INPUT; then conflicting id/revision copies =>
  CONFLICTING_REVISION. No partial success response. Unknown outer/inner keys are
  structural/event errors respectively. Whitespace/object-key order are ungraded;
  array order, scalar types, values and absence of extra output are graded.
- Each finite examination request, valid or invalid, contains at most 65537 bytes
  and must terminate within 30 seconds on the admitted host, with at most 4 MiB
  stdout plus stderr. Hardware/environment failures are
  investigated, not silently graded as code failures. The limit is calibrated and
  frozen before admission; an unsuitable host blocks release rather than changing
  an active attempt. No specific algorithm or asymptotic complexity is required.

R04. Implement the ledger originally; attribute sources and assistance. Keep
important decisions in ADRs with alternatives, consequences and owner. Use the
project's chosen vocabulary consistently. Provide evidence for the R02 judgment,
without needing to copy any artifact implementation or use its internal structure.

R05. Supply rerunnable behavioral tests with literal or independently derived
expectations covering revision selection, identical/conflicting duplicates,
cancellation, overlap and capacity, touching endpoints and gaps, empty evidence,
invalid input/error precedence, bounds and ordering invariance. Demonstrate at
least one actual meaningful failure caused by a deliberately introduced behavior
defect or a genuine missing behavior, and the restored passing result. Label
seeded defects, characterization, post-hoc tests and actual test-first development
truthfully. Passing zero tests, disabling assertions or hiding failures is not
verification. Preserve failed attempts and corrections.

R06. Your GitHub submission at a full commit includes original source, license,
README scope/installation/runtime versions and offline reproduction command,
tests, ADRs, artifact/source provenance, exact commands/exits/results, assistance,
limits and remaining unverified claims. You choose and authorize repository and
visibility; private is acceptable with authorized independent access. No live data,
credentials, devices, automatic production deployment or undeclared dependencies.
A complete uploaded file alone does not satisfy these requirements.

R07. An unfamiliar independent engineer must obtain your authorized repository,
checkout the exact submitted commit, understand the contract and reproduce the
observed results from the README without your help. The reviewer must inspect
source and test assertions, challenge at least one meaningful boundary/negative
case and one changed input, and record commands, hashes, outputs, exits and limits.
Genuine missing access/execution evidence produces NOT VERIFIED, not invented proof.

R08. After submission, demonstrate understanding to that reviewer without solution
coaching: (a) predict one previously unshown bounded input's result before running
it, compare and reconcile discrepancies; (b) trace one behavior through your source
and its meaningful test; (c) defend your artifact adoption/rejection using actual
evidence and a credible alternative; (d) distinguish three reviewer-selected
completion claims as observed, inferred or unverified with supporting evidence.
The reviewer records the prompts, your original answers, observations and any
corrections. All four must be supported. A corrected answer needs a fresh comparable
input/check to establish understanding; retain the earlier answer. Authorized tools
and declared assistance remain allowed, but cannot replace your explanation.

R09. Preserve attempt and evaluation history, including failed attempts, corrections,
contract/artifact/submission identities, access scope, reviewer identity and every
criterion disposition. Do not overwrite an earlier attempt to erase a failure.
Number One maintains the examiner's append-only record. You maintain your original
work and evidence. No certificate is issued before actual submission and review.

## Determination after submission only

Each R01..R09 is verified satisfied, verified unsatisfied, or not verified, with
an evidence locator. PASS requires every criterion verified satisfied, independent
reproduction and R08 understanding. REVISION REQUIRED means at least one criterion
is verified unsatisfied; identify it and retain evidence. Otherwise any unresolved
required evidence means NOT VERIFIED. Missing access is not evidence of a failed
algorithm. An explicitly omitted required submission item can be a verified failure;
an inaccessible item is unknown. No compensating points or style preferences apply.
Before submission the state is NOT SUBMITTED, with no graduation determination.

## Bounds and authority

Use authorized synthetic materials and legitimate tools. No real patient/device
records, private targets, third-party code copying, security/permissions changes,
installation, credential discovery or deployment. Chad owns implementation and
consequential decisions. Ordinary access/environment assistance is allowed without
revealing a solution. Existing Assimilation and target-project holds remain binding.
