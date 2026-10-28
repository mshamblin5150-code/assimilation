#!/usr/bin/env python3
"""Locate verified original skills offline; this is a guide, not an agent runtime."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys

# Prevent imported repository modules from writing __pycache__ during read-only use.
sys.dont_write_bytecode = True
import snapshot_sources

ROOT = Path(__file__).resolve().parents[1]


# Deliberate starting routes, not exhaustive workflows or permission to invoke them.
ROUTES = {
    'bug': [('matt', 'engineering/diagnosing-bugs'), ('pstack', 'principle-fix-root-causes'), ('pstack', 'principle-prove-it-works')],
    'feature': [('matt', 'engineering/grill-with-docs'), ('matt', 'engineering/tdd'), ('pstack', 'principle-model-the-domain')],
    'review': [('matt', 'engineering/code-review'), ('pstack', 'principle-test-behavior-not-implementation'), ('pstack', 'principle-prove-it-works')],
    'planning': [('matt', 'engineering/wayfinder'), ('pstack', 'principle-sequence-verifiable-units')],
    'writing': [('matt', 'productivity/writing-for-agents'), ('pstack', 'technical-writing')],
    'unknown': [('matt', 'engineering/ask-matt'), ('pstack', 'principle-attack-the-premise')],
}


def route(report: dict, task_type: str) -> dict:
    available = {skill['path']: skill for skill in report['skills']}
    selected = []
    for source, skill in ROUTES[task_type]:
        path = report['sources'][source]['directory'] + '/skills/' + skill + '/SKILL.md'
        if path not in available:
            raise MissingSkill('A requested original skill is unavailable')
        selected.append(available[path])
    report['skills'] = selected
    report['task_type'] = task_type
    report['next_actions'] = [
        'Read each returned original SKILL.md and its required references using your available file or browser tools; record the paths and commits actually read.',
        'Check skill scope, current project instructions and the operator goal before applying the procedure; follow local authority and permission boundaries.',
        'Inspect the target project and establish observable acceptance criteria before edits; ask only for essential missing decisions or authorization.',
        'Execute only supported authorized actions; verify real outputs, record decisions and evidence, and leave a durable handoff.']
    if task_type == 'unknown':
        report['status'] = 'needs-context'
        report['next_actions'].insert(0, 'Establish the operator goal, task stage and target project before choosing an implementation route.')
    if task_type == 'planning':
        report['next_actions'].insert(0, 'Wayfinder is for large multi-session work; use a short scoped plan instead when this task is small.')
    if task_type == 'writing':
        report['next_actions'].insert(0, 'Writing-for-agents applies to agent-facing instructions; for another audience, use technical-writing and select an audience-appropriate procedure.')
    return report


def inventory() -> dict:
    manifest = snapshot_sources.verify(ROOT)
    sources = {}
    skills = []
    for name, source in manifest['sources'].items():
        sources[name] = {'commit': source['commit_sha'], 'scope_tree_sha': source['scope_tree_sha'],
                         'directory': source['directory'], 'file_count': len(source['files'])}
        for path, record in sorted(source['files'].items()):
            if path == 'SKILL.md' or path.endswith('/SKILL.md'):
                skills.append({'path': source['directory'] + '/' + path, 'source': name,
                               'commit': source['commit_sha'], 'git_blob_sha': record['git_blob_sha']})
    return {'schema': 1, 'status': 'verified', 'sources': sources, 'skills': skills,
            'path_base': 'Assimilation repository root, not the target project',
            'skills_loaded': False,
            'capabilities': {
                'python': {'status': 'observed-running', 'version': '.'.join(map(str, sys.version_info[:3]))},
                'git': {'status': 'on-path-not-executed' if shutil.which('git') else 'not-found-on-path'},
                'network': {'status': 'not-probed'},
                'browser': {'status': 'unknown'},
                'delegation': {'status': 'unknown'},
                'target_project': {'status': 'not-inspected'},
                'tracker': {'status': 'unknown'}},
            'next_actions': [
                'Read START_HERE.md and the target project instructions within granted access.',
                'Inspect your actual host tool catalog and record observed capabilities, unavailable tools and unknowns.',
                'Choose a task type with route; read each returned original SKILL.md and required references yourself.',
                'Record project context, authority boundaries, decisions and evidence; this helper grants no permissions.']}


class MissingSkill(Exception):
    pass


class Arguments(argparse.ArgumentParser):
    def error(self, message):
        # argparse's default error echoes arbitrary user-supplied argument values.
        raise ValueError('invalid-arguments')


def main() -> int:
    parser = Arguments(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('inspect')
    choose = commands.add_parser('route')
    choose.add_argument('--task-type', required=True, choices=tuple(ROUTES))
    try:
        args = parser.parse_args()
    except ValueError:
        print(json.dumps({'schema': 1, 'status': 'blocked', 'error': 'invalid-arguments',
                          'next_action': 'Use inspect or route --task-type bug|feature|review|planning|writing|unknown.'}))
        return 2
    try:
        report = inventory()
        if args.command == 'route':
            report = route(report, args.task_type)
    except MissingSkill:
        print(json.dumps({'schema': 1, 'status': 'blocked', 'error': 'route-skill-unavailable',
                          'next_action': 'Inspect the verified inventory and choose an available original skill; do not invent or silently substitute missing source files.'}))
        return 1
    except (RuntimeError, OSError, ValueError, KeyError, TypeError):
        print(json.dumps({'schema': 1, 'status': 'blocked', 'error': 'source-verification-failed',
                          'next_action': 'Do not use unverified snapshots. Inspect sources.lock.json and sources.snapshot.json; restore reviewed files without bypassing verification.'}))
        return 1
    print(json.dumps(report, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
