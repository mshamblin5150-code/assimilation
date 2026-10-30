"""CI-only harness: compare clean worktree including ignored artifacts around CLI."""
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys


def inventory(root):
    result = {}
    total = 0
    def unavailable(error):
        raise ValueError('inventory-unavailable') from None
    for directory, dirs, files in os.walk(root, followlinks=False, onerror=unavailable):
        if Path(directory) == root:
            dirs[:] = [name for name in dirs if name != '.git']
        for name in list(dirs) + files:
            path = Path(directory) / name
            info = path.lstat()
            key = path.relative_to(root).as_posix()
            if len(result) >= 20000:
                raise ValueError('inventory-bound')
            if stat.S_ISLNK(info.st_mode):
                result[key] = ('link', os.readlink(path))
                if name in dirs:
                    dirs.remove(name)
            elif getattr(info, 'st_file_attributes', 0) & 0x400:
                raise ValueError('unsupported-reparse')
            elif stat.S_ISDIR(info.st_mode):
                result[key] = ('directory', info.st_mode)
            elif stat.S_ISREG(info.st_mode):
                total += info.st_size
                if total > 128 * 1024 * 1024:
                    raise ValueError('inventory-bound')
                with path.open('rb') as source:
                    data = source.read(info.st_size + 1)
                if len(data) != info.st_size:
                    raise ValueError('inventory-changed')
                result[key] = ('file', info.st_mode, hashlib.sha256(data).hexdigest())
            else:
                raise ValueError('unsupported-object')
    return result


def main():
    root = Path(__file__).resolve().parents[1]
    if not (root / '.git').exists():
        raise ValueError('complete-checkout-required')
    def status():
        return subprocess.run(['git', '--no-optional-locks', '-c', 'core.fsmonitor=false',
            '-c', 'core.untrackedCache=false', 'status', '--porcelain=v1',
            '--untracked-files=all', '--ignored=matching'], cwd=root,
            check=True, capture_output=True).stdout
    if status():
        raise ValueError('clean-checkout-required')
    before = inventory(root)
    for args in ([], ['--help']):
        completed = subprocess.run([sys.executable, '-B', 'scripts/windows_onboarding.py', *args],
                                   cwd=root, capture_output=True, check=True)
        if not args and json.loads(completed.stdout)['installation_admitted'] is not False:
            raise ValueError('admission-regression')
        if status() or inventory(root) != before:
            raise ValueError('worktree-changed')
    print('Clean-checkout onboarding report/help preserved tracked, untracked and ignored worktree state.')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, subprocess.SubprocessError):
        print('Clean-checkout onboarding regression failed.', file=sys.stderr)
        raise SystemExit(1)
