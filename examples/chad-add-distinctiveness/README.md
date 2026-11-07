# Add Its Distinctiveness to Our Own. offline practice fixture

This is a training-only exercise for Chad's next Assimilation lesson. It builds on
the **synthetic APK** in `examples/chad-reverse-engineering/` and teaches
independent design, not extraction or copying of source code. No connection to
printer hardware or network services exists in these Python files.

- `starter/readiness.py`: unfinished learner interface.
- `starter/test_readiness.py`: public behavioral contract expressed as tests.
- `starter/EXPECTED-RED.txt`: genuinely executed failing run against the stub.
- `instructor/readiness.py`: separately located independent example solution.
- `instructor/test_readiness.py`: matching public-behavior tests.
- `instructor/TEST-RESULTS.txt`: actual authoring-run output (not Chad's run).
- `TRACEABILITY.md`: learner's evidence and design worksheet.

From repository root:

```powershell
python -B -m unittest discover -s examples/chad-add-distinctiveness/starter -p test_readiness.py -v
python -B -m unittest discover -s examples/chad-add-distinctiveness/instructor -p test_readiness.py -v
```

Python 3.12+ is recommended for parity with other Chad practical lessons. The
package was verified independently of GitHub; the integration owner must rerun
it on the actual target branch and label any untested host combinations.


The current learner and instructor suites each contain fifteen tests. The
original eight-test author logs remain unchanged and describe the supplied
package, not the corrected integrated source. [Integration results](RESULTS.md)
link the new evidence. The corrected instructor does not read past the budget.
`evidence/supplied-author/` retains the original source as inert text for review.
The intentionally incomplete learner suite is expected to fail; root repository
validation runs the instructor suite in a separate process instead.
