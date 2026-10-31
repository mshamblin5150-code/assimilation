"""Simulated filesystem boundary; no fixture writes or cleanup."""
import io
from pathlib import Path
import stat
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from onboarding_clean_checkout import inventory


class InventoryTests(unittest.TestCase):
    def test_all_files_including_ignored_names_are_compared(self):
        root = Path('synthetic-root')
        files = {'tracked': b'old', 'untracked': b'old', 'ignored.pyc': b'old'}
        def walk(*args, **kwargs):
            yield str(root), [], list(files)
        def metadata(path):
            return SimpleNamespace(st_mode=stat.S_IFREG, st_file_attributes=0,
                                   st_size=len(files[path.name]))
        def opened(path, *args, **kwargs):
            return io.BytesIO(files[path.name])
        with patch('os.walk', walk), patch.object(Path, 'lstat', metadata), patch.object(Path, 'open', opened):
            before = inventory(root)
            for name in tuple(files):
                files[name] = b'edited'
                self.assertNotEqual(inventory(root), before)
                files[name] = b'old'
            files['new.pyc'] = b'new'
            self.assertNotEqual(inventory(root), before)
            del files['new.pyc']
            del files['tracked']
            self.assertNotEqual(inventory(root), before)

    def test_unreadable_walk_cannot_pass_with_partial_inventory(self):
        def walk(*args, **kwargs):
            kwargs['onerror'](PermissionError('synthetic-private'))
            return iter(())
        with patch('os.walk', walk), self.assertRaisesRegex(ValueError, '^inventory-unavailable$'):
            inventory(Path('synthetic-root'))
