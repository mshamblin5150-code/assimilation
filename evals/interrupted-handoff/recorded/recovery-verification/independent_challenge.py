"""Read/run only independent public-seam review of the retained synthetic trial."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest

PROJECT = Path(sys.argv.pop(1)).resolve()
sys.path.insert(0, str(PROJECT))
from parcelquote.api import QuoteService
from parcelquote.pricing import quote, legacy_total

class IndependentChallenge(unittest.TestCase):
    def test_pricing_literal_rounding_and_shipping(self):
        self.assertEqual(quote([{'unit_cents':19,'quantity':2}], 'SAVE10'), {'subtotal_cents':38,'discount_cents':3,'shipping_cents':499,'total_cents':534})
        self.assertEqual(quote([{'unit_cents':5555,'quantity':1}], 'SAVE10'), {'subtotal_cents':5555,'discount_cents':555,'shipping_cents':0,'total_cents':5000})
        self.assertEqual(quote([{'unit_cents':0,'quantity':1}])['shipping_cents'],499)
    def test_legacy_generator(self):
        self.assertEqual(legacy_total(x for x in [-5, 1.5, 2]),-1.5)
    def test_equal_boolean_float_retry_rejected_without_corrupting_cache(self):
        for field, value in [('quantity',True),('unit_cents',True),('quantity',1.0),('unit_cents',1.0)]:
            with self.subTest(field=field,value=repr(value)):
                service=QuoteService(); original=[{'order_id':'a','items':[{'unit_cents':1,'quantity':1}]}]
                expected=service.quote_batch('b',original)
                invalid=copy.deepcopy(original);invalid[0]['items'][0][field]=value
                self.assertEqual(invalid,original) # Python equality trap is real.
                with self.assertRaises(ValueError):service.quote_batch('b',invalid)
                self.assertEqual(service.quote_batch('b',original),expected)
    def test_retry_raw_shape_distinct(self):
        service=QuoteService(); service.quote_batch('b',[{'order_id':'a','items':[]}])
        with self.assertRaises(ValueError):service.quote_batch('b',[{'order_id':'a','items':[],'coupon':None}])
    def test_atomicity_and_mutation(self):
        service=QuoteService();original=[{'order_id':'a','items':[{'unit_cents':20,'quantity':1}]}]
        with self.assertRaises(ValueError):service.quote_batch('b',original+[{'order_id':'a','items':[]}])
        request=copy.deepcopy(original);result=service.quote_batch('b',request)
        request[0]['items'][0]['unit_cents']=50;result['quotes'].clear()
        self.assertEqual(service.quote_batch('b',original),{'batch_id':'b','quotes':[{'order_id':'a','subtotal_cents':20,'discount_cents':0,'shipping_cents':499,'total_cents':519}]})
    def cli(self,raw):
        return subprocess.run([sys.executable,'-B','-m','parcelquote'],cwd=PROJECT,input=raw,text=True,capture_output=True,timeout=5)
    def test_cli_normal_and_boolean_invalid(self):
        good=self.cli('{"batch_id":"b","orders":[]}')
        self.assertEqual((good.returncode,good.stderr),(0,''));self.assertEqual(json.loads(good.stdout),{'batch_id':'b','quotes':[]})
        bad=self.cli('{"batch_id":"b","orders":[{"order_id":"a","items":[{"unit_cents":1,"quantity":true}]}]}')
        self.assertEqual((bad.returncode,bad.stderr),(2,''));self.assertEqual(json.loads(bad.stdout),{'error':'invalid_request'})
    def test_cli_valid_large_integer_result(self):
        raw='{"batch_id":"b","orders":[{"order_id":"a","items":[{"unit_cents":'+('8'*4300)+',"quantity":10}]}]}'
        result=self.cli(raw)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(result.stderr,'')
        parsed=json.loads(result.stdout,parse_int=str)
        self.assertEqual(parsed['quotes'][0]['total_cents'],'8'*4300+'0')
    def test_cli_invalid_deep_json(self):
        result=self.cli('['*1200+'0'+']'*1200)
        self.assertEqual((result.returncode,result.stderr),(2,''));self.assertEqual(json.loads(result.stdout),{'error':'invalid_request'})

if __name__=='__main__':unittest.main(verbosity=2)
