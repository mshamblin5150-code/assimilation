"""Recorded SDK open completions; no native opener instantiated by these tests."""
from dataclasses import replace
import unittest

from test_windows_pair_observer import PARENT, CHILD
from test_windows_handle_observer import RecordingReader
from windows_opener import WindowsOpener, OpenError, OwnedObject
from windows_handle_observer import ReaderContext, ObserverError
from test_windows_descriptors import USER


class OpenAPI:
    def __init__(self):
        self.calls = []
        self.completions = [(0, 0, 1, 123), (0, 0, 1, 124)]
        self.close_ok = True

    def open(self, root, name):
        self.calls.append(('open', root, name))
        return self.completions.pop(0)

    def close(self, handle):
        self.calls.append(('close', handle))
        return self.close_ok, 0 if self.close_ok else 5


class OpenReader(RecordingReader):
    def metadata(self, handle):
        self.calls.append(('metadata', handle))
        return PARENT if handle == 123 else CHILD


class WindowsOpenerTests(unittest.TestCase):
    def test_recorded_stream_query_keeps_custody_during_sdk_callback(self):
        from test_windows_stream_query import StreamReader, recorded_last_error
        from windows_stream_query import observe_file_streams
        api, reader = OpenAPI(), StreamReader()
        reader.metadata = lambda handle: PARENT if handle == 123 else CHILD
        opener = WindowsOpener(reader, api)
        root = opener.open_root()
        child = opener.open_child(root, 'file', directory=False)
        query = reader.kernel.GetFileInformationByHandleEx
        rejected = []
        def callback(*args):
            try:
                opener.close_all()
            except OpenError as error:
                rejected.append(error.stage)
            return query(*args)
        reader.kernel.GetFileInformationByHandleEx = callback
        with recorded_last_error(), opener.retained_file(child) as handle:
            result = observe_file_streams(reader, handle, expected_facts=child.facts)
        self.assertEqual(rejected, ['operation_busy'])
        self.assertEqual(len(reader.sdk_calls), 1)
        self.assertEqual(tuple(opener.owned), (root, child))
        self.assertFalse(result.installation_admitted)
        opener.close_all()

    def test_retained_file_body_exception_preserves_primary_without_exit_queries(self):
        for failure in (ValueError('synthetic'), KeyboardInterrupt()):
            api, reader = OpenAPI(), OpenReader()
            opener = WindowsOpener(reader, api)
            root = opener.open_root()
            child = opener.open_child(root, 'file', directory=False)
            try:
                with opener.retained_file(child):
                    calls = list(reader.calls)
                    raise failure
            except BaseException as observed:
                self.assertIs(observed, failure)
            self.assertEqual(reader.calls, calls)
            self.assertTrue(opener.failed)
            self.assertEqual(tuple(opener.owned), (root, child))
            opener.close_all()
            self.assertEqual(api.calls[-2:], [('close', 124), ('close', 123)])

    def test_retained_file_invalid_nodes_refuse_before_reader_calls(self):
        api, reader = OpenAPI(), OpenReader()
        opener = WindowsOpener(reader, api)
        root = opener.open_root()
        child = opener.open_child(root, 'file', directory=False)
        opener.close(child)
        for node in (root, child, OwnedObject(124, CHILD), None):
            before = list(reader.calls)
            with self.assertRaises(OpenError):
                with opener.retained_file(node):
                    self.fail('invalid node admitted')
            self.assertEqual(reader.calls, before)
            self.assertFalse(opener.failed)
        opener.close_all()

    def test_retained_file_observed_change_latches_failure_and_releases_for_cleanup(self):
        for change in ('metadata', 'context', 'ownership', 'cleanup'):
            api, reader = OpenAPI(), OpenReader()
            opener = WindowsOpener(reader, api)
            root = opener.open_root()
            child = opener.open_child(root, 'file', directory=False)
            with self.subTest(change=change), self.assertRaises((OpenError, ObserverError)):
                with opener.retained_file(child):
                    if change == 'metadata':
                        reader.metadata = lambda handle: replace(CHILD, size=CHILD.size + 1)
                    elif change == 'context':
                        reader.context = lambda: ReaderContext(USER, True, False)
                    elif change == 'ownership':
                        opener.owned.reverse()  # Deliberate out-of-contract mutation control.
                    else:
                        reader.cleanup_errors.append(5)
            self.assertTrue(opener.failed)
            # Restore only simulated ordering for explicit cleanup; no real handles.
            if change == 'ownership':
                opener.owned.reverse()
            opener.close_all()
            self.assertEqual(api.calls[-2:], [('close', 124), ('close', 123)])

    def test_retained_file_missing_or_cyclic_ancestry_refuses_without_sdk_reads(self):
        for cyclic in (False, True):
            api, reader = OpenAPI(), OpenReader()
            opener = WindowsOpener(reader, api)
            root = opener.open_root()
            child = opener.open_child(root, 'file', directory=False)
            if cyclic:
                object.__setattr__(root, 'parent', root)  # Hostile model control.
            else:
                opener.owned.remove(root)
            before = list(reader.calls)
            with self.assertRaises(OpenError):
                with opener.retained_file(child):
                    self.fail('broken ancestry admitted')
            self.assertEqual(reader.calls, before)
            if cyclic:
                object.__setattr__(root, 'parent', None)
            opener.close_all()

    def test_retained_file_blocks_public_close_through_observation(self):
        api, reader = OpenAPI(), OpenReader()
        opener = WindowsOpener(reader, api)
        root = opener.open_root()
        child = opener.open_child(root, 'file', directory=False)
        before = list(api.calls)
        with opener.retained_file(child) as handle:
            self.assertEqual(handle, 124)
            for action in (lambda: opener.close(child), opener.close_all,
                           opener.open_root,
                           lambda: opener.open_child(root, 'new', directory=False)):
                with self.assertRaises(OpenError) as error:
                    action()
                self.assertEqual(error.exception.stage, 'operation_busy')
            with self.assertRaises(OpenError) as error:
                with opener.retained_file(child):
                    self.fail('nested lease admitted')
            self.assertEqual(error.exception.stage, 'operation_busy')
            self.assertEqual(api.calls, before)
            self.assertFalse(opener.failed)
        self.assertEqual(tuple(opener.owned), (root, child))
        opener.close_all()
        self.assertEqual(api.calls[-2:], [('close', 124), ('close', 123)])

    def test_every_public_mutator_refuses_reentry_before_any_state_or_sdk_change(self):
        api, reader = OpenAPI(), OpenReader()
        opener = WindowsOpener(reader, api)
        root = opener.open_root()
        original_open = api.open
        stages = []
        def callback_open(parent, name):
            completion = original_open(parent, name)
            for action in (opener.open_root, lambda: opener.open_child(root, 'nested', directory=False),
                           lambda: opener.close(root), opener.close_all):
                before = (tuple(opener.owned), list(api.calls), opener.failed)
                try:
                    action()
                except OpenError as error:
                    stages.append(error.stage)
                self.assertEqual((tuple(opener.owned), list(api.calls), opener.failed), before)
            return completion
        api.open = callback_open
        opener.open_child(root, 'file', directory=False)
        self.assertEqual(stages, ['operation_busy'] * 4)
        opener.close_all()

    def test_operation_lock_releases_after_invalid_scope_and_base_exception(self):
        api, reader = OpenAPI(), OpenReader()
        opener = WindowsOpener(reader, api)
        root = opener.open_root()
        with self.assertRaises(OpenError):
            opener.open_child(root, '..', directory=False)
        opener.open_child(root, 'file', directory=False)
        opener.close_all()
        api, reader = OpenAPI(), OpenReader()
        opener = WindowsOpener(reader, api)
        def interrupted(*args):
            raise KeyboardInterrupt()
        api.open = interrupted
        with self.assertRaises(KeyboardInterrupt):
            opener.open_root()
        self.assertEqual(opener.close_all(), ())
        self.assertEqual(opener.owned, [])

    def test_close_callback_cannot_start_another_acquisition(self):
        api, reader = OpenAPI(), OpenReader()
        opener = WindowsOpener(reader, api)
        root = opener.open_root()
        child = opener.open_child(root, 'file', directory=False)
        original_close = api.close
        stages = []
        def callback_close(handle):
            try:
                opener.open_child(root, 'new-file', directory=False)
            except OpenError as error:
                stages.append(error.stage)
            return original_close(handle)
        api.close = callback_close
        opener.close(child)
        opener.close(root)
        self.assertEqual(stages, ['operation_busy', 'operation_busy'])
        self.assertEqual(len([call for call in api.calls if call[0] == 'open']), 2)

    def test_reentrant_close_cannot_remove_parent_during_child_acquisition(self):
        api, reader = OpenAPI(), OpenReader()
        opener = WindowsOpener(reader, api)
        root = opener.open_root()
        original_open = api.open
        rejected = []
        def callback_open(parent, name):
            completion = original_open(parent, name)
            try:
                opener.close(root)
            except OpenError as error:
                rejected.append(error.stage)
            return completion
        api.open = callback_open
        opener.open_child(root, 'child', directory=False)
        self.assertEqual(rejected, ['operation_busy'])
        self.assertTrue(any(node is root for node in opener.owned))
        self.assertFalse(any(call[0] == 'close' for call in api.calls))
        opener.close_all()
        self.assertEqual(api.calls[-2:], [('close', 124), ('close', 123)])

    def test_duplicate_object_identity_cannot_own_two_recovery_roles(self):
        api, reader = OpenAPI(), OpenReader()
        api.completions.append((0, 0, 1, 125))
        opener = WindowsOpener(reader, api)
        root = opener.open_root()
        first = opener.open_child(root, 'first', directory=False)
        with self.assertRaises(OpenError) as error:
            opener.open_child(root, 'alias', directory=False)
        self.assertEqual(error.exception.stage, 'object_alias')
        self.assertEqual(api.calls[-1], ('close', 125))
        self.assertTrue(any(node is first for node in opener.owned))
        self.assertTrue(any(node is root for node in opener.owned))
        before = list(api.calls)
        with self.assertRaises(OpenError):
            opener.open_child(root, 'retry', directory=False)
        self.assertEqual(api.calls, before)
        opener.close_all()
        self.assertEqual(api.calls[-2:], [('close', 124), ('close', 123)])

    def test_non_immediate_ancestor_alias_is_rejected(self):
        api, reader = OpenAPI(), OpenReader()
        api.completions.append((0, 0, 1, 125))
        facts = {123: PARENT, 124: replace(PARENT, object_id=b'D' * 16), 125: PARENT}
        reader.metadata = lambda handle: facts[handle]
        opener = WindowsOpener(reader, api)
        root = opener.open_root()
        directory = opener.open_child(root, 'nested', directory=True)
        with self.assertRaises(OpenError) as error:
            opener.open_child(directory, 'alias', directory=True)
        self.assertEqual(error.exception.stage, 'object_alias')
        opener.close_all()
        self.assertEqual(api.calls[-3:], [('close', 125), ('close', 124), ('close', 123)])

    def test_successful_close_allows_new_acquisition_without_trusting_old_node(self):
        api, reader = OpenAPI(), OpenReader()
        api.completions.append((0, 0, 1, 125))
        opener = WindowsOpener(reader, api)
        root = opener.open_root()
        first = opener.open_child(root, 'file', directory=False)
        opener.close(first)
        second = opener.open_child(root, 'file', directory=False)
        self.assertIsNot(first, second)
        with self.assertRaises(OpenError):
            opener.close(first)
        opener.close_all()
        self.assertEqual(api.calls[-2:], [('close', 125), ('close', 123)])

    def test_duplicate_cleanup_failure_keeps_originals_and_never_retries_new_handle(self):
        api, reader = OpenAPI(), OpenReader()
        api.completions.append((0, 0, 1, 125))
        def close(handle):
            api.calls.append(('close', handle))
            return (False, 5) if handle == 125 else (True, 0)
        api.close = close
        opener = WindowsOpener(reader, api)
        root = opener.open_root()
        first = opener.open_child(root, 'file', directory=False)
        with self.assertRaises(OpenError) as error:
            opener.open_child(root, 'alias', directory=False)
        self.assertEqual(error.exception.stage, 'object_alias')
        self.assertEqual(opener.cleanup_errors, [5])
        self.assertTrue(any(node is first for node in opener.owned))
        opener.close_all()
        self.assertEqual(api.calls.count(('close', 125)), 1)
        self.assertEqual(api.calls[-2:], [('close', 124), ('close', 123)])

    def test_root_and_one_relative_component_retain_owned_handles_until_close(self):
        api, reader = OpenAPI(), OpenReader()
        opener = WindowsOpener(reader, api)
        parent = opener.open_root()
        child = opener.open_child(parent, 'plain.txt', directory=False)
        self.assertEqual(child.facts, CHILD)
        self.assertEqual(api.calls, [('open', None, '\\??\\C:\\'),
                                     ('open', 123, 'plain.txt')])
        opener.close_all()
        self.assertEqual(api.calls[-2:], [('close', 124), ('close', 123)])

    def test_ancestor_cannot_be_closed_while_its_child_is_owned(self):
        api, reader = OpenAPI(), OpenReader()
        opener = WindowsOpener(reader, api)
        parent = opener.open_root()
        child = opener.open_child(parent, 'plain.txt', directory=False)
        before = list(api.calls)
        with self.assertRaises(OpenError):
            opener.close(parent)
        self.assertEqual(api.calls, before)
        opener.close(child)
        opener.close(parent)
        self.assertEqual(api.calls[-2:], [('close', 124), ('close', 123)])

    def test_grandchildren_keep_entire_ancestor_chain_until_reverse_cleanup(self):
        api, reader = OpenAPI(), OpenReader()
        api.completions.append((0, 0, 1, 125))
        facts = {123: PARENT, 124: replace(CHILD, directory=True, attributes=0x10, size=0),
                 125: replace(CHILD, object_id=b'G' * 16)}
        reader.metadata = lambda handle: facts[handle]
        opener = WindowsOpener(reader, api)
        root = opener.open_root()
        child = opener.open_child(root, 'nested', directory=True)
        opener.open_child(child, 'payload.bin', directory=False)
        for ancestor in (root, child):
            with self.assertRaises(OpenError):
                opener.close(ancestor)
        opener.close_all()
        self.assertEqual(api.calls[-3:], [('close', 125), ('close', 124), ('close', 123)])

    def test_one_remaining_sibling_still_prevents_parent_close(self):
        api, reader = OpenAPI(), OpenReader()
        api.completions.append((0, 0, 1, 125))
        facts = {123: PARENT, 124: CHILD, 125: replace(CHILD, object_id=b'S' * 16)}
        reader.metadata = lambda handle: facts[handle]
        opener = WindowsOpener(reader, api)
        root = opener.open_root()
        first = opener.open_child(root, 'first', directory=False)
        second = opener.open_child(root, 'second', directory=False)
        opener.close(first)
        with self.assertRaises(OpenError):
            opener.close(root)
        opener.close(second)
        opener.close(root)

    def test_uncertain_child_close_allows_parent_cleanup_but_no_reuse_or_retry(self):
        api, reader = OpenAPI(), OpenReader()
        opener = WindowsOpener(reader, api)
        root = opener.open_root()
        child = opener.open_child(root, 'child', directory=False)
        api.close_ok = False
        opener.close(child)
        before = list(api.calls)
        with self.assertRaises(OpenError):
            opener.open_child(root, 'new', directory=False)
        with self.assertRaises(OpenError):
            opener.close(child)
        self.assertEqual(api.calls, before)
        api.close_ok = True
        opener.close_all()
        self.assertEqual(api.calls[-1], ('close', 123))
        self.assertEqual(opener.cleanup_errors, [5])

    def test_components_never_become_paths_devices_ads_or_aliases(self):
        for name in ('..', '.', 'a/b', 'a\\b', 'C:', 'plain:ads', 'NUL.txt',
                     'CON', 'a.', 'a ', 'abc~1', '.git', 'é', '', True, 'a' * 81):
            api, reader = OpenAPI(), OpenReader()
            opener = WindowsOpener(reader, api)
            parent = opener.open_root()
            before = len(api.calls)
            with self.subTest(name=name), self.assertRaises(OpenError):
                opener.open_child(parent, name, directory=False)
            self.assertEqual(len(api.calls), before)
            opener.close_all()

    def test_denied_pending_or_unexpected_status_never_reissues_or_claims_ownership(self):
        for status in (0xC0000022, 0x103, 1, True):
            api, reader = OpenAPI(), OpenReader()
            api.completions = [(status, 0, 1, None)]
            opener = WindowsOpener(reader, api)
            with self.subTest(status=status), self.assertRaises(OpenError):
                opener.open_root()
            with self.assertRaises(OpenError):
                opener.open_root()
            opener.close_all()
            self.assertEqual(len(api.calls), 1)

    def test_success_with_bad_completion_closes_new_handle_once(self):
        for completion in ((0, 0x103, 1, 123), (0, 0, 2, 123), (0, 0, True, 123)):
            api, reader = OpenAPI(), OpenReader()
            api.completions = [completion]
            opener = WindowsOpener(reader, api)
            with self.subTest(completion=completion), self.assertRaises(OpenError):
                opener.open_root()
            opener.close_all()
            self.assertEqual(api.calls[-1], ('close', 123))
            self.assertEqual(len(api.calls), 2)

    def test_reparse_or_wrong_type_is_rejected_before_security(self):
        for facts in (replace(PARENT, attributes=0x410), CHILD):
            api, reader = OpenAPI(), OpenReader()
            reader.metadata = lambda handle: facts
            opener = WindowsOpener(reader, api)
            with self.subTest(facts=facts), self.assertRaises((ObserverError, OpenError)):
                opener.open_root()
            self.assertEqual(api.calls[-1], ('close', 123))
            opener.close_all()
            self.assertEqual(len(api.calls), 2)

    def test_changed_parent_stops_before_child_open(self):
        api, reader = OpenAPI(), OpenReader()
        opener = WindowsOpener(reader, api)
        parent = opener.open_root()
        reader.metadata = lambda handle: replace(PARENT, object_id=b'X' * 16)
        with self.assertRaises(OpenError):
            opener.open_child(parent, 'plain.txt', directory=False)
        self.assertEqual(len(api.calls), 1)
        opener.close_all()

    def test_foreign_closed_or_forged_node_is_not_an_owned_parent(self):
        api, reader = OpenAPI(), OpenReader()
        opener = WindowsOpener(reader, api)
        parent = opener.open_root()
        with self.assertRaises(OpenError):
            opener.open_child(OwnedObject(parent.handle, parent.facts), 'plain.txt', directory=False)
        opener.close_all()
        with self.assertRaises(OpenError):
            opener.open_child(parent, 'plain.txt', directory=False)
        with self.assertRaises(OpenError):
            opener.close(parent)
        self.assertEqual(len(api.calls), 2)

    def test_close_failure_is_preserved_without_retry_or_future_open(self):
        api, reader = OpenAPI(), OpenReader()
        opener = WindowsOpener(reader, api)
        parent = opener.open_root()
        api.close_ok = False
        opener.close(parent)
        self.assertEqual(opener.cleanup_errors, [5])
        opener.close_all()
        with self.assertRaises(OpenError):
            opener.open_child(parent, 'plain.txt', directory=False)
        self.assertEqual(len(api.calls), 2)

    def test_context_change_after_open_closes_handle_and_refuses(self):
        api, reader = OpenAPI(), OpenReader()
        contexts = iter((ReaderContext(USER, False, False), ReaderContext(USER, True, False)))
        reader.context = lambda: next(contexts)
        opener = WindowsOpener(reader, api)
        with self.assertRaises(ObserverError):
            opener.open_root()
        self.assertEqual(api.calls[-1], ('close', 123))

    def test_cleanup_exception_does_not_replace_primary_failure(self):
        api, reader = OpenAPI(), OpenReader()
        reader.metadata = lambda handle: replace(PARENT, attributes=0x410)
        def throwing_close(handle):
            api.calls.append(('close', handle))
            raise RuntimeError('synthetic-cleanup-marker')
        api.close = throwing_close
        opener = WindowsOpener(reader, api)
        with self.assertRaises(ObserverError) as error:
            opener.open_root()
        self.assertEqual(error.exception.stage, 'unsupported_fixture_object')
        self.assertEqual(opener.cleanup_errors, [None])
        self.assertEqual(opener.owned, [])

    def test_cleanup_exception_does_not_prevent_other_distinct_owned_closes(self):
        api, reader = OpenAPI(), OpenReader()
        opener = WindowsOpener(reader, api)
        parent = opener.open_root()
        opener.open_child(parent, 'plain.txt', directory=False)
        def close(handle):
            api.calls.append(('close', handle))
            if handle == 124:
                raise RuntimeError('synthetic-cleanup-marker')
            return True, 0
        api.close = close
        opener.close_all()
        self.assertEqual(api.calls[-2:], [('close', 124), ('close', 123)])
        self.assertEqual(opener.cleanup_errors, [None])
        self.assertEqual(opener.owned, [])


if __name__ == '__main__':
    unittest.main()
