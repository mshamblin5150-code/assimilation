import json
import subprocess
import sys
import unittest
from pathlib import Path


class CliTests(unittest.TestCase):
    def invoke(self, request):
        return subprocess.run([sys.executable, '-m', 'parcelquote'], input=request, text=True, capture_output=True, cwd=Path(__file__).resolve().parents[1])

    def test_success_result_and_exit_code(self):
        result = self.invoke('{"batch_id":"b","orders":[{"order_id":"a","items":[{"unit_cents":100,"quantity":2}]}]}')
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, '')
        self.assertEqual(json.loads(result.stdout), {'batch_id': 'b', 'quotes': [{'order_id': 'a', 'subtotal_cents': 200, 'discount_cents': 0, 'shipping_cents': 499, 'total_cents': 699}]})

    def test_invalid_requests_have_exact_error_and_no_traceback(self):
        for request in ['', '{', '{}', '[]', 'null', '{"batch_id":"b","orders":[],"extra":1}',
                        '{"batch_id":"b","orders":[{"order_id":"a","items":null}]}',
                        '{"batch_id":"b","orders":[]} {}']:
            with self.subTest(request=request):
                result = self.invoke(request)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stderr, '')
                self.assertEqual(json.loads(result.stdout), {'error': 'invalid_request'})
