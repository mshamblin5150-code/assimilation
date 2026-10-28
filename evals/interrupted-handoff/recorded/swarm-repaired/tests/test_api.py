import unittest
from parcelquote.api import QuoteService


class BatchTests(unittest.TestCase):
    def test_empty_batch(self):
        self.assertEqual(QuoteService().quote_batch('empty', []), {'batch_id': 'empty', 'quotes': []})

    def test_invalid_batch_shapes_raise_value_error(self):
        for batch_id, orders in [(None, []), ('', []), (1, []), ('b', None), ('b', {}), ('b', ())]:
            with self.subTest(batch_id=batch_id, orders=orders):
                with self.assertRaises(ValueError):
                    QuoteService().quote_batch(batch_id, orders)

    def test_order_shapes_and_unique_ids(self):
        invalid = [None, {}, {'order_id': '', 'items': []}, {'order_id': 1, 'items': []},
                   {'order_id': 'a', 'items': [], 'extra': 2}]
        for order in invalid:
            with self.subTest(order=order), self.assertRaises(ValueError):
                QuoteService().quote_batch('b', [order])
        with self.assertRaises(ValueError):
            QuoteService().quote_batch('b', [{'order_id': 'a', 'items': []}] * 2)

    def test_quotes_preserve_order_and_prices(self):
        orders = [{'order_id': 'second', 'items': []}, {'order_id': 'first', 'items': [{'unit_cents': 5555, 'quantity': 1}], 'coupon': 'SAVE10'}]
        self.assertEqual(QuoteService().quote_batch('b', orders), {'batch_id': 'b', 'quotes': [
            {'order_id': 'second', 'subtotal_cents': 0, 'discount_cents': 0, 'shipping_cents': 0, 'total_cents': 0},
            {'order_id': 'first', 'subtotal_cents': 5555, 'discount_cents': 555, 'shipping_cents': 0, 'total_cents': 5000}]})

    def test_retry_equal_input_and_reject_changed_input(self):
        service = QuoteService()
        orders = [{'order_id': 'a', 'items': []}, {'order_id': 'b', 'items': []}]
        original = service.quote_batch('b', orders)
        self.assertEqual(service.quote_batch('b', [{'items': [], 'order_id': 'a'}, {'items': [], 'order_id': 'b'}]), original)
        with self.assertRaises(ValueError):
            service.quote_batch('b', list(reversed(orders)))

    def test_request_and_response_mutation_do_not_corrupt_retry(self):
        service = QuoteService()
        orders = [{'order_id': 'a', 'items': [{'unit_cents': 100, 'quantity': 1}]}]
        result = service.quote_batch('b', orders)
        orders[0]['items'][0]['unit_cents'] = 200
        result['quotes'][0]['total_cents'] = -1
        expected = {'batch_id': 'b', 'quotes': [{'order_id': 'a', 'subtotal_cents': 100, 'discount_cents': 0, 'shipping_cents': 499, 'total_cents': 599}]}
        retry = service.quote_batch('b', [{'order_id': 'a', 'items': [{'unit_cents': 100, 'quantity': 1}]}])
        self.assertEqual(retry, expected)
        retry['quotes'].clear()
        self.assertEqual(service.quote_batch('b', [{'order_id': 'a', 'items': [{'unit_cents': 100, 'quantity': 1}]}]), expected)

    def test_failed_batch_does_not_reserve_id(self):
        service = QuoteService()
        with self.assertRaises(ValueError):
            service.quote_batch('b', [{'order_id': 'good', 'items': []}, {'order_id': 'bad', 'items': [{'unit_cents': -1, 'quantity': 1}]}])
        self.assertEqual(service.quote_batch('b', []), {'batch_id': 'b', 'quotes': []})

    def test_cache_is_instance_local_and_invalid_equal_numbers_are_rejected(self):
        service = QuoteService()
        service.quote_batch('b', [{'order_id': 'a', 'items': [{'unit_cents': 1, 'quantity': 1}]}])
        for value in [True, 1.0]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                service.quote_batch('b', [{'order_id': 'a', 'items': [{'unit_cents': value, 'quantity': 1}]}])
        self.assertEqual(QuoteService().quote_batch('b', []), {'batch_id': 'b', 'quotes': []})
