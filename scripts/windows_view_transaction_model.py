"""Pure in-memory transaction model for synthetic fault injection.

No filesystem access, Windows security checks, installer actions, or durable recovery.
Digest and identity strings are untrusted test tokens, not verified evidence.
"""
from dataclasses import dataclass

STATES = ("proposed", "verified", "staged", "committed", "aborted")


class Refused(ValueError):
    pass


@dataclass(frozen=True)
class SimulatedTransaction:
    state: str = "proposed"
    source_digest: str = ""
    staged_digest: str = ""
    destination_identity: str = ""

    def advance(self, action, *, digest="", identity="", fault=False):
        if self.state not in STATES or self.state in ("committed", "aborted"):
            raise Refused("terminal-or-unknown-state")
        if fault:
            return SimulatedTransaction("aborted", self.source_digest,
                                        self.staged_digest, self.destination_identity)
        if self.state == "proposed" and action == "verify" and digest:
            return SimulatedTransaction("verified", digest)
        if self.state == "verified" and action == "stage" and digest == self.source_digest and identity:
            return SimulatedTransaction("staged", self.source_digest, digest, identity)
        if self.state == "staged" and action == "commit" and digest == self.staged_digest and identity == self.destination_identity:
            return SimulatedTransaction("committed", self.source_digest, digest, identity)
        raise Refused("unverified-transition")


def simulate_bytes(payload, *, destination_identity, altered_stage=None, altered_identity=None, fault_at=None):
    """Exercise transitions with SHA-256 computed from caller-provided synthetic bytes.

    This proves only model-level digest comparisons, not secure file reads or writes.
    """
    import hashlib
    if not isinstance(payload, bytes) or not isinstance(destination_identity, str) or not destination_identity:
        raise Refused("invalid-synthetic-input")
    if fault_at not in (None, "verify", "stage", "commit"):
        raise Refused("invalid-fault-point")
    digest = hashlib.sha256(payload).hexdigest()
    tx = SimulatedTransaction()
    if fault_at == "verify":
        return tx.advance("verify", fault=True)
    tx = tx.advance("verify", digest=digest)
    if fault_at == "stage":
        return tx.advance("stage", fault=True)
    staged = payload if altered_stage is None else altered_stage
    if not isinstance(staged, bytes):
        raise Refused("invalid-staged-bytes")
    staged_digest = hashlib.sha256(staged).hexdigest()
    tx = tx.advance("stage", digest=staged_digest, identity=destination_identity)
    if fault_at == "commit":
        return tx.advance("commit", fault=True)
    return tx.advance("commit", digest=staged_digest,
                      identity=destination_identity if altered_identity is None else altered_identity)
