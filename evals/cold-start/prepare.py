"""Create a fresh synthetic trial directory; never overwrite existing work."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

parser = argparse.ArgumentParser()
parser.add_argument('trial', type=Path)
args = parser.parse_args()
trial = args.trial.resolve()
trial.mkdir(parents=True, exist_ok=False)
project = trial / 'project'
shutil.copytree(Path(__file__).resolve().parent / 'fixture', project)
(trial / 'before.json').write_text(json.dumps({p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                            for p in project.iterdir() if p.is_file()}, indent=2))
print(project)
