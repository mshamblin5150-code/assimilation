"""Recording reader controls are simulated, not native Windows observations."""
from pathlib import Path
import sys
import unittest
from dataclasses import replace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from windows_handle_observer import observe_borrowed_handle, ReaderContext, HandleFacts, ObserverError
from test_windows_descriptors import USER, descriptor


class RecordingReader:
    def __init__(self):
        self.calls = []
        self.cleanup_errors = []
        self.context_value = ReaderContext(USER, False, False)
        self.facts = [HandleFacts(b'V' * 8, b'F' * 16, 0x20, 1, 21, 100, False, False)] * 2
        self.raw = descriptor()

    def context(self):
        self.calls.append('context')
        return self.context_value

    def metadata(self, handle):
        self.calls.append('metadata')
        return self.facts.pop(0)

    def security(self, handle):
        self.calls.append('security')
        return self.raw


class HandleObserverTests(unittest.TestCase):
    def test_snapshot_uses_borrowed_handle_without_granting_confinement(self):
        reader = RecordingReader()
        result = observe_borrowed_handle(reader, 123, expected_size=21)
        self.assertEqual(result.status, 'observed')
        self.assertTrue(result.profile_match)
        self.assertEqual(result.owner_class, 'current-user')
        self.assertFalse(result.confinement_verified)
        self.assertFalse(result.installation_admitted)
        self.assertEqual(reader.calls, ['context', 'metadata', 'security', 'metadata', 'context'])

    def test_denial_stops_without_named_security_or_token_fallback(self):
        reader = RecordingReader()
        def denied(handle):
            reader.calls.append('security')
            raise ObserverError('GetSecurityInfo', 5)
        reader.security = denied
        with self.assertRaises(ObserverError) as error:
            observe_borrowed_handle(reader, 123, expected_size=21)
        self.assertEqual(error.exception.code, 5)
        self.assertEqual(reader.calls, ['context', 'metadata', 'security'])

    def test_elevation_impersonation_or_reparse_refuses_before_security_query(self):
        for context in (ReaderContext(USER, True, False), ReaderContext(USER, False, True)):
            reader = RecordingReader()
            reader.context_value = context
            with self.assertRaises(ObserverError):
                observe_borrowed_handle(reader, 123, expected_size=21)
            self.assertEqual(reader.calls, ['context'])
        reader = RecordingReader()
        reader.facts[0] = replace(reader.facts[0], attributes=0x400)
        with self.assertRaises(ObserverError):
            observe_borrowed_handle(reader, 123, expected_size=21)
        self.assertEqual(reader.calls, ['context', 'metadata'])

    def test_identity_or_context_change_never_returns_a_successful_snapshot(self):
        reader = RecordingReader()
        reader.facts[1] = replace(reader.facts[1], object_id=b'X' * 16)
        with self.assertRaises(ObserverError) as error:
            observe_borrowed_handle(reader, 123, expected_size=21)
        self.assertEqual(error.exception.stage, 'observation_changed')

    def test_preexisting_cleanup_failure_stops_before_any_more_native_calls(self):
        reader = RecordingReader()
        reader.cleanup_errors = [('CloseHandle', 5)]
        with self.assertRaises(ObserverError):
            observe_borrowed_handle(reader, 123, expected_size=21)
        self.assertEqual(reader.calls, [])

    def test_error_reports_cannot_echo_arbitrary_native_or_identity_text(self):
        error = ObserverError('synthetic-private-path', 'synthetic-private-code')
        self.assertNotIn('synthetic-private', repr(error))
        self.assertEqual(error.stage, 'unclassified_failure')
        self.assertIsNone(error.code)

    def test_unsupported_descriptor_preserves_only_fixed_parser_reason(self):
        reader = RecordingReader()
        reader.raw = b'synthetic-private-descriptor'
        with self.assertRaises(ObserverError) as error:
            observe_borrowed_handle(reader, 123, expected_size=21)
        self.assertEqual(error.exception.stage, 'unsupported_captured_descriptor')
        self.assertEqual(error.exception.detail, 'unsupported_descriptor_control')
        self.assertNotIn('synthetic-private', repr(error.exception))


if __name__ == '__main__':
    unittest.main()
