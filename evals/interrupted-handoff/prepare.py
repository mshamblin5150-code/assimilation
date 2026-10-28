#!/usr/bin/env python3
"""Copy only the synthetic project; never overwrite an existing destination."""
import argparse
from pathlib import Path
import shutil

FIXTURE = Path(__file__).resolve().parent / 'fixture'

def prepare(destination, mode='interrupted'):
    destination = Path(destination)
    if destination.exists():
        raise FileExistsError(destination)
    shutil.copytree(FIXTURE, destination)
    if mode == 'swarm':
        shutil.copyfile(FIXTURE.parent / 'swarm_brief.md', destination / 'PROJECT_BRIEF.md')
    return destination

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path)
    parser.add_argument('--mode', choices=('interrupted', 'swarm'), default='interrupted')
    args = parser.parse_args()
    print(prepare(args.destination, args.mode))
