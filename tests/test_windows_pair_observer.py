"""Recorded retained-handle pairs, never native edge qualification."""
from dataclasses import replace
import unittest

from test_windows_handle_observer import RecordingReader
from windows_handle_observer import HandleFacts, ObserverError
from windows_pair_observer import observe_retained_pair
from test_windows_descriptors import USER, OTHER, ace, descriptor
from windows_handle_observer import ReaderContext

PARENT = HandleFacts(b'V' * 8, b'P' * 16, 0x10, 1, 0, 100, True, False)
CHILD = HandleFacts(b'V' * 8, b'C' * 16, 0x20, 1, 21, 101, False, False)


class PairReader(RecordingReader):
    def __init__(self):
        super().__init__()
        self.by_handle = {123: [PARENT, PARENT], 124: [CHILD, CHILD]}

    def metadata(self, handle):
        self.calls.append(('metadata', handle))
        return self.by_handle[handle].pop(0)

    def security(self, handle):
        self.calls.append(('security', handle))
        return self.raw


def observe(reader, **overrides):
    args = dict(parent_handle=123, child_handle=124,
                expected_parent=PARENT, expected_child=CHILD)
    args.update(overrides)
    return observe_retained_pair(reader, **args)


class PairObserverTests(unittest.TestCase):
    def test_matching_pair_reports_partial_snapshot_without_edge_admission(self):
        reader = PairReader()
        result = observe(reader)
        self.assertEqual(result.status, 'observed')
        self.assertEqual(len(result.descriptors), 2)
        self.assertFalse(result.confinement_verified)
        self.assertFalse(result.installation_admitted)
        self.assertIn('namespace_relation_unverified', result.blockers)
        self.assertIn('race_exclusion_unverified', result.blockers)
        self.assertEqual(result.evidence_scope, 'retained-pair-partial-snapshot')

    def test_invalid_or_aliased_expected_objects_refuse_before_any_query(self):
        cases = [dict(parent_handle=True), dict(child_handle=123),
                 dict(expected_parent=CHILD), dict(expected_child=True),
                 dict(expected_child=replace(CHILD, volume=b'X' * 8)),
                 dict(expected_child=replace(CHILD, object_id=PARENT.object_id)),
                 dict(expected_child=replace(CHILD, attributes=0x400)),
                 dict(expected_child=replace(CHILD, delete_pending=True)),
                 dict(expected_parent=replace(PARENT, links=2)),
                 dict(expected_child=replace(CHILD, size=True))]
        for overrides in cases:
            reader = PairReader()
            with self.subTest(overrides=overrides), self.assertRaises(ObserverError):
                observe(reader, **overrides)
            self.assertEqual(reader.calls, [])

    def test_changed_or_malformed_observed_identity_stops_before_security(self):
        for handle, value in ((123, replace(PARENT, object_id=b'X' * 16)),
                              (124, replace(CHILD, volume=b'X' * 8)),
                              (124, replace(CHILD, size=True)),
                              (123, replace(PARENT, directory=False))):
            reader = PairReader()
            reader.by_handle[handle][0] = value
            with self.subTest(handle=handle), self.assertRaises(ObserverError):
                observe(reader)
            self.assertFalse(any(isinstance(call, tuple) and call[0] == 'security'
                                 for call in reader.calls))

    def test_parent_or_child_change_during_capture_refuses(self):
        for handle, value in ((123, replace(PARENT, object_id=b'X' * 16)),
                              (123, replace(PARENT, change_time=102)),
                              (124, replace(CHILD, object_id=b'X' * 16)),
                              (124, replace(CHILD, delete_pending=True))):
            reader = PairReader()
            reader.by_handle[handle][1] = value
            with self.subTest(handle=handle), self.assertRaises(ObserverError):
                observe(reader)

    def test_descriptor_denial_has_no_peer_query_fallback_or_handle_close(self):
        reader = PairReader()
        def deny(handle):
            reader.calls.append(('denied_security', handle))
            raise ObserverError('GetSecurityInfo', 5)
        reader.security = deny
        with self.assertRaises(ObserverError) as error:
            observe(reader)
        self.assertEqual(error.exception.code, 5)
        self.assertEqual(reader.calls[-1], ('denied_security', 123))
        self.assertNotIn(('security', 124), reader.calls)
        # Reader deliberately has no close/open operation; both handles borrowed.

    def test_cleanup_failure_stops_before_further_port_reads(self):
        reader = PairReader()
        def security(handle):
            reader.calls.append(('security', handle))
            reader.cleanup_errors.append(('LocalFree', 5))
            return reader.raw
        reader.security = security
        with self.assertRaises(ObserverError) as error:
            observe(reader)
        self.assertEqual(error.exception.stage, 'native_cleanup_failure')
        self.assertEqual(reader.calls[-1], ('security', 123))

    def test_untrusted_parent_or_child_cannot_be_masked_by_trusted_peer(self):
        for unsafe in (123, 124):
            reader = PairReader()
            def security(handle):
                return descriptor([ace(OTHER)]) if handle == unsafe else descriptor()
            reader.security = security
            result = observe(reader)
            self.assertEqual(result.status, 'profile-refused')
            self.assertIn('untrusted_trustee', result.descriptors[unsafe - 123][1].issues)
            self.assertFalse(result.installation_admitted)

    def test_context_change_or_elevation_cannot_return_a_snapshot(self):
        for after in (ReaderContext(USER, True, False), ReaderContext(USER, False, True),
                      ReaderContext(OTHER, False, False)):
            reader = PairReader()
            contexts = iter((reader.context_value, after))
            reader.context = lambda: next(contexts)
            with self.subTest(after=after), self.assertRaises(ObserverError):
                observe(reader)

    def test_stable_pair_never_attests_relationship_lifetime_or_race_exclusion(self):
        result = observe(PairReader())
        self.assertIn('root_provenance_unverified', result.blockers)
        self.assertIn('handle_lifetime_custody_unverified', result.blockers)
        self.assertIn('security_completeness_unverified', result.blockers)
        self.assertFalse(result.filesystem_verified)
        self.assertFalse(result.activation_admitted)
        for identity in (PARENT.object_id.hex(), CHILD.object_id.hex(), USER.hex()):
            self.assertNotIn(identity, repr(result))

    def test_directory_child_uses_directory_inheritance_profile(self):
        reader = PairReader()
        child = replace(CHILD, attributes=0x10, directory=True, size=0)
        reader.by_handle[124] = [child, child]
        reader.raw = descriptor([ace(USER, flags=11)])
        result = observe(reader, expected_child=child)
        self.assertEqual(result.status, 'observed')
        self.assertFalse(result.descriptors[1][1].aces[0].applies_here)
        self.assertFalse(result.confinement_verified)

    def test_preexisting_cleanup_failure_queries_neither_handle(self):
        reader = PairReader()
        reader.cleanup_errors = [('CloseHandle', 5)]
        with self.assertRaises(ObserverError):
            observe(reader)
        self.assertEqual(reader.calls, [])


if __name__ == '__main__':
    unittest.main()
