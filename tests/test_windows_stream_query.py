"""Recorded SDK calls only. No Win32Reader/DLL/live enumeration instantiated."""
import ctypes as c
from dataclasses import replace
from contextlib import contextmanager, ExitStack
from threading import local
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from test_windows_handle_observer import RecordingReader
from test_windows_streams import record
from windows_stream_query import observe_file_streams, StreamQueryError
from windows_handle_observer import ObserverError, ReaderContext
from test_windows_descriptors import OTHER


@contextmanager
def recorded_last_error():
    """Scoped recording state, never native last-error or ABI evidence."""
    state = local()
    def get_error():
        return getattr(state, 'value', 0)
    def set_error(value):
        previous = get_error()
        state.value = value
        return previous
    with ExitStack() as stack:
        stack.enter_context(patch.object(c, 'get_last_error', get_error, create=True))
        stack.enter_context(patch.object(c, 'set_last_error', set_error, create=True))
        yield


class RecordedLastErrorTests(unittest.TestCase):
    def test_present_attributes_and_state_restore_on_normal_and_exceptional_exit(self):
        previous = [73]
        def get_previous():
            return previous[0]
        def set_previous(value):
            old = previous[0]
            previous[0] = value
            return old
        with patch.object(c, 'get_last_error', get_previous, create=True), \
             patch.object(c, 'set_last_error', set_previous, create=True):
            for fail in (False, True):
                with self.subTest(exceptional=fail):
                    marker = RuntimeError('synthetic-exit')
                    caught = None
                    try:
                        with recorded_last_error():
                            self.assertEqual(c.get_last_error(), 0)
                            self.assertEqual(c.set_last_error(5), 0)
                            with recorded_last_error():
                                self.assertEqual(c.get_last_error(), 0)
                                c.set_last_error(9)
                            self.assertEqual(c.get_last_error(), 5)
                            if fail:
                                raise marker
                    except RuntimeError as observed:
                        if not fail:
                            raise
                        caught = observed
                    self.assertIs(caught, marker if fail else None)
                    self.assertIs(c.get_last_error, get_previous)
                    self.assertIs(c.set_last_error, set_previous)
                    self.assertEqual(previous, [73])

    def test_absent_attributes_removed_on_normal_and_exceptional_exit(self):
        names = ('get_last_error', 'set_last_error')
        saved = {name: (name in c.__dict__, c.__dict__.get(name)) for name in names}
        sentinel = object()
        other = getattr(c, 'WinDLL', sentinel)
        try:
            for name in names:
                if name in c.__dict__:
                    delattr(c, name)
            for fail in (False, True):
                with self.subTest(exceptional=fail):
                    marker = RuntimeError('synthetic-exit')
                    caught = None
                    try:
                        with recorded_last_error():
                            self.assertEqual(c.get_last_error(), 0)
                            self.assertEqual(c.set_last_error(5), 0)
                            self.assertEqual(c.get_last_error(), 5)
                            if fail:
                                raise marker
                    except RuntimeError as observed:
                        if not fail:
                            raise
                        caught = observed
                    self.assertIs(caught, marker if fail else None)
                    for name in names:
                        self.assertNotIn(name, c.__dict__)
                    self.assertIs(getattr(c, 'WinDLL', sentinel), other)
        finally:
            for name, (existed, value) in saved.items():
                if existed:
                    setattr(c, name, value)
                elif name in c.__dict__:
                    delattr(c, name)

class StreamReader(RecordingReader):
    def __init__(self):
        super().__init__()
        self.sdk_calls = []
        self.raw = record()
        self.ok, self.code = 1, 0
        self.kernel = SimpleNamespace(GetFileInformationByHandleEx=self.sdk)

    def sdk(self, handle, kind, buffer, size):
        self.sdk_calls.append((handle, kind, size, bytes(buffer.raw)))
        c.memmove(buffer, self.raw, len(self.raw))
        c.set_last_error(self.code)
        return self.ok


class StreamQueryTests(unittest.TestCase):
    def setUp(self):
        stack = ExitStack()
        self.addCleanup(stack.close)
        stack.enter_context(recorded_last_error())

    def test_single_query_uses_zero_initialized_bounded_buffer_without_admission(self):
        reader = StreamReader()
        with patch.object(c, 'WinDLL', side_effect=AssertionError('DLL forbidden'), create=True):
            result = observe_file_streams(reader, 123, expected_facts=reader.facts[0])
        self.assertEqual(len(reader.sdk_calls), 1)
        self.assertEqual(reader.sdk_calls[0][:3], (123, 7, 65536))
        self.assertFalse(any(reader.sdk_calls[0][3]))
        self.assertFalse(result.confinement_verified)
        self.assertFalse(result.installation_admitted)
        self.assertEqual(result.evidence_scope, 'retained-file-stream-partial-snapshot')

    def test_eof_denial_and_insufficient_buffer_never_trigger_retry_or_later_reads(self):
        for ok, code in ((0, 0), (0, 5), (0, 122), (0, 234), (0, 38), (1, 38), (1, 5)):
            reader = StreamReader()
            expected = reader.facts[0]
            reader.ok, reader.code = ok, code
            with self.subTest(ok=ok, code=code), self.assertRaises(StreamQueryError) as error:
                observe_file_streams(reader, 123, expected_facts=expected)
            self.assertEqual(error.exception.code, code)
            self.assertEqual(len(reader.sdk_calls), 1)
            self.assertEqual(reader.calls, ['context', 'metadata'])

    def test_invalid_scope_and_directory_refuse_before_port_calls(self):
        for handle, field in ((True, {}), (0, {}), (123, {'directory': True, 'attributes': 0x10})):
            reader = StreamReader()
            with self.assertRaises((StreamQueryError, ObserverError)):
                observe_file_streams(reader, handle, expected_facts=replace(reader.facts[0], **field))
            self.assertEqual(reader.calls, [])
            self.assertEqual(reader.sdk_calls, [])

    def test_identity_mismatch_before_query_stops_without_enumeration(self):
        reader = StreamReader()
        expected = replace(reader.facts[0], object_id=b'X' * 16)
        with self.assertRaises(StreamQueryError):
            observe_file_streams(reader, 123, expected_facts=expected)
        self.assertEqual(reader.sdk_calls, [])

    def test_metadata_or_context_changes_after_query_refuse(self):
        for context_change in (False, True):
            reader = StreamReader()
            expected = reader.facts[0]
            if context_change:
                values = iter((reader.context_value, ReaderContext(OTHER, False, False)))
                reader.context = lambda: next(values)
            else:
                reader.facts[1] = replace(expected, change_time=101)
            with self.assertRaises(StreamQueryError):
                observe_file_streams(reader, 123, expected_facts=expected)
            self.assertEqual(len(reader.sdk_calls), 1)

    def test_query_cleanup_failure_stops_immediately(self):
        reader = StreamReader()
        expected = reader.facts[0]
        original = reader.kernel.GetFileInformationByHandleEx
        def fail_cleanup(*args):
            result = original(*args)
            reader.cleanup_errors.append(('LocalFree', 5))
            return result
        reader.kernel.GetFileInformationByHandleEx = fail_cleanup
        with self.assertRaises(StreamQueryError):
            observe_file_streams(reader, 123, expected_facts=expected)
        self.assertEqual(reader.calls, ['context', 'metadata'])

    def test_unaligned_buffer_is_never_passed_to_sdk(self):
        reader = StreamReader()
        with patch.object(c, 'addressof', return_value=1), self.assertRaises(StreamQueryError):
            observe_file_streams(reader, 123, expected_facts=reader.facts[0])
        self.assertEqual(reader.sdk_calls, [])

    def test_unknown_stream_capture_refuses_without_name_or_identity_output(self):
        reader = StreamReader()
        reader.raw = record(name=b'synthetic-private-stream')
        with self.assertRaises(StreamQueryError) as error:
            observe_file_streams(reader, 123, expected_facts=reader.facts[0])
        self.assertEqual(error.exception.stage, 'capture')
        self.assertNotIn('synthetic-private', repr(error.exception))

    def test_stale_last_error_is_reset_before_query(self):
        reader = StreamReader()
        original = reader.kernel.GetFileInformationByHandleEx
        observed = []
        def capture_error(*args):
            observed.append(c.get_last_error())
            return original(*args)
        reader.kernel.GetFileInformationByHandleEx = capture_error
        c.set_last_error(38)
        result = observe_file_streams(reader, 123, expected_facts=reader.facts[0])
        self.assertEqual(observed, [0])
        self.assertFalse(result.installation_admitted)

    def test_preexisting_cleanup_failure_stops_before_context_or_query(self):
        for state in ([('CloseHandle', 5)], True):
            reader = StreamReader()
            reader.cleanup_errors = state
            with self.assertRaises(StreamQueryError):
                observe_file_streams(reader, 123, expected_facts=reader.facts[0])
            self.assertEqual(reader.calls, [])
            self.assertEqual(reader.sdk_calls, [])


if __name__ == '__main__':
    unittest.main()
