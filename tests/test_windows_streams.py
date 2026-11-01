"""Synthetic SDK stream buffers; never live stream enumeration or payloads."""
from pathlib import Path
import struct
import sys
import unittest
from contextlib import ExitStack
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from windows_streams import assess_file_stream_buffer, StreamError

DEFAULT = b':\x00:\x00$\x00D\x00A\x00T\x00A\x00'


def record(name=DEFAULT, size=21, allocated=4096, following=0):
    return struct.pack('<IIqq', following, len(name), size, allocated) + name


class StreamBufferTests(unittest.TestCase):
    def test_single_unnamed_stream_is_only_captured_evidence(self):
        result = assess_file_stream_buffer(record(), expected_size=21)
        self.assertEqual(result.status, 'captured-default-stream-only')
        self.assertFalse(result.filesystem_verified)
        self.assertFalse(result.installation_admitted)
        self.assertFalse(result.native_action_admitted)

    def test_unknown_named_duplicate_or_malformed_chain_always_refuses(self):
        for following in (1, 8, 40, 0xFFFFFFFF):
            with self.subTest(following=following), self.assertRaises(StreamError):
                assess_file_stream_buffer(record(following=following) + record(), expected_size=21)
        with self.assertRaises(StreamError) as error:
            assess_file_stream_buffer(record(name=b'synthetic-private-stream'), expected_size=21)
        self.assertNotIn('synthetic-private', str(error.exception))

    def test_truncation_wrong_name_length_and_unknown_tail_refuse(self):
        raw = record()
        for length in range(len(raw)):
            with self.subTest(length=length), self.assertRaises(StreamError):
                assess_file_stream_buffer(raw[:length], expected_size=21)
        for length in (0, 13, 15, 0xFFFFFFFF):
            malformed = bytearray(raw)
            struct.pack_into('<I', malformed, 4, length)
            with self.assertRaises(StreamError):
                assess_file_stream_buffer(bytes(malformed), expected_size=21)
        with self.assertRaises(StreamError):
            assess_file_stream_buffer(raw + b'private', expected_size=21)

    def test_signed_metadata_and_independent_size_mismatch_refuse(self):
        for raw in (record(size=-1), record(size=22), record(allocated=-1)):
            with self.assertRaises(StreamError):
                assess_file_stream_buffer(raw, expected_size=21)
        for size in (True, -1, 2**63, '21'):
            with self.assertRaises(StreamError):
                assess_file_stream_buffer(record(), expected_size=size)

    def test_zero_and_sparse_allocation_do_not_grant_native_qualification(self):
        for size, allocation in ((0, 0), (21, 0), (2**63 - 1, 4096)):
            result = assess_file_stream_buffer(record(size=size, allocated=allocation), expected_size=size)
            self.assertEqual(result.evidence_scope, 'captured-file-stream-buffer-only')
            self.assertFalse(result.filesystem_verified)

    def test_capacity_padding_and_exact_type_bounds_are_enforced(self):
        self.assertFalse(assess_file_stream_buffer(record() + bytes(65536 - 38), expected_size=21).installation_admitted)
        for raw in (record() + bytes(65537 - 38), bytearray(record()), None):
            with self.assertRaises(StreamError):
                assess_file_stream_buffer(raw, expected_size=21)

    def test_decoder_makes_no_filesystem_process_network_or_native_calls(self):
        with ExitStack() as stack:
            controls = [stack.enter_context(patch(name, side_effect=AssertionError('boundary forbidden'),
                                                        create=(name == 'ctypes.WinDLL')))
                        for name in ('builtins.open', 'os.stat', 'os.scandir',
                                     'socket.socket', 'subprocess.Popen', 'ctypes.WinDLL')]
            for control in controls:
                with self.assertRaises(AssertionError):
                    control('synthetic-positive-control')
            result = assess_file_stream_buffer(record(), expected_size=21)
        self.assertFalse(result.native_action_admitted)


if __name__ == '__main__':
    unittest.main()
