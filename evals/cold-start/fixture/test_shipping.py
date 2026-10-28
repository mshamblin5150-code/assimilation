import unittest
from shipping import shipping_cost

class ShippingTests(unittest.TestCase):
    def test_below_threshold(self):
        self.assertEqual(shipping_cost(40), 5)
    def test_above_threshold(self):
        self.assertEqual(shipping_cost(60), 0)
