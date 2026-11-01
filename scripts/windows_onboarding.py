#!/usr/bin/env python3
"""Report prerequisites without qualifying or performing an installation."""
import json
import os
import struct
import sys


def report(*, git_requested=False):
    """Observe runtime categories without filesystem discovery or Git execution."""
    return {
        'schema': 1,
        'status': 'observed-not-qualified',
        'python_prerequisite': {'minimum': [3, 10], 'status':
                                'satisfied' if sys.version_info[:2] >= (3, 10) else 'unsupported'},
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
            *(['Stop: use an existing trusted Python 3.10+ interpreter; do not install one automatically.']
              if sys.version_info[:2] < (3, 10) else []),
            'Do not install dependencies or change PATH, Git, ACLs or security settings automatically.',
            'Read docs/WINDOWS_ONBOARDING.md; record missing prerequisites and request only the required operator action.',
            'Native Windows source operations remain unsupported; POSIX runtime identity alone does not qualify a filesystem.',
            ('Compatibility is unverified. Review any failure; do not retry, repair or install automatically.'
             if git_requested else 'Git availability/version are unverified: no PATH search, configuration read, execution or transport probe is performed.')],
    }


def main(argv=None, *, resources=None, platform=None):
    args = sys.argv[1:] if argv is None else argv
    if args == ['--help']:
        print('Usage: python -B scripts/windows_onboarding.py [--git-executable ABSOLUTE_PATH]\n'
              'No installation or security changes. Default/help are passive; no Git discovery. '
              'Optional selected trusted Windows .exe runs only --version, no shell/input/retry. '
              'Trust its installation, dependencies, stable paths and runtime; lexical validation is not confinement. '
              'Five-second deadline after creation; 4 KiB combined output cap during reading. '
              'Creation/termination latency and hostile descendants are not bounded/contained. '
              'Timeout/overflow stop/reap the direct child; cleanup failure refuses without retry. '
              'Observed version compatibility remains unverified; no installation admission.')
        return 0
    reason = None
    status = 0
    selected = None
    if args and (len(args) != 2 or args[0] != '--git-executable'):
        reason, status = 'invalid-arguments', 2
    elif args:
        try:
            from selected_git import capture_version, valid_selection
        except (ImportError, OSError, ValueError):
            reason, status = 'observation-unavailable', 1
        else:
            if not valid_selection(args[1]):
                reason, status = 'invalid-selection', 2
            elif (sys.platform if platform is None else platform) != 'win32':
                reason, status = 'unsupported-platform', 2
            else:
                selected = args[1]
    try:
        observed = report(git_requested=selected is not None)
    except (OSError, ValueError):
        observed = {'schema': 1, 'status': 'blocked', 'error': 'observation-unavailable',
                    'installation_admitted': False, 'filesystem_verified': False,
                    'source_verified': False,
                    'git': {'discovery': 'not-probed', 'execution': 'not-probed',
                            'availability': 'unverified', 'version': 'unverified',
                            'compatibility': 'unverified'}}
        if reason:
            observed['error'] = reason
        print(json.dumps(observed, sort_keys=True))
        return status or 1
    if selected is not None:
        version, reason = capture_version(selected, resources=resources)
        status = 1 if reason else 0
        observed['git'].update(availability='unverified' if reason else 'available',
                               execution='failed' if reason else 'observed',
                               version='unverified' if reason else version,
                               compatibility='unverified')
    if reason:
        observed['status'] = 'blocked'
        observed['error'] = reason
        observed['git']['compatibility'] = 'unverified'
    print(json.dumps(observed, sort_keys=True))
    return status


if __name__ == '__main__':
    sys.exit(main())
