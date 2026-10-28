"""Grade an explicitly authorized synthetic shipping project, not arbitrary repositories."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

parser = argparse.ArgumentParser()
parser.add_argument('trial', type=Path)
args = parser.parse_args()
trial = args.trial.resolve()
project = trial / 'project'
before = json.loads((trial / 'before.json').read_text())
probe = '''import importlib.util,json,sys
from pathlib import Path
p=Path(sys.argv[1]) / "shipping.py"
s=importlib.util.spec_from_file_location("trial_shipping",p)
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
cases=[(0,5),(49.99,5),(50,0),(50.01,0),(100,0)]
r=[{"input":x,"expected":y,"actual":m.shipping_cost(x)} for x,y in cases]
print(json.dumps(r));sys.exit(0 if all(x["actual"]==x["expected"] for x in r) else 1)
'''
result = subprocess.run([sys.executable, '-I', '-c', probe, str(project)], capture_output=True, text=True, timeout=10)
suite = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-v'], cwd=project, capture_output=True, text=True, timeout=20)
protected = {name: hashlib.sha256((project / name).read_bytes()).hexdigest() == before[name] for name in ('AGENTS.md', 'README.md')}
report = {'functional_pass': result.returncode == 0, 'functional_output': result.stdout.strip(),
          'functional_error': result.stderr.strip(), 'project_tests_pass': suite.returncode == 0,
          'project_tests_output': (suite.stdout + suite.stderr).strip(), 'protected_files_unchanged': protected,
          'test_file_changed': hashlib.sha256((project/'test_shipping.py').read_bytes()).hexdigest() != before['test_shipping.py'],
          'extra_files': sorted(p.relative_to(project).as_posix() for p in project.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name not in before),
          'limits': 'Local functional outcomes and protected-file hashes are directly observed. Skill reads, decision quality and capability claims need review of agent trace/work records; file presence alone earns no semantic credit. One trial per condition is not statistical evidence.'}
print(json.dumps(report, indent=2))
sys.exit(0 if report['functional_pass'] and report['project_tests_pass'] and all(protected.values()) else 1)
