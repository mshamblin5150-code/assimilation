# Coordinator-assisted post-evaluation CLI repair

This synthetic-only repair is not fresh-agent original success. Original independent challenge failures remain evaluation evidence. Only CLI implementation changed; independent tests were not edited. Protected instructions and contract remain unchanged.

Read original Matt Pocock TDD plus tests/mocking references, P-Stack prove-it-works and test-behavior-not-implementation. Approved seam: real JSON stdin/stdout CLI subprocess; asserts output, status and absence of traceback, not private helpers.

## Before CLI
```python
"""One-request JSON stdin/stdout adapter."""
import json
import sys

from .api import QuoteService


def main():
    try:
        request = json.load(sys.stdin)
        if not isinstance(request, dict) or set(request) != {'batch_id', 'orders'}:
            raise ValueError('invalid request')
        result = QuoteService().quote_batch(request['batch_id'], request['orders'])
    except ValueError:
        print(json.dumps({'error': 'invalid_request'}))
        return 2
    print(json.dumps(result))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
```

## Slice 1: unrestricted contract integers

Command: `python -B -m unittest discover -s tests -p test_challenge.py -k test_cli_valid_large_integer_product_emits_success -v`

```text
test_cli_valid_large_integer_product_emits_success (test_challenge.ChallengeTests.test_cli_valid_large_integer_product_emits_success) ... FAIL

======================================================================
FAIL: test_cli_valid_large_integer_product_emits_success (test_challenge.ChallengeTests.test_cli_valid_large_integer_product_emits_success)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/workspace/scratch/b6810fbd29e0/assimilation-handoff-evidence/trial-b/tests/test_challenge.py", line 63, in test_cli_valid_large_integer_product_emits_success
    self.assertEqual(result.returncode, 0, result.stderr)
AssertionError: 1 != 0 : Traceback (most recent call last):
  File "<frozen runpy>", line 198, in _run_module_as_main
  File "<frozen runpy>", line 88, in _run_code
  File "/workspace/scratch/b6810fbd29e0/assimilation-handoff-evidence/trial-b/parcelquote/__main__.py", line 22, in <module>
    raise SystemExit(main())
                     ^^^^^^
  File "/workspace/scratch/b6810fbd29e0/assimilation-handoff-evidence/trial-b/parcelquote/__main__.py", line 17, in main
    print(json.dumps(result))
          ^^^^^^^^^^^^^^^^^^
  File "/opt/codex/runtimes/codex-primary-runtime/dependencies/python/lib/python3.12/json/__init__.py", line 231, in dumps
    return _default_encoder.encode(obj)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/codex/runtimes/codex-primary-runtime/dependencies/python/lib/python3.12/json/encoder.py", line 200, in encode
    chunks = self.iterencode(o, _one_shot=True)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/codex/runtimes/codex-primary-runtime/dependencies/python/lib/python3.12/json/encoder.py", line 258, in iterencode
    return _iterencode(o, 0)
           ^^^^^^^^^^^^^^^^^
ValueError: Exceeds the limit (4300 digits) for integer string conversion; use sys.set_int_max_str_digits() to increase the limit


----------------------------------------------------------------------
Ran 1 test in 0.027s

FAILED (failures=1)
Exit: 1
```

Command: `python -B -m unittest discover -s tests -p test_challenge.py -k test_cli_valid_large_integer_product_emits_success -v`

```text
test_cli_valid_large_integer_product_emits_success (test_challenge.ChallengeTests.test_cli_valid_large_integer_product_emits_success) ... ok

----------------------------------------------------------------------
Ran 1 test in 0.030s

OK
Exit: 0
```

## Slice 2: deeply nested invalid input

Command: `python -B -m unittest discover -s tests -p test_challenge.py -k test_cli_deep_invalid_request_returns_contract_error -v`

```text
test_cli_deep_invalid_request_returns_contract_error (test_challenge.ChallengeTests.test_cli_deep_invalid_request_returns_contract_error) ... ok

----------------------------------------------------------------------
Ran 1 test in 0.039s

OK
Exit: 0
```

Command: `python -B -m unittest discover -s tests -p test_challenge.py -k test_cli_deep_invalid_request_returns_contract_error -v`

```text
test_cli_deep_invalid_request_returns_contract_error (test_challenge.ChallengeTests.test_cli_deep_invalid_request_returns_contract_error) ... ok

----------------------------------------------------------------------
Ran 1 test in 0.026s

OK
Exit: 0
```

Command: `python -B -m unittest discover -s tests -v`

```text
test_cache_is_instance_local_and_invalid_equal_numbers_are_rejected (test_api.BatchTests.test_cache_is_instance_local_and_invalid_equal_numbers_are_rejected) ... ok
test_empty_batch (test_api.BatchTests.test_empty_batch) ... ok
test_failed_batch_does_not_reserve_id (test_api.BatchTests.test_failed_batch_does_not_reserve_id) ... ok
test_invalid_batch_shapes_raise_value_error (test_api.BatchTests.test_invalid_batch_shapes_raise_value_error) ... ok
test_order_shapes_and_unique_ids (test_api.BatchTests.test_order_shapes_and_unique_ids) ... ok
test_quotes_preserve_order_and_prices (test_api.BatchTests.test_quotes_preserve_order_and_prices) ... ok
test_request_and_response_mutation_do_not_corrupt_retry (test_api.BatchTests.test_request_and_response_mutation_do_not_corrupt_retry) ... ok
test_retry_equal_input_and_reject_changed_input (test_api.BatchTests.test_retry_equal_input_and_reject_changed_input) ... ok
test_cli_deep_invalid_request_returns_contract_error (test_challenge.ChallengeTests.test_cli_deep_invalid_request_returns_contract_error) ... ok
test_cli_valid_large_integer_product_emits_success (test_challenge.ChallengeTests.test_cli_valid_large_integer_product_emits_success) ... ok
test_late_failure_retry_and_conflict_preserve_committed_result (test_challenge.ChallengeTests.test_late_failure_retry_and_conflict_preserve_committed_result) ... ok
test_legacy_generator_negative_fractional (test_challenge.ChallengeTests.test_legacy_generator_negative_fractional) ... ok
test_nested_mutations_and_item_list_order (test_challenge.ChallengeTests.test_nested_mutations_and_item_list_order) ... ok
test_partitioned_rounding_and_quantity_threshold (test_challenge.ChallengeTests.test_partitioned_rounding_and_quantity_threshold) ... ok
test_invalid_requests_have_exact_error_and_no_traceback (test_cli.CliTests.test_invalid_requests_have_exact_error_and_no_traceback) ... ok
test_success_result_and_exit_code (test_cli.CliTests.test_success_result_and_exit_code) ... ok
test_legacy_sum (test_legacy.LegacyTests.test_legacy_sum) ... ok
test_delivery_threshold_uses_discounted_total (test_pricing.PricingTests.test_delivery_threshold_uses_discounted_total) ... ok
test_discount_floors_whole_subtotal (test_pricing.PricingTests.test_discount_floors_whole_subtotal) ... ok
test_empty_order_is_free_but_nonempty_zero_order_pays_delivery (test_pricing.PricingTests.test_empty_order_is_free_but_nonempty_zero_order_pays_delivery) ... ok
test_invalid_item_shapes_raise_value_error (test_pricing.PricingTests.test_invalid_item_shapes_raise_value_error) ... ok
test_item_numbers_are_domain_integers (test_pricing.PricingTests.test_item_numbers_are_domain_integers) ... ok
test_large_integer_quote_has_exact_integer_results (test_pricing.PricingTests.test_large_integer_quote_has_exact_integer_results) ... ok
test_legacy_still_sums_empty_negative_fractional_and_generator_inputs (test_pricing.PricingTests.test_legacy_still_sums_empty_negative_fractional_and_generator_inputs) ... ok
test_line_quantities_and_standard_delivery (test_pricing.PricingTests.test_line_quantities_and_standard_delivery) ... ok
test_only_exact_coupon_is_accepted_even_for_empty_items (test_pricing.PricingTests.test_only_exact_coupon_is_accepted_even_for_empty_items) ... ok

----------------------------------------------------------------------
Ran 26 tests in 0.286s

OK
Exit: 0
```

## Scope and limits
Python decimal conversion limits are disabled only on execution as a one-shot CLI; importing main leaves the host policy unchanged. This preserves the specified unbounded integer domain, including a 4301-digit output, but removes a resource-protection limit in that subprocess. This is **not** production or security hardening. Production magnitude/resource caps require a separate approved contract decision. RecursionError joins ValueError at the CLI adapter boundary, yielding the specified invalid-request response for deeply nested invalid JSON shapes. No changes to pricing, cache semantics, tests, production systems, or approval holds.

### Corrected deep-input evidence
The independent depth-1200 example was already green before the exception change on this runtime; it does not demonstrate a regression. Reverted that exception change, then used the same approved subprocess CLI seam with depth 10000, below. No independent test modified.

Depth-10000 CLI red; input: `"[" * 10000 + "0" + "]" * 10000`
```text
stdout: 
stderr: Traceback (most recent call last):
  File "<frozen runpy>", line 198, in _run_module_as_main
  File "<frozen runpy>", line 88, in _run_code
  File "/workspace/scratch/b6810fbd29e0/assimilation-handoff-evidence/trial-b/parcelquote/__main__.py", line 26, in <module>
    raise SystemExit(main())
                     ^^^^^^
  File "/workspace/scratch/b6810fbd29e0/assimilation-handoff-evidence/trial-b/parcelquote/__main__.py", line 10, in main
    request = json.load(sys.stdin)
              ^^^^^^^^^^^^^^^^^^^^
  File "/opt/codex/runtimes/codex-primary-runtime/dependencies/python/lib/python3.12/json/__init__.py", line 293, in load
    return loads(fp.read(),
           ^^^^^^^^^^^^^^^^
  File "/opt/codex/runtimes/codex-primary-runtime/dependencies/python/lib/python3.12/json/__init__.py", line 346, in loads
    return _default_decoder.decode(s)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/codex/runtimes/codex-primary-runtime/dependencies/python/lib/python3.12/json/decoder.py", line 338, in decode
    obj, end = self.raw_decode(s, idx=_w(s, 0).end())
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/codex/runtimes/codex-primary-runtime/dependencies/python/lib/python3.12/json/decoder.py", line 354, in raw_decode
    obj, end = self.scan_once(s, idx)
               ^^^^^^^^^^^^^^^^^^^^^^
RecursionError: maximum recursion depth exceeded while decoding a JSON array from a unicode string

exit: 1
```

Depth-10000 CLI green; input: `"[" * 10000 + "0" + "]" * 10000`
```text
stdout: {"error": "invalid_request"}

stderr: 
exit: 2
```

## Import policy check
`python -B -c "import sys; before=sys.get_int_max_str_digits(); import parcelquote.__main__; assert sys.get_int_max_str_digits()==before; print(before)"`
```text
Import preserves int conversion policy: 4300
Exit: 0
```

## Re-runnable public-seam verification
Run from this project directory:
```sh
python -B - <<'PY'
import json, subprocess, sys
raw = '{"batch_id":"large","orders":[{"order_id":"a","items":[{"unit_cents":' + '9' * 4300 + ',"quantity":10}]}]}'
r = subprocess.run([sys.executable, '-B', '-m', 'parcelquote'], input=raw, text=True, capture_output=True, timeout=5)
assert r.returncode == 0 and r.stderr == '', (r.returncode, r.stderr)
assert json.loads(r.stdout, parse_int=str) == {'batch_id': 'large', 'quotes': [{'order_id': 'a', 'subtotal_cents': '9' * 4300 + '0', 'discount_cents': '0', 'shipping_cents': '0', 'total_cents': '9' * 4300 + '0'}]}
r = subprocess.run([sys.executable, '-B', '-m', 'parcelquote'], input='[' * 10000 + '0' + ']' * 10000, text=True, capture_output=True, timeout=5)
assert r.returncode == 2 and r.stderr == '', (r.returncode, r.stderr)
assert json.loads(r.stdout) == {'error': 'invalid_request'}
before = sys.get_int_max_str_digits()
import parcelquote.__main__
assert sys.get_int_max_str_digits() == before
print('PASS: exact large-integer result, deep-invalid error, unchanged import policy')
PY
```
Observed:
```text
PASS: exact large-integer result, deep-invalid error, unchanged import policy
Exit: 0
```
