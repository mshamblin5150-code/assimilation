"""Harness calibration, not evidence that a real agent completed the exercise."""
import importlib.util
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / 'evals' / 'interrupted-handoff'
spec = importlib.util.spec_from_file_location('handoff_grade', EVAL / 'grade.py')
grader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(grader)
prepare_spec = importlib.util.spec_from_file_location('handoff_prepare', EVAL / 'prepare.py')
preparer = importlib.util.module_from_spec(prepare_spec)
prepare_spec.loader.exec_module(preparer)

# Deliberately separate calibration implementation; never copied to agent sessions.
PRICING = '''
def legacy_total(prices):
    return sum(prices)

def quote(items, coupon=None):
    if not isinstance(items, list) or not (coupon is None or type(coupon) is str and coupon == 'SAVE10'):
        raise ValueError()
    subtotal = 0
    for line in items:
        if not isinstance(line, dict) or set(line) != {'unit_cents', 'quantity'}:
            raise ValueError()
        cents, quantity = line['unit_cents'], line['quantity']
        if type(cents) is not int or type(quantity) is not int or cents < 0 or quantity <= 0:
            raise ValueError()
        subtotal += cents * quantity
    discount = subtotal // 10 if coupon else 0
    shipping = 0 if not items or subtotal - discount >= 5000 else 499
    return dict(subtotal_cents=subtotal, discount_cents=discount,
                shipping_cents=shipping, total_cents=subtotal-discount+shipping)
'''
API = '''
from copy import deepcopy
from .pricing import quote

class QuoteService:
    def __init__(self):
        self.cache = {}

    def quote_batch(self, batch_id, orders):
        if not isinstance(batch_id, str) or not batch_id or not isinstance(orders, list):
            raise ValueError()
        seen, quotes = set(), []
        for order in orders:
            if not isinstance(order, dict) or set(order) not in (
                {'order_id', 'items'}, {'order_id', 'items', 'coupon'}):
                raise ValueError()
            oid = order['order_id']
            if not isinstance(oid, str) or not oid or oid in seen:
                raise ValueError()
            seen.add(oid)
            quotes.append(dict(order_id=oid, **quote(order['items'], order.get('coupon'))))
        if batch_id in self.cache:
            before, response = self.cache[batch_id]
            if before != orders:
                raise ValueError()
            return deepcopy(response)
        response = dict(batch_id=batch_id, quotes=quotes)
        self.cache[batch_id] = deepcopy((orders, response))
        return response
'''
CLI = '''
import json
import sys
from .api import QuoteService
if hasattr(sys, 'set_int_max_str_digits'):
    sys.set_int_max_str_digits(0)
try:
    request = json.load(sys.stdin)
    if not isinstance(request, dict) or set(request) != {'batch_id', 'orders'}:
        raise ValueError()
    result = QuoteService().quote_batch(**request)
except (ValueError, RecursionError):
    print(json.dumps({'error': 'invalid_request'}))
    sys.exit(2)
print(json.dumps(result))
'''

class HandoffHarnessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name) / 'project'
        shutil.copytree(EVAL / 'fixture', self.project)

    def install_core(self, source=PRICING):
        (self.project / 'parcelquote/pricing.py').write_text(source)

    def install_solution(self):
        self.install_core()
        (self.project / 'parcelquote/api.py').write_text(API)
        (self.project / 'parcelquote/__main__.py').write_text(CLI)

    def test_prepare_refuses_overwrite_and_preserves_existing(self):
        original = (self.project / 'PROJECT_BRIEF.md').read_bytes()
        with self.assertRaises(FileExistsError):
            preparer.prepare(self.project)
        self.assertEqual((self.project / 'PROJECT_BRIEF.md').read_bytes(), original)

    def test_explicit_swarm_mode_uses_distinct_protected_baseline(self):
        swarm = Path(self.temp.name) / 'swarm'
        preparer.prepare(swarm, mode='swarm')
        self.project = swarm
        self.install_solution()
        self.assertTrue(grader.grade(swarm, mode='swarm')['passed'])
        self.assertFalse(grader.grade(swarm)['passed'])

    def test_initial_fixture_fails_behavior_and_checkpoint(self):
        result = grader.grade(self.project)
        self.assertFalse(result['passed'])
        self.assertFalse(result['checkpoint'])
        self.assertFalse(result['groups']['core'])
        self.assertTrue(any(c['passed'] and c['name'] == 'legacy_regression' for c in result['checks']))

    def test_actual_core_checkpoint_is_not_completion(self):
        self.install_core()
        result = grader.grade(self.project, 'checkpoint')
        self.assertTrue(result['passed'], result)
        self.assertFalse(result['complete'])
        self.assertFalse(grader.grade(self.project)['passed'])

    def test_known_complete_solution_passes(self):
        self.install_solution()
        result = grader.grade(self.project)
        self.assertTrue(result['passed'], result)
        self.assertFalse(result['checkpoint'])

    def test_session1_retry_decision_is_behaviorally_enforced(self):
        self.install_solution()
        self.assertTrue(grader.grade(self.project, retry_policy='distinct')['passed'])
        self.assertFalse(grader.grade(self.project, retry_policy='equivalent')['passed'])

    def test_retry_boolean_validation_bypass_rejected(self):
        self.install_solution()
        # Move the cache lookup ahead of request validation to recreate the bug.
        block = API[API.index('        if batch_id in self.cache:'):API.index('        response = dict')]
        broken = API.replace(block, '').replace('        seen, quotes = set(), []', block + '        seen, quotes = set(), []')
        (self.project / 'parcelquote/api.py').write_text(broken)
        result = grader.grade(self.project)
        self.assertFalse(result['passed'])
        self.assertTrue(any(not c['passed'] and c['name'] == 'retry_still_validates_domain_types' for c in result['checks']))

    def test_partial_batch_cache_rejected_after_late_invalid_order(self):
        self.install_solution()
        broken = API.replace('        seen, quotes = set(), []', """        if all(isinstance(o, dict) and isinstance(o.get('order_id'), str) for o in orders):
            ids = [o['order_id'] for o in orders]
            if len(ids) != len(set(ids)):
                raise ValueError()
        new_batch = batch_id not in self.cache
        seen, quotes = set(), []""").replace(
            "            quotes.append(dict(order_id=oid, **quote(order['items'], order.get('coupon'))))",
            """            quotes.append(dict(order_id=oid, **quote(order['items'], order.get('coupon'))))
            if new_batch:
                self.cache[batch_id] = deepcopy((orders, dict(batch_id=batch_id, quotes=quotes)))""")
        (self.project / 'parcelquote/api.py').write_text(broken)
        result = grader.grade(self.project)
        self.assertFalse(result['passed'])
        self.assertTrue(any(not c['passed'] and c['name'] == 'late_invalid_order_is_atomic' for c in result['checks']))

    def test_cli_large_valid_product_serialization_failure_rejected(self):
        self.install_solution()
        # Model a 4300-digit serialization cap independently of Python version.
        broken = CLI.replace('print(json.dumps(result))', """if any(q['total_cents'] >= 10**4300 for q in result['quotes']):
    raise ValueError('serialization digit limit')
print(json.dumps(result))""")
        (self.project / 'parcelquote/__main__.py').write_text(broken)
        result = grader.grade(self.project)
        self.assertFalse(result['passed'])
        self.assertTrue(any(not c['passed'] and c['name'] == 'large_integer_product' for c in result['checks']))

    def test_cli_deep_invalid_json_failure_rejected(self):
        self.install_solution()
        broken = CLI.replace('except (ValueError, RecursionError):', 'except ValueError:')
        (self.project / 'parcelquote/__main__.py').write_text(broken)
        result = grader.grade(self.project)
        self.assertFalse(result['passed'])
        self.assertTrue(any(not c['passed'] and c['name'] == 'deep_invalid_request' for c in result['checks']))

    def test_wrong_shipping_decision_rejected(self):
        self.install_solution()
        self.install_core(PRICING.replace('subtotal - discount >= 5000', 'subtotal >= 5000'))
        result = grader.grade(self.project)
        self.assertFalse(result['passed'])
        self.assertTrue(any(not c['passed'] and c['name'] == 'post_discount_threshold' for c in result['checks']))

    def test_wrong_rounding_decision_rejected(self):
        self.install_solution()
        self.install_core(PRICING.replace('subtotal // 10', 'round(subtotal / 10)'))
        self.assertFalse(grader.grade(self.project)['passed'])

    def test_protected_drift_rejected_despite_correct_behavior(self):
        self.install_solution()
        with (self.project / 'PROJECT_BRIEF.md').open('a') as out:
            out.write('\nUnauthorized decision change.\n')
        result = grader.grade(self.project)
        self.assertTrue(all(result['groups'].values()))
        self.assertFalse(result['passed'])

    def test_broken_replay_rejected(self):
        self.install_solution()
        (self.project / 'parcelquote/api.py').write_text(API.replace('return deepcopy(response)', 'return response'))
        # First reply isolation also requires stored values not to alias replies.
        text = (self.project / 'parcelquote/api.py').read_text()
        (self.project / 'parcelquote/api.py').write_text(text.replace('deepcopy((orders, response))', '(orders, response)'))
        self.assertFalse(grader.grade(self.project)['passed'])

    def test_failing_project_suite_rejects_correct_oracle_behavior(self):
        self.install_solution()
        (self.project / 'tests/test_failure.py').write_text('import unittest\nclass Failure(unittest.TestCase):\n def test_failure(self): self.fail("synthetic")\n')
        result = grader.grade(self.project)
        self.assertTrue(all(result['groups'].values()))
        self.assertFalse(result['passed'])

    def test_nested_float_money_rejected(self):
        self.install_solution()
        broken = API.replace('response = dict(batch_id=batch_id, quotes=quotes)',
            'quotes = [{k: float(v) if type(v) is int else v for k, v in q.items()} for q in quotes]\n        response = dict(batch_id=batch_id, quotes=quotes)')
        (self.project / 'parcelquote/api.py').write_text(broken)
        self.assertFalse(grader.grade(self.project)['passed'])

    def test_cached_retry_response_alias_rejected(self):
        self.install_solution()
        (self.project / 'parcelquote/api.py').write_text(API.replace('return deepcopy(response)', 'return response'))
        self.assertFalse(grader.grade(self.project)['passed'])

    def test_prose_claim_does_not_substitute_for_behavior(self):
        (self.project / 'RUN_RECORD.md').write_text('All tests passed. Feature complete. Decisions preserved.')
        self.assertFalse(grader.grade(self.project)['passed'])

if __name__ == '__main__':
    unittest.main()
