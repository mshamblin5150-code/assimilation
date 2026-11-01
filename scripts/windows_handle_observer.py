"""Borrowed-handle snapshot policy. No path opens, setters or payload reads."""
from dataclasses import dataclass, field

from windows_descriptors import assess_descriptor, DescriptorError, SYSTEM_SID, ADMINISTRATORS_SID

FAILURE_STAGES = frozenset({
    'invalid_context', 'elevated_or_impersonating_context', 'unsupported_process_user',
    'invalid_handle_metadata', 'unsupported_fixture_object', 'invalid_observation_scope',
    'observation_changed', 'native_cleanup_failure', 'unsupported_captured_descriptor',
    'invalid_token_buffer', 'unsupported_native_runtime', 'load_system_dll',
    'OpenThreadToken', 'OpenProcessToken', 'GetTokenInformation',
    'GetFileInformationByHandleEx', 'not_disk_handle', 'GetSecurityInfo',
    'invalid_descriptor_buffer', 'GetSecurityDescriptorControl',
    'unsupported_descriptor_format', 'CloseHandle', 'LocalFree', 'invalid_reader_state'})
DESCRIPTOR_REASONS = frozenset({'descriptor_bound', 'unsupported_object_kind', 'invalid_user_sid',
    'sid_bounds', 'unsupported_sid', 'unsupported_descriptor_control', 'unsupported_descriptor_offset',
    'acl_bounds', 'unsupported_acl', 'overlapping_descriptor_regions', 'unrecognized_descriptor_bytes',
    'ace_bounds', 'unsupported_ace', 'unsupported_ace_flags', 'unsupported_ace_payload', 'unrecognized_acl_bytes'})


class ObserverError(ValueError):
    """Fixed stages/codes only; never echo a native buffer or account data."""
    def __init__(self, stage, code=None, *, detail=None):
        super().__init__('native_observation_refused')
        self.stage = stage if type(stage) is str and stage in FAILURE_STAGES else 'unclassified_failure'
        self.code = code if type(code) is int and 0 <= code <= 0xFFFFFFFF else None
        self.detail = detail if type(detail) is str and detail in DESCRIPTOR_REASONS else None


@dataclass(frozen=True)
class ReaderContext:
    user_sid: bytes = field(repr=False)
    elevated: bool
    thread_token_present: bool


@dataclass(frozen=True)
class HandleFacts:
    volume: bytes = field(repr=False)
    object_id: bytes = field(repr=False)
    attributes: int
    links: int
    size: int
    change_time: int
    directory: bool
    delete_pending: bool


@dataclass(frozen=True)
class HandleSnapshot:
    status: str
    profile_match: bool
    owner_class: str
    issues: tuple
    aces: tuple
    size: int
    attributes: int
    evidence_scope: str = field(default='borrowed-handle-partial-snapshot', init=False)
    confinement_verified: bool = field(default=False, init=False)
    filesystem_verified: bool = field(default=False, init=False)
    installation_admitted: bool = field(default=False, init=False)
    activation_admitted: bool = field(default=False, init=False)


def require_context(value):
    if (type(value) is not ReaderContext or type(value.user_sid) is not bytes
            or not 12 <= len(value.user_sid) <= 68 or value.user_sid[0] != 1
            or not 1 <= value.user_sid[1] <= 15 or len(value.user_sid) != 8 + 4 * value.user_sid[1]
            or type(value.elevated) is not bool or type(value.thread_token_present) is not bool):
        raise ObserverError('invalid_context')
    if value.elevated or value.thread_token_present:
        raise ObserverError('elevated_or_impersonating_context')
    if value.user_sid in (SYSTEM_SID, ADMINISTRATORS_SID):
        raise ObserverError('unsupported_process_user')


def _require_facts(value, expected_size):
    if (type(value) is not HandleFacts or type(value.volume) is not bytes or len(value.volume) != 8
            or type(value.object_id) is not bytes or len(value.object_id) != 16
            or any(type(number) is not int or not 0 <= number <= 0xFFFFFFFF
                   for number in (value.attributes, value.links))
            or type(value.size) is not int or value.size != expected_size
            or type(value.change_time) is not int or not 0 <= value.change_time < 2**63
            or type(value.directory) is not bool or type(value.delete_pending) is not bool):
        raise ObserverError('invalid_handle_metadata')
    if (value.directory or value.delete_pending or value.links != 1
            or value.attributes & ~0xA7
            or value.attributes & 0x80 and value.attributes != 0x80):
        raise ObserverError('unsupported_fixture_object')


def observe_borrowed_handle(reader, handle, *, expected_size):
    """Use only a scope-authorized handle; this function does not grant scope.

    Reader is a system boundary: recording readers are simulations. Native
    evidence additionally needs verified reader source/runtime and actual calls.
    """
    if (type(handle) is not int or handle <= 0 or type(expected_size) is not int
            or not 0 <= expected_size <= 4096):
        raise ObserverError('invalid_observation_scope')
    _require_cleanup(reader)
    before_context = reader.context()
    _require_cleanup(reader)
    require_context(before_context)
    before = reader.metadata(handle)
    _require_cleanup(reader)
    _require_facts(before, expected_size)
    raw = reader.security(handle)
    _require_cleanup(reader)
    after = reader.metadata(handle)
    _require_cleanup(reader)
    _require_facts(after, expected_size)
    after_context = reader.context()
    _require_cleanup(reader)
    require_context(after_context)
    if before != after or before_context != after_context:
        raise ObserverError('observation_changed')
    try:
        assessment = assess_descriptor(raw, kind='file', expected_user_sid=before_context.user_sid)
    except DescriptorError as error:
        raise ObserverError('unsupported_captured_descriptor', detail=str(error)) from None
    return HandleSnapshot('observed' if assessment.profile_match else 'profile-refused',
                          assessment.profile_match, assessment.owner_class,
                          assessment.issues, assessment.aces, before.size, before.attributes)


def _require_cleanup(reader):
    if type(reader.cleanup_errors) not in (tuple, list):
        raise ObserverError('invalid_reader_state')
    if reader.cleanup_errors:
        raise ObserverError('native_cleanup_failure')
