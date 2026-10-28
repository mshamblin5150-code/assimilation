"""Independent literal oracle. Executed in a subprocess against a synthetic project."""
import copy
import importlib
import json
from pathlib import Path
import subprocess
import sys


def run(project, retry_policy=None):
    sys.path.insert(0, str(project))
    checks = []

    def check(group, name, operation):
        try:
            operation()
        except Exception as exc:
            checks.append({'group': group, 'name': name, 'passed': False,
                           'detail': type(exc).__name__ + ': ' + str(exc)[:300]})
        else:
            checks.append({'group': group, 'name': name, 'passed': True})

    def equal(actual, expected):
        assert actual == expected, f'{actual!r} != {expected!r}'
        if type(expected) is int:
            assert type(actual) is int, 'integer result required'
        elif isinstance(expected, dict):
            for key, value in expected.items():
                equal(actual[key], value)
        elif isinstance(expected, list):
            for actual_item, expected_item in zip(actual, expected):
                equal(actual_item, expected_item)

    def rejects(fn):
        try:
            fn()
        except ValueError:
            return
        raise AssertionError('expected ValueError')

    def price(items, coupon, expected):
        from parcelquote.pricing import quote
        before = copy.deepcopy(items)
        equal(quote(items, coupon), dict(zip(
            ['subtotal_cents', 'discount_cents', 'shipping_cents', 'total_cents'], expected)))
        equal(items, before)

    item = lambda cents, qty=1: {'unit_cents': cents, 'quantity': qty}
    cases = [
        ('empty', [], None, (0, 0, 0, 0)),
        ('nonempty_free_item', [item(0)], None, (0, 0, 499, 499)),
        ('threshold_below', [item(4999)], None, (4999, 0, 499, 5498)),
        ('threshold_equal', [item(5000)], None, (5000, 0, 0, 5000)),
        ('post_discount_threshold', [item(5500)], 'SAVE10', (5500, 550, 499, 5449)),
        ('discount_threshold_equal', [item(5555)], 'SAVE10', (5555, 555, 0, 5000)),
        ('aggregate_floor', [item(19), item(19)], 'SAVE10', (38, 3, 499, 534)),
        ('quantity', [item(199, 3)], 'SAVE10', (597, 59, 499, 1037)),
        ('large_integer', [item(10**18 + 9)], 'SAVE10',
         (1000000000000000009, 100000000000000000, 0, 900000000000000009)),
    ]
    for name, items, coupon, expected in cases:
        check('core', name, lambda i=items, c=coupon, e=expected: price(i, c, e))

    def legacy():
        from parcelquote.pricing import legacy_total
        equal(legacy_total(iter([1.5, -2, 5])), 4.5)
        equal(legacy_total([]), 0)
    check('core', 'legacy_regression', legacy)
    bad_items = [None, {}, 'x', [None], [{'unit_cents': 1}], [item(-1)],
                 [item(True)], [item(1.0)], [item(1, False)], [item(1, 0)],
                 [item(1, -2)], [item(1, 1.5)], [dict(item(1), extra=1)]]
    for index, items in enumerate(bad_items):
        def bad(items=items):
            from parcelquote.pricing import quote
            rejects(lambda: quote(items))
        check('core', f'invalid_items_{index}', bad)
    for coupon in ['', 'save10', False, 0, [], {}]:
        def bad_coupon(coupon=coupon):
            from parcelquote.pricing import quote
            rejects(lambda: quote([], coupon))
        check('core', f'invalid_coupon_{coupon!r}', bad_coupon)

    orders = [{'order_id': 'synthetic-A', 'items': [item(5500)], 'coupon': 'SAVE10'},
              {'order_id': 'synthetic-B', 'items': []}]
    expected = {'batch_id': 'synthetic-batch', 'quotes': [
        {'order_id': 'synthetic-A', 'subtotal_cents': 5500, 'discount_cents': 550,
         'shipping_cents': 499, 'total_cents': 5449},
        {'order_id': 'synthetic-B', 'subtotal_cents': 0, 'discount_cents': 0,
         'shipping_cents': 0, 'total_cents': 0}]}
    def service():
        from parcelquote.api import QuoteService
        return QuoteService()
    def batch_success():
        s = service()
        equal(s.quote_batch('synthetic-batch', copy.deepcopy(orders)), expected)
        equal(s.quote_batch('empty', []), {'batch_id': 'empty', 'quotes': []})
    check('api', 'batch_values_and_order', batch_success)

    def replay():
        s = service()
        request = copy.deepcopy(orders)
        response = s.quote_batch('synthetic-batch', request)
        response['quotes'][0]['total_cents'] = -1
        request[0]['items'][0]['unit_cents'] = 7
        reordered = [{k: o[k] for k in reversed(o)} for o in orders]
        retry_response = s.quote_batch('synthetic-batch', reordered)
        equal(retry_response, expected)
        retry_response['quotes'][0]['total_cents'] = -2
        equal(s.quote_batch('synthetic-batch', reordered), expected)
        rejects(lambda: s.quote_batch('synthetic-batch', request))
        rejects(lambda: s.quote_batch('synthetic-batch', list(reversed(orders))))
        equal(service().quote_batch('synthetic-batch', []),
              {'batch_id': 'synthetic-batch', 'quotes': []})
    check('api', 'replay_conflict_mutation_and_instance_isolation', replay)

    def retry_validation():
        s = service()
        valid = [{'order_id': 'one', 'items': [item(1)]}]
        s.quote_batch('retry-validation', valid)
        # Python bool/int equality must not bypass domain validation on retries.
        for field in ('unit_cents', 'quantity'):
            invalid = copy.deepcopy(valid)
            invalid[0]['items'][0][field] = True
            rejects(lambda: s.quote_batch('retry-validation', invalid))
    check('api', 'retry_still_validates_domain_types', retry_validation)

    if retry_policy is not None:
        def retry_coupon_policy():
            s = service()
            omitted = [{'order_id': 'choice', 'items': []}]
            explicit = [dict(omitted[0], coupon=None)]
            first = s.quote_batch('decision', omitted)
            if retry_policy == 'equivalent':
                equal(s.quote_batch('decision', explicit), first)
            else:
                rejects(lambda: s.quote_batch('decision', explicit))
        check('api', 'preserved_session1_retry_policy_' + retry_policy, retry_coupon_policy)

    def late_invalid_order():
        s = service()
        invalid = [orders[0], {'order_id': 'late-invalid', 'items': [item(-1)]}]
        rejects(lambda: s.quote_batch('synthetic-batch', invalid))
        equal(s.quote_batch('synthetic-batch', orders), expected)
    check('api', 'late_invalid_order_is_atomic', late_invalid_order)

    invalid_orders = [None, {}, [None], [{}], [{'order_id': '', 'items': []}],
                      [{'order_id': 1, 'items': []}], [dict(orders[0], extra=True)],
                      [orders[0], orders[0]], [{'order_id': 'x', 'items': [item(-1)]}],
                      [{'order_id': 'x', 'items': [], 'coupon': 'bogus'}]]
    for index, invalid in enumerate(invalid_orders):
        def invalid_batch(invalid=invalid):
            s = service()
            rejects(lambda: s.quote_batch('synthetic-batch', invalid))
            equal(s.quote_batch('synthetic-batch', orders), expected)
        check('api', f'invalid_batch_atomic_{index}', invalid_batch)
    for batch_id in [None, '', 1, True, []]:
        check('api', f'invalid_id_{batch_id!r}',
              lambda b=batch_id: rejects(lambda: service().quote_batch(b, [])))

    def cli(payload, status, result, parse_int=int):
        completed = subprocess.run([sys.executable, '-B', '-m', 'parcelquote'],
            input=payload, text=True, cwd=project, capture_output=True, timeout=5)
        equal(completed.returncode, status)
        equal(json.loads(completed.stdout, parse_int=parse_int), result)
        assert 'Traceback' not in completed.stderr
    check('cli', 'valid_batch', lambda: cli(json.dumps(
        {'batch_id': 'synthetic-batch', 'orders': orders}), 0, expected))
    # Literal decimal-string oracle avoids sharing the interpreter's conversion
    # limit or deriving expectations from the participant's arithmetic.
    huge_digits = '9' * 4300
    large_payload = ('{"batch_id":"large","orders":[{"order_id":"a","items":'
                     '[{"unit_cents":' + huge_digits + ',"quantity":10}]}]}')
    large_expected = {'batch_id': 'large', 'quotes': [{'order_id': 'a',
        'subtotal_cents': ('integer', huge_digits + '0'), 'discount_cents': ('integer', '0'),
        'shipping_cents': ('integer', '0'), 'total_cents': ('integer', huge_digits + '0')}]}
    check('cli', 'large_integer_product',
          lambda: cli(large_payload, 0, large_expected,
                      parse_int=lambda digits: ('integer', digits)))
    check('cli', 'deep_invalid_request', lambda: cli(
        '[' * 10000 + '0' + ']' * 10000, 2, {'error': 'invalid_request'}))
    for payload in ['{', 'null', '[]', '{}',
                    '{"batch_id":"x","orders":[],"extra":true}',
                    '{"batch_id":"x","orders":[{"order_id":"x","items":null}]}']:
        check('cli', f'invalid_request_{payload}', lambda p=payload:
              cli(p, 2, {'error': 'invalid_request'}))
    return checks

if __name__ == '__main__':
    print(json.dumps(run(Path(sys.argv[1]).resolve(), sys.argv[2] if len(sys.argv) > 2 else None), sort_keys=True))
