"""Integer-cent quotations and the unchanged legacy summation seam."""
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
        unit, quantity = item['unit_cents'], item['quantity']
        if (not isinstance(unit, int) or isinstance(unit, bool) or unit < 0
                or not isinstance(quantity, int) or isinstance(quantity, bool)
                or quantity <= 0):
            raise ValueError('invalid item values')
    subtotal = sum(item['unit_cents'] * item['quantity'] for item in items)
    discount = subtotal // 10 if coupon == 'SAVE10' else 0
    shipping = 0 if not items or subtotal - discount >= 5000 else 499
    return {'subtotal_cents': subtotal, 'discount_cents': discount,
            'shipping_cents': shipping, 'total_cents': subtotal - discount + shipping}
