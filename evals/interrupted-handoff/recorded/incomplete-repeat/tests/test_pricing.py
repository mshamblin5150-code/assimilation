import unittest
from parcelquote.pricing import quote


class PricingTests(unittest.TestCase):
    def test_prices_quantities_and_shipping(self):
        self.assertEqual(quote([{'unit_cents': 125, 'quantity': 2},
                                {'unit_cents': 75, 'quantity': 3}]),
                         {'subtotal_cents': 475, 'discount_cents': 0,
                          'shipping_cents': 499, 'total_cents': 974})

    def test_discount_floors_whole_subtotal(self):
        self.assertEqual(quote([{'unit_cents': 19, 'quantity': 1},
                                {'unit_cents': 19, 'quantity': 1}], 'SAVE10'),
                         {'subtotal_cents': 38, 'discount_cents': 3,
                          'shipping_cents': 499, 'total_cents': 534})

    def test_shipping_uses_discounted_threshold_and_empty_order(self):
        cases = [([], None, (0, 0, 0, 0)),
                 ([], 'SAVE10', (0, 0, 0, 0)),
                 ([{'unit_cents': 0, 'quantity': 1}], None, (0, 0, 499, 499)),
                 ([{'unit_cents': 4999, 'quantity': 1}], None, (4999, 0, 499, 5498)),
                 ([{'unit_cents': 5000, 'quantity': 1}], None, (5000, 0, 0, 5000)),
                 ([{'unit_cents': 5000, 'quantity': 1}], 'SAVE10', (5000, 500, 499, 4999)),
                 ([{'unit_cents': 5554, 'quantity': 1}], 'SAVE10', (5554, 555, 499, 5498)),
                 ([{'unit_cents': 5555, 'quantity': 1}], 'SAVE10', (5555, 555, 0, 5000))]
        for items, coupon, expected in cases:
            with self.subTest(items=items, coupon=coupon):
                self.assertEqual(quote(items, coupon), dict(zip(
                    ('subtotal_cents', 'discount_cents', 'shipping_cents', 'total_cents'), expected)))

    def test_rejects_invalid_item_shapes_and_numbers(self):
        invalid = [None, {}, (), 'items', iter([]), [None], [[]], [{}],
                   [{'unit_cents': 1}], [{'quantity': 1}],
                   [{'unit_cents': 1, 'quantity': 1, 'extra': 0}]]
        for field, values in [('unit_cents', [-1, True, False, 1.0, '1', None]),
                              ('quantity', [-1, 0, True, False, 1.0, '1', None])]:
            for value in values:
                item = {'unit_cents': 1, 'quantity': 1}
                item[field] = value
                invalid.append([item])
        for items in invalid:
            with self.subTest(items=items), self.assertRaises(ValueError):
                quote(items)

    def test_rejects_unknown_coupons_even_for_empty_orders(self):
        for coupon in ['', 'save10', ' SAVE10', 'SAVE10 ', False, 0, [], {}, 10]:
            with self.subTest(coupon=coupon), self.assertRaises(ValueError):
                quote([], coupon)

    def test_large_integer_amount_remains_exact(self):
        result = quote([{'unit_cents': 100000000000000000019, 'quantity': 1}], 'SAVE10')
        self.assertEqual(result, {'subtotal_cents': 100000000000000000019,
                                  'discount_cents': 10000000000000000001,
                                  'shipping_cents': 0,
                                  'total_cents': 90000000000000000018})
        self.assertTrue(all(type(value) is int for value in result.values()))
