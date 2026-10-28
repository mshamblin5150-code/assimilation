"""In-memory batch quotations."""
from copy import deepcopy

from .pricing import quote


class QuoteService:
    def __init__(self):
        self._batches = {}

    def quote_batch(self, batch_id, orders):
        if not isinstance(batch_id, str) or not batch_id:
            raise ValueError('invalid batch ID')
        if not isinstance(orders, list):
            raise ValueError('orders must be a list')
        seen = set()
        for order in orders:
            if (not isinstance(order, dict)
                    or not {'order_id', 'items'} <= set(order)
                    or set(order) - {'order_id', 'items', 'coupon'}):
                raise ValueError('invalid order shape')
            order_id = order['order_id']
            if not isinstance(order_id, str) or not order_id or order_id in seen:
                raise ValueError('invalid or duplicate order ID')
            seen.add(order_id)
        quotes = [{'order_id': order['order_id'],
                   **quote(order['items'], order.get('coupon'))} for order in orders]
        if batch_id in self._batches:
            request, response = self._batches[batch_id]
            if request != orders:
                raise ValueError('conflicting batch retry')
            return deepcopy(response)
        response = {'batch_id': batch_id, 'quotes': quotes}
        self._batches[batch_id] = (deepcopy(orders), deepcopy(response))
        return deepcopy(response)
