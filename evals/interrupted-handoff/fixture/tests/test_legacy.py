import unittest
from parcelquote.pricing import legacy_total

class LegacyTests(unittest.TestCase):
    def test_legacy_sum(self):
        self.assertEqual(legacy_total([125, 75]), 200)

if __name__ == '__main__':
    unittest.main()
