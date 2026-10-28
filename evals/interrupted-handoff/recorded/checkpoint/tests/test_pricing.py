import unittest
from parcelquote.pricing import quote


class PricingTests(unittest.TestCase):
    def test_nonempty_order_has_subtotal_and_delivery(self):
        self.assertEqual(quote([{'unit_cents': 125, 'quantity': 2}]), {
            'subtotal_cents': 250, 'discount_cents': 0,
            'shipping_cents': 499, 'total_cents': 749})

    def test_discount_rounds_whole_subtotal_down(self):
        self.assertEqual(quote([{'unit_cents': 19, 'quantity': 1},
                                {'unit_cents': 19, 'quantity': 1}], 'SAVE10'), {
            'subtotal_cents': 38, 'discount_cents': 3,
            'shipping_cents': 499, 'total_cents': 534})

    def test_delivery_threshold_is_discounted_and_inclusive(self):
        for price, coupon, discount, shipping, total in [
            (4999, None, 0, 499, 5498), (5000, None, 0, 0, 5000),
            (5000, 'SAVE10', 500, 499, 4999),
            (5555, 'SAVE10', 555, 0, 5000),
            (5554, 'SAVE10', 555, 499, 5498)]:
            with self.subTest(price=price, coupon=coupon):
                self.assertEqual(quote([{'unit_cents': price, 'quantity': 1}], coupon), {
                    'subtotal_cents': price, 'discount_cents': discount,
                    'shipping_cents': shipping, 'total_cents': total})

    def test_empty_order_is_free_but_zero_price_order_has_delivery(self):
        for coupon in (None, 'SAVE10'):
            self.assertEqual(quote([], coupon), {
                'subtotal_cents': 0, 'discount_cents': 0,
                'shipping_cents': 0, 'total_cents': 0})
        self.assertEqual(quote([{'unit_cents': 0, 'quantity': 1}]), {
            'subtotal_cents': 0, 'discount_cents': 0,
            'shipping_cents': 499, 'total_cents': 499})

    def test_invalid_coupons_raise_value_error_even_for_empty_orders(self):
        for coupon in ('save10', ' SAVE10', '', 10, True, [], {}, ['SAVE10']):
            with self.subTest(coupon=coupon), self.assertRaises(ValueError):
                quote([], coupon)

    def test_invalid_items_raise_value_error(self):
        invalid = [None, (), {}, '', True, 5, [None], [[]], [{}],
                   [{'unit_cents': 1}], [{'unit_cents': 1, 'quantity': 1, 'extra': 2}]]
        for field, values in [('unit_cents', [-1, True, False, 1.5, '1', None, []]),
                              ('quantity', [0, -1, True, False, 1.5, '1', None, []])]:
            for value in values:
                item = {'unit_cents': 1, 'quantity': 1}
                item[field] = value
                invalid.append([item])
        for items in invalid:
            with self.subTest(items=items), self.assertRaises(ValueError):
                quote(items)
