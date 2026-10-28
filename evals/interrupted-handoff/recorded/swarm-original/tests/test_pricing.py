import unittest
from parcelquote.pricing import quote, legacy_total


class PricingTests(unittest.TestCase):
    def test_line_quantities_and_standard_delivery(self):
        self.assertEqual(quote([{'unit_cents': 125, 'quantity': 3}, {'unit_cents': 25, 'quantity': 1}]), {
            'subtotal_cents': 400, 'discount_cents': 0, 'shipping_cents': 499, 'total_cents': 899})

    def test_discount_floors_whole_subtotal(self):
        self.assertEqual(quote([{'unit_cents': 19, 'quantity': 1}, {'unit_cents': 19, 'quantity': 1}], 'SAVE10'), {
            'subtotal_cents': 38, 'discount_cents': 3, 'shipping_cents': 499, 'total_cents': 534})

    def test_delivery_threshold_uses_discounted_total(self):
        cases = [(4999, None, 499, 5498), (5000, None, 0, 5000),
                 (5000, 'SAVE10', 499, 4999), (5555, 'SAVE10', 0, 5000),
                 (5554, 'SAVE10', 499, 5498)]
        for cents, coupon, shipping, total in cases:
            with self.subTest(cents=cents, coupon=coupon):
                result = quote([{'unit_cents': cents, 'quantity': 1}], coupon)
                self.assertEqual((result['shipping_cents'], result['total_cents']), (shipping, total))

    def test_empty_order_is_free_but_nonempty_zero_order_pays_delivery(self):
        self.assertEqual(quote([]), {'subtotal_cents': 0, 'discount_cents': 0, 'shipping_cents': 0, 'total_cents': 0})
        self.assertEqual(quote([{'unit_cents': 0, 'quantity': 1}], 'SAVE10'), {
            'subtotal_cents': 0, 'discount_cents': 0, 'shipping_cents': 499, 'total_cents': 499})

    def test_invalid_item_shapes_raise_value_error(self):
        for items in (None, {}, (), 'items', [None], [[]], [{}], [{'unit_cents': 1}],
                      [{'unit_cents': 1, 'quantity': 1, 'extra': 0}]):
            with self.subTest(items=items), self.assertRaises(ValueError):
                quote(items)

    def test_item_numbers_are_domain_integers(self):
        for field, values in [('unit_cents', [-1, True, False, 1.0, '1', None]),
                              ('quantity', [-1, 0, True, False, 1.0, '1', None])]:
            for value in values:
                item = {'unit_cents': 1, 'quantity': 1, field: value}
                with self.subTest(item=item), self.assertRaises(ValueError):
                    quote([item])

    def test_only_exact_coupon_is_accepted_even_for_empty_items(self):
        for coupon in ('save10', ' SAVE10', '', True, 10, [], {}, b'SAVE10'):
            with self.subTest(coupon=coupon), self.assertRaises(ValueError):
                quote([], coupon)

    def test_legacy_still_sums_empty_negative_fractional_and_generator_inputs(self):
        for prices, expected in [([], 0), ([-5, 2], -3), ([0.5, 1.25], 1.75),
                                 ((x for x in [2, 3]), 5)]:
            with self.subTest(expected=expected):
                self.assertEqual(legacy_total(prices), expected)

    def test_large_integer_quote_has_exact_integer_results(self):
        self.assertEqual(quote([{'unit_cents': 100000000000000009, 'quantity': 1}], 'SAVE10'), {
            'subtotal_cents': 100000000000000009, 'discount_cents': 10000000000000000,
            'shipping_cents': 0, 'total_cents': 90000000000000009})
        self.assertTrue(all(type(value) is int for value in quote([]).values()))
