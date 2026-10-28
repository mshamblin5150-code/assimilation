import unittest
from parcelquote.pricing import legacy_total

class LegacyTests(unittest.TestCase):
    def test_legacy_sum(self):
        self.assertEqual(legacy_total([125, 75]), 200)

    def test_existing_empty_negative_fractional_and_generator_inputs(self):
        self.assertEqual(legacy_total([]), 0)
        self.assertEqual(legacy_total([-5, 2]), -3)
        self.assertEqual(legacy_total([1.25, 2.5]), 3.75)
        self.assertEqual(legacy_total(value for value in [2, -5, 1.5]), -1.5)

if __name__ == '__main__':
    unittest.main()
