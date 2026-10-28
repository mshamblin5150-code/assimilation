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
    except (ValueError, RecursionError):
        print(json.dumps({'error': 'invalid_request'}))
        return 2
    print(json.dumps(result))
    return 0


if __name__ == '__main__':
    # The synthetic CLI contract has no integer magnitude cap. Keep this
    # conversion policy inside the one-shot process, not module imports.
    if hasattr(sys, 'set_int_max_str_digits'):
        sys.set_int_max_str_digits(0)
    raise SystemExit(main())
