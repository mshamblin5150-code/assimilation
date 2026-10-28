import json
from pathlib import Path
import subprocess
import sys
import unittest


class CliTests(unittest.TestCase):
    def run_cli(self, raw):
        return subprocess.run([sys.executable, '-m', 'parcelquote'], input=raw,
                              text=True, capture_output=True,
                              cwd=Path(__file__).resolve().parents[1], timeout=5)

    def test_valid_request_prints_single_result(self):
        result = self.run_cli(json.dumps({'batch_id': 'cli', 'orders': [
            {'order_id': 'a', 'items': [{'unit_cents': 19, 'quantity': 2}], 'coupon': 'SAVE10'}]}))
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, '')
        self.assertEqual(json.loads(result.stdout), {'batch_id': 'cli', 'quotes': [
            {'order_id': 'a', 'subtotal_cents': 38, 'discount_cents': 3,
             'shipping_cents': 499, 'total_cents': 534}]})

    def test_invalid_json_shape_and_api_errors_are_clean(self):
        for raw in ('', '{', '{} {}', 'null', '[]', '42', 'true', '"text"', '{}',
                    '{"batch_id":"b"}', '{"orders":[]}',
                    '{"batch_id":"b","orders":[],"extra":1}',
                    '{"batch_id":"","orders":[]}',
                    '{"batch_id":"b","orders":null}',
                    '{"batch_id":"b","orders":[{"order_id":"a","items":[],"coupon":"bad"}]}',
                    '{"batch_id":"b","orders":[{"order_id":"a","items":[]},{"order_id":"a","items":[]}]}'):
            with self.subTest(raw=raw):
                result = self.run_cli(raw)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stderr, '')
                self.assertEqual(json.loads(result.stdout), {'error': 'invalid_request'})
