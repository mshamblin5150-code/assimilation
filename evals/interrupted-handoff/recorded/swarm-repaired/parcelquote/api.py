"""In-memory batch quotation API."""


from copy import deepcopy

from .pricing import quote


class QuoteService:
    def __init__(self):
        self._batches = {}

    def quote_batch(self, batch_id, orders):
        if not isinstance(batch_id, str) or not batch_id or not isinstance(orders, list):
            raise ValueError('invalid batch')
        seen = set()
        quotes = []
        for order in orders:
            if not isinstance(order, dict) or set(order) not in ({'order_id', 'items'}, {'order_id', 'items', 'coupon'}):
                raise ValueError('invalid order')
            order_id = order['order_id']
            if not isinstance(order_id, str) or not order_id or order_id in seen:
                raise ValueError('invalid order id')
            seen.add(order_id)
            quotes.append({'order_id': order_id, **quote(order['items'], order.get('coupon'))})
        if batch_id in self._batches:
            previous, result = self._batches[batch_id]
            if orders != previous:
                raise ValueError('batch id already used')
            return deepcopy(result)
        result = {'batch_id': batch_id, 'quotes': quotes}
        self._batches[batch_id] = (deepcopy(orders), deepcopy(result))
        return result
