"""Bounded FILE_STREAM_INFO bytes, regular-file default-stream profile only.

No native query, path/payload access or security change. A caller's supplied
buffer cannot establish successful/complete enumeration or object continuity.
"""
from dataclasses import dataclass, field
import struct

DEFAULT_NAME = b':\x00:\x00$\x00D\x00A\x00T\x00A\x00'
MAX_BUFFER = 65536


class StreamError(ValueError):
    """Fixed refusal codes only; no stream names, sizes or payload echoed."""


@dataclass(frozen=True)
class StreamAssessment:
    status: str = field(default='captured-default-stream-only', init=False)
    evidence_scope: str = field(default='captured-file-stream-buffer-only', init=False)
    filesystem_verified: bool = field(default=False, init=False)
    native_action_admitted: bool = field(default=False, init=False)
    installation_admitted: bool = field(default=False, init=False)


def assess_file_stream_buffer(raw, *, expected_size):
    """Refuse everything except one supported unnamed regular-file data stream.

    Expected size is an independent caller claim, not authenticated payload proof.
    Native callers must separately establish successful complete FileStreamInfo
    query on an authorized retained ordinary file handle; failure/EOF/overflow
    cannot be interpreted as default-only. No such native adapter is wired here.
    Directory streams and other NTFS attribute types are outside this profile.
    """
    if (type(raw) is not bytes or not 38 <= len(raw) <= MAX_BUFFER
            or type(expected_size) is not int or not 0 <= expected_size < 2**63):
        raise StreamError('invalid_capture')
    following, name_bytes, size, allocated = struct.unpack_from('<IIqq', raw)
    # Any chain is outside this single-stream profile, even duplicate defaults.
    if following:
        raise StreamError('additional_or_unsupported_streams')
    if name_bytes != len(DEFAULT_NAME) or raw[24:38] != DEFAULT_NAME:
        raise StreamError('unsupported_stream_name')
    if size != expected_size or size < 0 or allocated < 0:
        raise StreamError('stream_metadata_mismatch')
    if any(raw[38:]):
        raise StreamError('unsupported_capture_tail')
    return StreamAssessment()
