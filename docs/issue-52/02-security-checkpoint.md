# Drone 02: independent Security Checkpoint 1

Reviewer: native task `/root/drone02_security`, separate from Drone 01 and coordinator. Decision owner: Matt Shamblin.

**Verdict: HOLD for acoustic implementation.** Review completed against main `228038a22e07e93ef99332e793e7abb5d1942e7e`, all 11 pre-fleet Issue #52 comments, and draft PR #53 head `df718a03bc9e97c134eaab510e5f6fd193f11108`, its complete 81-line added-file diff. Later reviewed Drone 01's candidate/protocol and independently inspected pinned SpeechBrain code/configuration. This is review evidence, not a security certification.

## Blocking findings

| Finding | Required correction before acoustic execution |
| --- | --- |
| Incomplete supply chain | Freeze Python/framework/audio/transitive dependencies and every weight/config artifact; expected hashes plus actual acquired-byte verification. |
| Mutable nested acquisition and executable configuration | Replace remote paths with reviewed immutable local paths; audit YAML constructors and checkpoint loader; prevent implicit network/remote code. |
| Unspecified synthetic provenance | Name and review the generator, artificial voice provenance and exact terms. Public human recordings are outside current synthetic-only scope. |
| Unfrozen benchmark | Specify enrollment aggregation, calibration/held-out lists, overlap, exact attack counts/generation, channel conditions, errors and denominators before evaluation. |
| Incomplete lifecycle | Fix expiry and inventory workspace, caches, temporary/crash outputs, snapshots and cleanup evidence. Seven-day maximum is a proposal, not an implemented control. |

The [pinned scorer](https://github.com/speechbrain/speechbrain/blob/c0241278f93ef02cd5191f03caf4e5f8e1292bf6/speechbrain/inference/speaker.py), [model card](https://huggingface.co/speechbrain/spkrec-ecapa-voxceleb/blob/0f99f2d0ebe89ac095bcc5903c4dd8f72b367286/README.md) and [YAML](https://huggingface.co/speechbrain/spkrec-ecapa-voxceleb/blob/0f99f2d0ebe89ac095bcc5903c4dd8f72b367286/hyperparams.yaml) support candidate feasibility but not liveness. [PyTorch loader documentation](https://docs.pytorch.org/docs/2.15/generated/torch.load.html) warns about untrusted serialized inputs; this warrants loader review, not a claim that this checkpoint is malicious.

## Architecture challenge and required corrections

1. **Identity:** NIST SP800-63B-4 §3.2.3.2 excludes voice biometric comparison from its authentication requirements. This is a conformity boundary, not a prohibition on supplemental research. Keep uncertain speaker similarity separate from independently authenticated identity. [NIST](https://pages.nist.gov/800-63-4/sp800-63b.html).
2. **Replay and synthesis:** A random spoken challenge is not proven liveness; synthesis may answer a fresh challenge. Separate replay, generated speech and zero-effort impostors. Include matcher-accepted/authorizer-denied cases. [ASVspoof](https://www.asvspoof.org/index2021.html), [primary outside-dataset study](https://www.isca-archive.org/asvspoof_2024/falez24_asvspoof.html).
3. **Host trust:** Another person's environment may forge screens, transcripts or agent outputs. A receiving host must independently validate trusted evidence and preserve the host owner's permissions. Captain identity never overrides host ownership.
4. **Gateway contract:** Define issuer/key trust, allowed algorithms, subject, audience, expiry, nonce/replay handling, auth method and request/action binding; test substitution, revocation and stale evidence. RFC8725 supports algorithm/issuer/audience validation for JWT designs; token format remains undecided. These are future requirements, not deployment permission. [RFC8725](https://www.rfc-editor.org/rfc/rfc8725.html).
5. **Passkeys:** Verify challenge, origin, RP binding, signature and applicable user-verification flags. A generic passkey does not automatically establish device binding or natural-person identity; initial account binding also needs a trusted process. [WebAuthn](https://www.w3.org/TR/webauthn-3/#sctn-verifying-assertion).
6. **Drive:** Encrypt before upload with separately controlled keys. Ordinary service-managed encryption is not D-52-09 key separation. Workspace client-side encryption has account/admin prerequisites, unverified here. Design key custody/recovery, restricted access, plaintext cache controls, metadata and revisions. Visiting agents should request gateway verification, not receive templates or decryption keys. [Google documentation](https://support.google.com/drive/answer/10519333?hl=en).
7. **Revocation:** Revoke access/assertions/template versions; copied biometrics cannot be made secret again. Enrollment changes never remove the independent authenticator requirement. Drive trash is not immediate permanent deletion and sharing/revision/backup effects require explicit lifecycle treatment. [Google deletion semantics](https://developers.google.com/workspace/drive/api/guides/delete).

Threat coverage also includes enrollment poisoning, overlapping/background speakers, transcription corruption, stolen sessions, query abuse and credential isolation. Future enrollment must have trusted provenance/consent, authenticated subject binding and reviewed recovery. Keep signing keys, Drive OAuth credentials and decryption keys outside agent execution boundaries. Rate limiting and response minimization belong in any future gateway design; nothing was provisioned here.

## Narrow plan review

The reviewer separately returned **PASS for preparing/publishing the exact model-free simulator plan** in [REPORT.md](REPORT.md). The test-only authentication stub and fixture fields must be visibly synthetic. Its only positive result is inert read-status simulation.

This PASS is for the plan alone. It does not lift acoustic Checkpoint 1 HOLD or approve code execution, gateway creation, credentials, human enrollment or deployment. No live voice, model, authentication or deletion tests occurred. No Captain participation is needed to resolve current research blockers.
