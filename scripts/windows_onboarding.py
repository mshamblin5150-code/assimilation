#!/usr/bin/env python3
"""Report prerequisites without qualifying or performing an installation."""
import json
import os
import struct
import sys


def report():
    """Observe runtime categories without filesystem discovery or Git execution."""
    return {
        'schema': 1,
        'status': 'observed-not-qualified',
        'runtime': {'platform': sys.platform, 'os_name': os.name,
                    'python': list(sys.version_info[:3]),
                    'pointer_bits': struct.calcsize('P') * 8,
                    'windows_version': list(sys.getwindowsversion()[:3])
                    if sys.platform == 'win32' else None},
        'git': {'discovery': 'not-probed', 'availability': 'unverified',
                'execution': 'not-probed', 'version': 'unverified'},
        'environment': {
            'markers': [label for key, label in
                        (('VIRTUAL_ENV', 'virtual-env'), ('CONDA_PREFIX', 'conda'))
                        if os.environ.get(key)],
            'status': 'markers-only-not-validated',
            'python_prefix_differs': sys.prefix != sys.base_prefix},
        'installation_admitted': False,
        'filesystem_verified': False,
        'source_verified': False,
        'source_operations': 'native-windows-unsupported'
        if sys.platform == 'win32' and os.name == 'nt' else 'not-qualified',
        'qualification': {name: 'not-probed' for name in
                          ('acl', 'ownership', 'junctions', 'symlinks',
                           'rollback', 'concurrency', 'msys')},
        'next_actions': [
            'Do not install dependencies or change PATH, Git, ACLs or security settings automatically.',
            'Read docs/WINDOWS_ONBOARDING.md; record missing prerequisites and request only the required operator action.',
            'Native Windows source operations remain unsupported; POSIX runtime identity alone does not qualify a filesystem.',
            'Git availability/version are unverified: no PATH search, configuration read, execution or transport probe is performed.'],
    }


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if args == ['--help']:
        print('Usage: python -B scripts/windows_onboarding.py [--help]\n'
              'Read-only prerequisite categories. No installation or security changes. '
              'No Git execution, source verification or filesystem qualification.')
        return 0
    if args:
        print(json.dumps({'schema': 1, 'status': 'blocked', 'error': 'invalid-arguments'}))
        return 2
    try:
        observed = report()
    except (OSError, ValueError):
        print(json.dumps({'schema': 1, 'status': 'blocked', 'error': 'observation-unavailable',
                          'installation_admitted': False}))
        return 1
    print(json.dumps(observed, sort_keys=True))
    return 0


if __name__ == '__main__':
    sys.exit(main())
