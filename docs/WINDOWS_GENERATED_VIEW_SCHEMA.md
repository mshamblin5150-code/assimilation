# Generated view and approval plan: proposed wire contract

Status: **proposal for review, not an accepted native security contract**.
This specifies a pure data boundary for issue 11 and PR 12. It neither reads a
destination nor grants consent, verifies provenance, locks files, or executes a
transaction. See [ADR 0015](adr/0015-generated-view-plan-wire-contract.md).

## Parsing and binding

Proposed inputs are UTF-8 JSON objects, at most 8 MiB each. Reject duplicate keys,
unknown fields, non-JSON numeric constants, floats, booleans in integer fields,
unsupported versions, and malformed strings before producing a plan. Reject
rather than trim, normalize, case-correct, or silently discard input.

The proposed digest encoding is UTF-8 JSON with object keys sorted by Unicode
code point, no insignificant whitespace, strings emitted with ASCII JSON escapes,
and nonnegative integers emitted in shortest decimal form, with zero written `0`.
Array order is preserved. Strings reject unpaired Unicode surrogates. The string
encoding uses `\"` for quotation marks and `\\` for backslashes. It uses the
short escapes `\b`, `\f`, `\n`, `\r`, and `\t` for those five control characters.
Other characters below U+0020 use lowercase four-digit `\u` escapes. Printable
ASCII characters, including `/`, are emitted unchanged. Characters above U+007F
use lowercase four-digit `\u` escapes; supplementary code points use their UTF-16
surrogate pair as two such escapes. U+007F is encoded as `\u007f`.

The byte sequence has no BOM or final newline. A digest is lowercase SHA-256
hexadecimal of those bytes. Cross-language worked vectors remain required to
verify an implementation; arbitrary JSON serializer output is not equivalent.

Worked encoding examples, with each cell showing literal JSON text:

| Input | Canonical output |
| --- | --- |
| `{"b":0, "a":1}` | `{"a":1,"b":0}` |
| `"a\/b"` | `"a/b"` |
| `"\u000A"` | `"\n"` |
| `"\u00E9"` | `"\u00e9"` |
| `"\uD83D\uDE00"` | `"\ud83d\ude00"` |
| `"\uD800"` | Rejected unpaired surrogate |

These small examples specify encoding only. They are not complete view objects
and have not been exercised against a production parser.

Paths are manifest-relative strings accepted by the existing conservative
`validate_view_names` prototype. Preserve the exact path spelling; its returned
lowercase key is only a collision key. Sort file/effect arrays by that key and
reject unsorted arrays. Existing limits (20,000 paths, 1,024 characters per path,
64 components, 120 characters per component) remain. Check collisions within the view and within the effect paths separately, including
file/directory prefix collisions. An effect references its view file by exact
original path spelling, not only a matching collision key. This matching pair is
one planned file, not a duplicate namespace entry.
These rules do not establish native Windows path identity or Unicode support.

## Generated view object

All fields below are required; no additional fields are accepted.

| Field | Proposed value |
| --- | --- |
| `schema` | Literal `generated-files-v1` |
| `source` | Object with `object_format`, `commit`, `tree`, `lock_sha256` |
| `mapping` | Literal `regular-files-only-v1` |
| `files` | Nonempty ordered array of file objects |

`object_format` is `sha1` or `sha256`; commit, tree and blob IDs are lowercase
hexadecimal of respectively 40 or 64 characters under that format. `lock_sha256`
is always 64 lowercase hexadecimal characters. IDs and hashes are declarations
until an independent source verifier checks them against canonical source bytes.

Each file object has exactly `path`, `size`, `sha256`, and `origin`. `size` is an
integer from zero through 2^53−1; `sha256` is a payload-byte digest, not the Git
blob ID. The consumer must also impose independently reviewed aggregate resource
limits before materializing payloads; this proposal does not authorize enormous
allocations merely because a length is representable.

`origin` has exactly `path`, `blob`, and `mode`. For this first contract, `mode`
is `100644` and the source must be a regular, non-executable file whose bytes
are unchanged in the view. The source and output paths may differ, but both use
the conservative manifest path syntax. Link flattening, generated wrappers,
executable-mode conversion and other transformations are outside this initial
proposal. Reject them instead of dropping their provenance. Supporting them
requires a separately versioned mapping and reviewed provenance rules.

The view digest covers the entire generated-view object. A regular file view
is deliberately not a canonical source tree: it cannot prove Git link/mode
equivalence or permission to execute its contents.

## Approval plan object

| Required field | Proposed value |
| --- | --- |
| `schema` | Literal `installation-plan-proposal-v1` |
| `view_sha256` | Digest of the complete view object |
| `destination_display` | Nonempty local display string, never a path-authority token |
| `destination_binding` | Literal `unqualified` in this proposal |
| `effects` | Nonempty ordered array of effect objects |
| `activation` | Literal `none` |
| `recovery` | Literal `unqualified` |

The literal unqualified fields deliberately prevent this wire proposal from
being confused with an executable or approvable native plan. A production plan
requires a later reviewed version defining native identity/custody and recovery
bindings. An arbitrary identity string, copied hash, journal or syntactically
valid plan cannot supply those proofs. Do not solicit installation approval for
this proposal format.

Each effect has exactly `action`, `path`, `before`, and `after`. In this initial
proposal, `action` is the literal `create`, `before` is null, and `after` is the
corresponding view file's SHA-256. Every view file has exactly one effect and every
effect refers to exactly one view file, with identical original path spelling.
All digests are 64 lowercase hexadecimal characters. Duplicate effects refuse.

Replace and delete operations are outside this format and refuse. Their future
contract needs an independently established managed baseline, native object
identity, and protection for edited or unmanaged objects. Unmanaged collision
detection must precede opening private content. This data-only format cannot
establish absence of such collisions.

The plan digest covers every field above and is distinct from the view digest.
Neither digest is a signature, authorization token, session binding, or replay
defense. A future consent controller must bind its locally verified actor and
single attempt to the final production plan bytes, never this proposal format.

## Rejection examples for the later pure parser seam

These are test requirements, not executed tests or native safety evidence.

| Mutation to a valid create-only proposal | Required result |
| --- | --- |
| Duplicate `schema`, extra `approved`, or version 2 | Reject the entire input |
| Boolean/fractional size or malformed object ID | Reject |
| `A.txt` plus `a.txt`, `a` plus `a/b`, or `NUL.txt` | Reject |
| Source mode `120000`/`100755` or undocumented mapping | Reject |
| Changed payload digest without matching effect digest | Reject |
| Duplicate effect, missing view file effect, or extra effect path | Reject |
| Reordered file/effect array | Reject; do not repair silently |
| Replace/delete or claimed destination/recovery qualification | Reject |
| Same parsed content with changed view digest | Reject |

A valid parse must yield only validated proposal data. It must never invoke
filesystem, network, process, consent, journal, locking or installation APIs.
Native confinement, authentic recovery, competing writers, UI trust and replay
require different qualified seams; passing this parser cannot satisfy them.
