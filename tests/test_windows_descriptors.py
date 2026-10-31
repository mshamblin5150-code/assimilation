"""Synthetic descriptor bytes, not native ACL or identity qualification."""
from pathlib import Path
import struct
import sys
import unittest
from contextlib import ExitStack
from unittest.mock import patch
import os
import socket
import subprocess

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from windows_descriptors import assess_descriptor, DescriptorError

USER = bytes.fromhex('010200000000000515000000e9030000')
ADMINS = bytes.fromhex('01020000000000052000000020020000')
SYSTEM = bytes.fromhex('010100000000000512000000')
OTHER = bytes.fromhex('010100000000000100000000')


def ace(sid=USER, mask=0x00120089, flags=0, kind=0):
    return struct.pack('<BBHI', kind, flags, 8 + len(sid), mask) + sid


def descriptor(aces=None, owner=USER, group=ADMINS, control=0x8004, revision=2):
    entries = [ace()] if aces is None else aces
    acl = struct.pack('<BBHHH', revision, 0, 8 + sum(map(len, entries)), len(entries), 0)
    acl += b''.join(entries)
    return (struct.pack('<BBHIIII', 1, 0, control, 20, 20 + len(owner), 0,
                        20 + len(owner) + len(group)) + owner + group + acl)


class WindowsDescriptorTests(unittest.TestCase):
    def test_current_user_owned_allow_only_descriptor_stays_unqualified(self):
        result = assess_descriptor(descriptor(), kind='file', expected_user_sid=USER)
        self.assertTrue(result.profile_match)
        self.assertEqual(result.owner_class, 'current-user')
        self.assertEqual(result.aces[0].trustee_class, 'current-user')
        self.assertEqual(result.aces[0].mapped_mask, 0x00120089)
        self.assertEqual(result.evidence_scope, 'captured-descriptor-only')
        self.assertFalse(result.filesystem_verified)
        self.assertFalse(result.native_action_admitted)

    def test_generic_rights_are_mapped_without_reordering_trustees(self):
        raw = descriptor([ace(SYSTEM, 0x80000000), ace(USER, 0x40000000),
                          ace(ADMINS, 0x20000000), ace(USER, 0x10000000)])
        result = assess_descriptor(raw, kind='file', expected_user_sid=USER)
        self.assertTrue(result.profile_match)
        self.assertEqual([entry.trustee_class for entry in result.aces],
                         ['system', 'current-user', 'administrators', 'current-user'])
        self.assertEqual([entry.mapped_mask for entry in result.aces],
                         [0x00120089, 0x00120116, 0x001200A0, 0x001F01FF])

    def test_owner_and_trustee_policy_violations_are_reported_without_identities(self):
        result = assess_descriptor(descriptor([ace(OTHER)], owner=ADMINS),
                                   kind='file', expected_user_sid=USER)
        self.assertFalse(result.profile_match)
        self.assertEqual(result.owner_class, 'administrators')
        self.assertEqual(result.issues, ('owner_not_current_user', 'untrusted_trustee'))
        self.assertNotIn(USER.hex(), repr(result))
        self.assertNotIn(OTHER.hex(), repr(result))

    def test_inheritance_is_kind_specific_and_inherit_only_does_not_apply_here(self):
        inherited = assess_descriptor(descriptor([ace(flags=0x10)]),
                                       kind='file', expected_user_sid=USER)
        self.assertTrue(inherited.aces[0].applies_here)
        child_only = assess_descriptor(descriptor([ace(flags=0x0B)]),
                                        kind='directory', expected_user_sid=USER)
        self.assertFalse(child_only.aces[0].applies_here)
        for kind, flags in (('file', 1), ('file', 8), ('directory', 8),
                            ('directory', 4), ('directory', 0x40)):
            with self.subTest(kind=kind, flags=flags), self.assertRaises(DescriptorError):
                assess_descriptor(descriptor([ace(flags=flags)]), kind=kind, expected_user_sid=USER)

    def test_nonallow_and_opaque_ace_forms_and_unknown_rights_refuse(self):
        for entry in (ace(kind=1), ace(kind=5), ace(kind=9), ace(kind=0x11),
                      ace(mask=0x02000000), ace(mask=0x00000200)):
            with self.subTest(entry=entry), self.assertRaises(DescriptorError):
                assess_descriptor(descriptor([entry]), kind='file', expected_user_sid=USER)

    def test_null_empty_unsupported_control_or_resource_metadata_refuses(self):
        for raw in (descriptor([]), descriptor(control=0x8000), descriptor(control=0xC004),
                    descriptor(control=0x8014), descriptor(control=0x8104)):
            with self.subTest(raw=raw[:20]), self.assertRaises(DescriptorError):
                assess_descriptor(raw, kind='file', expected_user_sid=USER)
        raw = bytearray(descriptor())
        raw[1] = 1
        with self.assertRaises(DescriptorError):
            assess_descriptor(bytes(raw), kind='file', expected_user_sid=USER)

    def test_overlapping_unaligned_missing_and_out_of_bounds_offsets_refuse(self):
        for field, offset in ((4, 0), (8, 20), (8, 21), (12, 20), (16, 0), (16, 0xFFFFFFFC)):
            raw = bytearray(descriptor())
            struct.pack_into('<I', raw, field, offset)
            with self.subTest(field=field, offset=offset), self.assertRaises(DescriptorError):
                assess_descriptor(bytes(raw), kind='file', expected_user_sid=USER)

    def test_truncated_size_count_sid_and_unknown_tail_refuse_with_safe_errors(self):
        raw = descriptor()
        for size in range(len(raw)):
            with self.subTest(size=size), self.assertRaises(DescriptorError):
                assess_descriptor(raw[:size], kind='file', expected_user_sid=USER)
        for changed in (raw + b'synthetic-private-marker', raw + bytes(131073),
                        descriptor([ace()] * 1025)):
            with self.assertRaises(DescriptorError) as error:
                assess_descriptor(changed, kind='file', expected_user_sid=USER)
            self.assertNotIn('synthetic-private', str(error.exception))
        for index, value in ((20, 0), (21, 16)):
            changed = bytearray(raw)
            changed[index] = value
            with self.assertRaises(DescriptorError):
                assess_descriptor(bytes(changed), kind='file', expected_user_sid=USER)

    def test_acl_revisions_two_and_four_are_supported_without_general_acl_claim(self):
        result = assess_descriptor(descriptor(revision=4), kind='file', expected_user_sid=USER)
        self.assertTrue(result.profile_match)
        self.assertFalse(result.native_action_admitted)
        with self.assertRaises(DescriptorError):
            assess_descriptor(descriptor(revision=3), kind='file', expected_user_sid=USER)

    def test_captured_byte_assessment_makes_no_native_or_filesystem_calls(self):
        raw = descriptor()
        with ExitStack() as stack:
            controls = [stack.enter_context(patch(name, side_effect=AssertionError('boundary forbidden')))
                        for name in ('builtins.open', 'os.stat', 'os.listdir', 'os.scandir',
                                     'os.mkdir', 'os.rename', 'socket.socket', 'subprocess.Popen')]
            for control in controls:
                with self.assertRaises(AssertionError):
                    control('synthetic-no-operation')
            result = assess_descriptor(raw, kind='file', expected_user_sid=USER)
        self.assertTrue(result.profile_match)


if __name__ == '__main__':
    unittest.main()
