import importlib.util,tempfile,shutil,json,sys
from pathlib import Path
root=Path('/workspace/scratch/b6810fbd29e0/assimilation-handoff-work')
spec=importlib.util.spec_from_file_location('cal',root/'tests/test_interrupted_handoff.py'); c=importlib.util.module_from_spec(spec); spec.loader.exec_module(c)
with tempfile.TemporaryDirectory() as d:
 p=Path(d)/'project'; shutil.copytree(c.EVAL/'fixture',p)
 (p/'parcelquote/pricing.py').write_text(c.PRICING)
 (p/'parcelquote/__main__.py').write_text(c.CLI)
 api=c.API.replace('        seen, quotes = set(), []', '''        if all(isinstance(o, dict) and isinstance(o.get('order_id'), str) for o in orders):
            ids = [o['order_id'] for o in orders]
            if len(ids) != len(set(ids)):
                raise ValueError()
        new_batch = batch_id not in self.cache
        seen, quotes = set(), []''').replace("            quotes.append(dict(order_id=oid, **quote(order['items'], order.get('coupon'))))", """            quotes.append(dict(order_id=oid, **quote(order['items'], order.get('coupon'))))
            if new_batch:
                self.cache[batch_id] = deepcopy((orders, dict(batch_id=batch_id, quotes=quotes)))""")
 (p/'parcelquote/api.py').write_text(api)
 r=c.grader.grade(p,retry_policy='distinct'); print('mutant grader passed:', r['passed'])
 sys.path.insert(0,str(p)); from parcelquote.api import QuoteService
 s=QuoteService()
 try: s.quote_batch('atomic',[{'order_id':'valid','items':[]},{'order_id':'invalid','items':[{'unit_cents':-1,'quantity':1}]}])
 except ValueError: print('invalid late order rejected')
 try: print('valid replacement:',s.quote_batch('atomic',[]))
 except ValueError: print('BUG: failed batch reserved ID; valid replacement rejected')
