"""Single read-only SDK query on an independently authorized retained file.

No DLL activation, path open, payload access, handle close or enumeration retry.
Recording readers provide simulated evidence only; this module grants no scope.
"""
import ctypes as c
from dataclasses import dataclass, field

from windows_handle_observer import require_context
from windows_pair_observer import require_ordinary_facts
from windows_streams import MAX_BUFFER, assess_file_stream_buffer, StreamError


class StreamQueryError(ValueError):
    def __init__(self, stage, code=None):
        super().__init__('stream_observation_refused')
        self.stage = stage if type(stage) is str and stage in {
            'scope', 'cleanup', 'query', 'changed', 'capture'} else 'query'
        self.code = code if type(code) is int and 0 <= code <= 0xFFFFFFFF else None


@dataclass(frozen=True)
class StreamSnapshot:
    status: str = field(default='observed-default-stream-buffer', init=False)
    evidence_scope: str = field(default='retained-file-stream-partial-snapshot', init=False)
    confinement_verified: bool = field(default=False, init=False)
    filesystem_verified: bool = field(default=False, init=False)
    native_action_admitted: bool = field(default=False, init=False)
    installation_admitted: bool = field(default=False, init=False)
    activation_admitted: bool = field(default=False, init=False)


def _cleanup(reader):
    if type(reader.cleanup_errors) not in (list, tuple) or reader.cleanup_errors:
        raise StreamQueryError('cleanup')


def observe_file_streams(reader, handle, *, expected_facts):
    """One bounded FileStreamInfo query, never a filesystem/race certificate.

    Caller must own scope and preserve borrowed-handle lifetime. Expected facts
    are caller claims. Stream buffers may change between snapshots; endpoint
    equality does not establish race exclusion or complete security metadata.
    """
    if type(handle) is not int or not 0 < handle < 2**64 - 1:
        raise StreamQueryError('scope')
    require_ordinary_facts(expected_facts)
    if expected_facts.directory:
        raise StreamQueryError('scope')
    _cleanup(reader)
    context = reader.context()
    _cleanup(reader)
    require_context(context)
    before = reader.metadata(handle)
    _cleanup(reader)
    require_ordinary_facts(before)
    if before != expected_facts:
        raise StreamQueryError('changed')
    buffer = c.create_string_buffer(MAX_BUFFER)  # Entire capacity starts zeroed.
    if c.addressof(buffer) % 8:
        raise StreamQueryError('capture')
    c.set_last_error(0)
    ok = reader.kernel.GetFileInformationByHandleEx(handle, 7, buffer, MAX_BUFFER)
    code = c.get_last_error()
    _cleanup(reader)
    # EOF/no streams, insufficient buffers and all other nonzero errors refuse,
    # even paired with BOOL success. No resizing, alternate query or fallback.
    if not ok or code:
        raise StreamQueryError('query', code)
    raw = bytes(buffer.raw)
    after = reader.metadata(handle)
    _cleanup(reader)
    require_ordinary_facts(after)
    after_context = reader.context()
    _cleanup(reader)
    require_context(after_context)
    if before != after or context != after_context:
        raise StreamQueryError('changed')
    try:
        assess_file_stream_buffer(raw, expected_size=before.size)
    except StreamError:
        raise StreamQueryError('capture') from None
    return StreamSnapshot()
