"""Legacy summation and validated synthetic order pricing."""
def legacy_total(prices):
    return sum(prices)


def quote(items, coupon=None):
    if coupon is not None and (not isinstance(coupon, str) or coupon != 'SAVE10'):
        raise ValueError('invalid coupon')
    if not isinstance(items, list):
        raise ValueError('items must be a list')
    for item in items:
        if not isinstance(item, dict) or set(item) != {'unit_cents', 'quantity'}:
            raise ValueError('invalid item shape')
        if type(item['unit_cents']) is not int or item['unit_cents'] < 0:
            raise ValueError('invalid unit cents')
        if type(item['quantity']) is not int or item['quantity'] <= 0:
            raise ValueError('invalid quantity')
    subtotal = sum(item['unit_cents'] * item['quantity'] for item in items)
    discount = subtotal // 10 if coupon == 'SAVE10' else 0
    shipping = 0 if not items or subtotal - discount >= 5000 else 499
    return {'subtotal_cents': subtotal, 'discount_cents': discount,
            'shipping_cents': shipping, 'total_cents': subtotal - discount + shipping}
