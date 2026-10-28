"""JSON stdin/stdout adapter for batch quotations."""
import json
import sys

from .api import QuoteService


def main():
    try:
        request = json.load(sys.stdin)
        if not isinstance(request, dict) or set(request) != {'batch_id', 'orders'}:
            raise ValueError('invalid request shape')
        result = QuoteService().quote_batch(request['batch_id'], request['orders'])
    except ValueError:
        print(json.dumps({'error': 'invalid_request'}))
        return 2
    print(json.dumps(result))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
