"""Read-only retained-pair protocol; never establishes a namespace edge.

Caller must separately authorize both objects and retain exclusive handle-lifetime
custody throughout. Expected facts are caller claims, not authenticated anchors.
No handle opens, closes, payload reads or setters occur in this module.
"""
from dataclasses import dataclass, field

from windows_handle_observer import HandleFacts, ObserverError, require_context
from windows_descriptors import assess_descriptor, DescriptorError


@dataclass(frozen=True)
class PairSnapshot:
    status: str
    descriptors: tuple
    evidence_scope: str = field(default='retained-pair-partial-snapshot', init=False)
    blockers: tuple = field(default=('root_provenance_unverified',
        'namespace_relation_unverified', 'handle_lifetime_custody_unverified',
        'race_exclusion_unverified', 'security_completeness_unverified'), init=False)
    confinement_verified: bool = field(default=False, init=False)
    filesystem_verified: bool = field(default=False, init=False)
    installation_admitted: bool = field(default=False, init=False)
    activation_admitted: bool = field(default=False, init=False)


def _cleanup(reader):
    if type(reader.cleanup_errors) not in (list, tuple) or reader.cleanup_errors:
        raise ObserverError('native_cleanup_failure')


def require_ordinary_facts(value):
    if (type(value) is not HandleFacts
            or type(value.volume) is not bytes or len(value.volume) != 8
            or type(value.object_id) is not bytes or len(value.object_id) != 16
            or not any(value.object_id)
            or any(type(number) is not int or not 0 <= number <= 0xFFFFFFFF
                   for number in (value.attributes, value.links))
            or type(value.size) is not int or not 0 <= value.size < 2**63
            or type(value.change_time) is not int or not 0 <= value.change_time < 2**63
            or type(value.directory) is not bool or type(value.delete_pending) is not bool):
        raise ObserverError('invalid_handle_metadata')
    allowed = 0xB7 if value.directory else 0xA7
    if (value.links != 1 or value.delete_pending or value.attributes & ~allowed
            or bool(value.attributes & 0x10) != value.directory
            or value.attributes & 0x80 and value.attributes != 0x80):
        raise ObserverError('unsupported_fixture_object')


def observe_retained_pair(reader, *, parent_handle, child_handle,
                          expected_parent, expected_child):
    """Inspect two borrowed handles without granting root/edge/action admission.

    Reader uses the existing context/metadata/security query seam. Native usage
    requires separately reviewed scope and adapter admission. Simulations provide
    no native evidence. Directory size is only an equality check, not payload size.
    """
    if (any(type(handle) is not int or not 0 < handle < 2**64 - 1
            for handle in (parent_handle, child_handle)) or parent_handle == child_handle):
        raise ObserverError('invalid_observation_scope')
    require_ordinary_facts(expected_parent)
    require_ordinary_facts(expected_child)
    if (not expected_parent.directory or expected_parent.volume != expected_child.volume
            or expected_parent.object_id == expected_child.object_id):
        raise ObserverError('invalid_observation_scope')
    _cleanup(reader)
    before_context = reader.context()
    _cleanup(reader)
    require_context(before_context)
    handles = (parent_handle, child_handle)
    expected = (expected_parent, expected_child)
    before = []
    for handle, wanted in zip(handles, expected):
        facts = reader.metadata(handle)
        _cleanup(reader)
        require_ordinary_facts(facts)
        if facts != wanted:
            raise ObserverError('observation_changed')
        before.append(facts)
    descriptors = []
    for ordinal, handle in enumerate(handles):
        raw = reader.security(handle)
        _cleanup(reader)
        try:
            assessment = assess_descriptor(raw, kind='directory' if ordinal == 0
                                           or expected_child.directory else 'file',
                                           expected_user_sid=before_context.user_sid)
        except DescriptorError as error:
            raise ObserverError('unsupported_captured_descriptor', detail=str(error)) from None
        descriptors.append((ordinal, assessment))
    for handle, prior in zip(handles, before):
        after = reader.metadata(handle)
        _cleanup(reader)
        require_ordinary_facts(after)
        if after != prior:
            raise ObserverError('observation_changed')
    after_context = reader.context()
    _cleanup(reader)
    require_context(after_context)
    if after_context != before_context:
        raise ObserverError('observation_changed')
    return PairSnapshot('observed' if all(item.profile_match for _, item in descriptors)
                        else 'profile-refused', tuple(descriptors))
