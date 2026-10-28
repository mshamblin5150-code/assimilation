"""Independent public-seam contract challenges; no internal mocks."""
import json
import subprocess
import sys
import unittest
from copy import deepcopy
from pathlib import Path

from parcelquote.api import QuoteService
from parcelquote.pricing import quote, legacy_total


class ChallengeTests(unittest.TestCase):
    def test_partitioned_rounding_and_quantity_threshold(self):
        self.assertEqual(quote([{'unit_cents': 3, 'quantity': 3}, {'unit_cents': 1, 'quantity': 1}], 'SAVE10'),
                         {'subtotal_cents': 10, 'discount_cents': 1, 'shipping_cents': 499, 'total_cents': 508})
        self.assertEqual(quote([{'unit_cents': 2777, 'quantity': 2}], 'SAVE10'),
                         {'subtotal_cents': 5554, 'discount_cents': 555, 'shipping_cents': 499, 'total_cents': 5498})

    def test_late_failure_retry_and_conflict_preserve_committed_result(self):
        service = QuoteService()
        good = [{'order_id': 'a', 'items': [{'unit_cents': 7, 'quantity': 2}]}]
        for bad in [{'order_id': 'a', 'items': []}, {'order_id': 'b', 'items': [], 'coupon': 'save10'}]:
            with self.assertRaises(ValueError):
                service.quote_batch('batch', good + [bad])
        expected = {'batch_id': 'batch', 'quotes': [{'order_id': 'a', 'subtotal_cents': 14, 'discount_cents': 0, 'shipping_cents': 499, 'total_cents': 513}]}
        self.assertEqual(service.quote_batch('batch', good), expected)
        with self.assertRaises(ValueError):
            service.quote_batch('batch', [])
        self.assertEqual(service.quote_batch('batch', good), expected)

    def test_nested_mutations_and_item_list_order(self):
        service = QuoteService()
        request = [{'order_id': 'a', 'items': [{'unit_cents': 2, 'quantity': 1}, {'unit_cents': 3, 'quantity': 1}]}]
        original = deepcopy(request)
        result = service.quote_batch('b', request)
        expected = {'batch_id': 'b', 'quotes': [{'order_id': 'a', 'subtotal_cents': 5, 'discount_cents': 0, 'shipping_cents': 499, 'total_cents': 504}]}
        request[0]['items'].reverse()
        with self.assertRaises(ValueError):
            service.quote_batch('b', request)
        request.clear()
        result['quotes'][0].clear()
        result['batch_id'] = 'changed'
        self.assertEqual(service.quote_batch('b', original), expected)
        retry = service.quote_batch('b', original)
        retry['quotes'].append({})
        self.assertEqual(service.quote_batch('b', original), expected)

    def test_legacy_generator_negative_fractional(self):
        self.assertEqual(legacy_total(x for x in [-4.5, 1.25, 0.25]), -3)
        self.assertEqual(legacy_total(iter([])), 0)

    def invoke(self, raw):
        return subprocess.run([sys.executable, '-m', 'parcelquote'], input=raw,
                              text=True, capture_output=True, timeout=5,
                              cwd=Path(__file__).resolve().parents[1])

    def test_cli_valid_large_integer_product_emits_success(self):
        # Both input numbers are legal nonnegative/positive integers. Multiplying
        # 4300 nines by ten is 4300 nines followed by a zero: independent oracle.
        raw = '{"batch_id":"large","orders":[{"order_id":"a","items":[{"unit_cents":' + '9' * 4300 + ',"quantity":10}]}]}'
        result = self.invoke(raw)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        parsed = json.loads(result.stdout, parse_int=str)
        self.assertEqual(parsed, {'batch_id': 'large', 'quotes': [{'order_id': 'a',
            'subtotal_cents': '9' * 4300 + '0', 'discount_cents': '0',
            'shipping_cents': '0', 'total_cents': '9' * 4300 + '0'}]})

    def test_cli_deep_invalid_request_returns_contract_error(self):
        # A small (2.4 KB) JSON value, but the top-level list is never valid.
        result = self.invoke('[' * 1200 + '0' + ']' * 1200)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(result.stderr, '')
        self.assertEqual(json.loads(result.stdout), {'error': 'invalid_request'})
