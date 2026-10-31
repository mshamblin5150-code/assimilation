"""In-memory transaction model for fault-injection tests; never touches the host filesystem.

This is a specification aid, not a native Windows installer, journal, or recovery proof.
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
