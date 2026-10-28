import unittest
from parcelquote.api import QuoteService


class BatchTests(unittest.TestCase):
    def test_returns_quotes_in_order_and_accepts_empty_batches(self):
        service = QuoteService()
        self.assertEqual(service.quote_batch('empty', []), {'batch_id': 'empty', 'quotes': []})
        self.assertEqual(service.quote_batch('batch', [
            {'order_id': 'z', 'items': [{'unit_cents': 5555, 'quantity': 1}], 'coupon': 'SAVE10'},
            {'order_id': 'a', 'items': []}]), {
                'batch_id': 'batch', 'quotes': [
                    {'order_id': 'z', 'subtotal_cents': 5555, 'discount_cents': 555,
                     'shipping_cents': 0, 'total_cents': 5000},
                    {'order_id': 'a', 'subtotal_cents': 0, 'discount_cents': 0,
                     'shipping_cents': 0, 'total_cents': 0}]})

    def test_invalid_batches_raise_value_error_without_reserving_id(self):
        invalid_orders = [None, {}, (), '', True, [None], [[]], [{}],
            [{'order_id': 'a'}], [{'items': []}],
            [{'order_id': 'a', 'items': [], 'extra': 1}],
            [{'order_id': value, 'items': []} for value in ('a', 'a')]]
        invalid_orders += [[{'order_id': value, 'items': []}]
                           for value in ('', None, 1, True, [], {})]
        invalid_orders += [[{'order_id': 'good', 'items': []}, bad] for bad in (
            {'order_id': 'bad', 'items': None},
            {'order_id': 'bad', 'items': [], 'coupon': 'unknown'},
            {'order_id': 'bad', 'items': [{'unit_cents': True, 'quantity': 1}]})]
        for orders in invalid_orders:
            with self.subTest(orders=orders):
                service = QuoteService()
                with self.assertRaises(ValueError):
                    service.quote_batch('batch', orders)
                self.assertEqual(service.quote_batch('batch', []), {'batch_id': 'batch', 'quotes': []})
        for batch_id in ('', None, 0, True, [], {}):
            with self.subTest(batch_id=batch_id), self.assertRaises(ValueError):
                QuoteService().quote_batch(batch_id, [])

    def test_retry_identity_preserves_raw_shape_and_list_order(self):
        service = QuoteService()
        orders = [{'order_id': 'a', 'items': []}, {'order_id': 'b', 'items': []}]
        expected = service.quote_batch('batch', orders)
        self.assertEqual(service.quote_batch('batch', [
            {'items': [], 'order_id': 'a'}, {'items': [], 'order_id': 'b'}]), expected)
        for changed in (list(reversed(orders)), [],
                        [{'order_id': 'a', 'items': [], 'coupon': None}, orders[1]]):
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                service.quote_batch('batch', changed)
        self.assertEqual(service.quote_batch('batch', orders), expected)
        self.assertEqual(QuoteService().quote_batch('batch', []), {'batch_id': 'batch', 'quotes': []})

    def test_mutations_cannot_change_stored_request_or_response(self):
        service = QuoteService()
        orders = [{'order_id': 'a', 'items': [{'unit_cents': 10, 'quantity': 2}]}]
        response = service.quote_batch('batch', orders)
        orders[0]['items'][0]['unit_cents'] = 99
        response['quotes'][0]['total_cents'] = -1
        response['batch_id'] = 'corrupt'
        original = [{'order_id': 'a', 'items': [{'unit_cents': 10, 'quantity': 2}]}]
        expected = {'batch_id': 'batch', 'quotes': [{'order_id': 'a',
                    'subtotal_cents': 20, 'discount_cents': 0,
                    'shipping_cents': 499, 'total_cents': 519}]}
        retry = service.quote_batch('batch', original)
        self.assertEqual(retry, expected)
        retry['quotes'].clear()
        self.assertEqual(service.quote_batch('batch', original), expected)
        with self.assertRaises(ValueError):
            service.quote_batch('batch', orders)

    def test_invalid_retry_does_not_replace_valid_batch(self):
        service = QuoteService()
        original = [{'order_id': 'a', 'items': [{'unit_cents': 1, 'quantity': 1}]}]
        expected = service.quote_batch('batch', original)
        with self.assertRaises(ValueError):
            service.quote_batch('batch', [{'order_id': 'a', 'items': [
                {'unit_cents': True, 'quantity': 1}]}])
        self.assertEqual(service.quote_batch('batch', original), expected)

    def test_nested_item_list_order_is_part_of_retry_identity(self):
        service = QuoteService()
        items = [{'unit_cents': 1, 'quantity': 1}, {'unit_cents': 2, 'quantity': 1}]
        service.quote_batch('batch', [{'order_id': 'a', 'items': items}])
        with self.assertRaises(ValueError):
            service.quote_batch('batch', [{'order_id': 'a', 'items': list(reversed(items))}])
