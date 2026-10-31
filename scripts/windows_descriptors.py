"""Bounded captured-byte descriptor profile; never a native access check.

No Windows calls, token lookup, path access or security setters exist here.
The private-project profile remains proposed; a match grants no authority.
"""
from dataclasses import dataclass, field
import struct

MAX_DESCRIPTOR_BYTES = 128 * 1024
MAX_ACES = 1024
SYSTEM_SID = bytes.fromhex('010100000000000512000000')
ADMINISTRATORS_SID = bytes.fromhex('01020000000000052000000020020000')


class DescriptorError(ValueError):
    """Fixed refusal codes; never include descriptor, account or SID data."""


@dataclass(frozen=True)
class AceSummary:
    trustee_class: str
    mapped_mask: int
    flags: int
    applies_here: bool


@dataclass(frozen=True)
class DescriptorAssessment:
    profile_match: bool
    owner_class: str
    aces: tuple
    issues: tuple
    evidence_scope: str = field(default='captured-descriptor-only', init=False)
    filesystem_verified: bool = field(default=False, init=False)
    native_action_admitted: bool = field(default=False, init=False)


def _sid(data, offset, limit):
    if offset < 0 or offset + 8 > limit:
        raise DescriptorError('sid_bounds')
    count = data[offset + 1]
    end = offset + 8 + 4 * count
    if data[offset] != 1 or not 1 <= count <= 15 or end > limit:
        raise DescriptorError('unsupported_sid')
    return data[offset:end], end


def _trustee(sid, user):
    if sid == user:
        return 'current-user'
    if sid == SYSTEM_SID:
        return 'system'
    if sid == ADMINISTRATORS_SID:
        return 'administrators'
    return 'other'


def assess_descriptor(raw, *, kind, expected_user_sid):
    """Assess supported captured structure and proposed ownership/trust rules.

    expected_user_sid is a caller-supplied claim, not a token observation. Neither
    a successful parse nor profile_match proves effective access or confinement.
    """
    if type(raw) is not bytes or not 20 <= len(raw) <= MAX_DESCRIPTOR_BYTES:
        raise DescriptorError('descriptor_bound')
    if type(kind) is not str or kind not in ('file', 'directory'):
        raise DescriptorError('unsupported_object_kind')
    if type(expected_user_sid) is not bytes or not 12 <= len(expected_user_sid) <= 68:
        raise DescriptorError('invalid_user_sid')
    _, user_end = _sid(expected_user_sid, 0, len(expected_user_sid))
    if user_end != len(expected_user_sid):
        raise DescriptorError('invalid_user_sid')
    revision, reserved, control, owner_at, group_at, sacl_at, dacl_at = struct.unpack_from('<BBHIIII', raw)
    if revision != 1 or reserved or control & ~0x940F or control & 0x8004 != 0x8004 or sacl_at:
        raise DescriptorError('unsupported_descriptor_control')
    if any(offset < 20 or offset % 4 for offset in (owner_at, group_at, dacl_at)):
        raise DescriptorError('unsupported_descriptor_offset')
    owner, owner_end = _sid(raw, owner_at, len(raw))
    _, group_end = _sid(raw, group_at, len(raw))
    if dacl_at + 8 > len(raw):
        raise DescriptorError('acl_bounds')
    acl_revision, pad1, acl_size, count, pad2 = struct.unpack_from('<BBHHH', raw, dacl_at)
    acl_end = dacl_at + acl_size
    if (acl_revision not in (2, 4) or pad1 or pad2 or acl_size < 8 or acl_size % 4
            or acl_end > len(raw) or not 1 <= count <= MAX_ACES):
        raise DescriptorError('unsupported_acl')
    regions = sorted(((0, 20), (owner_at, owner_end), (group_at, group_end), (dacl_at, acl_end)))
    end = 0
    for start, stop in regions:
        if start < end:
            raise DescriptorError('overlapping_descriptor_regions')
        if any(raw[end:start]):
            raise DescriptorError('unrecognized_descriptor_bytes')
        end = stop
    if any(raw[end:]):
        raise DescriptorError('unrecognized_descriptor_bytes')
    summaries = []
    cursor = dacl_at + 8
    for _ in range(count):
        if cursor + 8 > acl_end:
            raise DescriptorError('ace_bounds')
        ace_type, flags, size, mask = struct.unpack_from('<BBHI', raw, cursor)
        ace_end = cursor + size
        if ace_type != 0 or size < 20 or size % 4 or ace_end > acl_end:
            raise DescriptorError('unsupported_ace')
        if (flags & ~0x1F or (kind == 'file' and flags & 0x0F)
                or (flags & 0x0C and not flags & 0x03)):
            raise DescriptorError('unsupported_ace_flags')
        sid, sid_end = _sid(raw, cursor + 8, ace_end)
        if sid_end != ace_end or mask & ~0xF01F01FF:
            raise DescriptorError('unsupported_ace_payload')
        mapped = mask & 0x001F01FF
        for bit, rights in ((0x80000000, 0x00120089), (0x40000000, 0x00120116),
                            (0x20000000, 0x001200A0), (0x10000000, 0x001F01FF)):
            if mask & bit:
                mapped |= rights
        summaries.append(AceSummary(_trustee(sid, expected_user_sid), mapped, flags, not bool(flags & 8)))
        cursor = ace_end
    if any(raw[cursor:acl_end]):
        raise DescriptorError('unrecognized_acl_bytes')
    owner_class = _trustee(owner, expected_user_sid)
    issues = []
    if owner_class != 'current-user':
        issues.append('owner_not_current_user')
    if any(ace.trustee_class == 'other' for ace in summaries):
        issues.append('untrusted_trustee')
    return DescriptorAssessment(not issues, owner_class, tuple(summaries), tuple(issues))
