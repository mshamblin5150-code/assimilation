"""Existing legacy pricing seam; new quote engine is not implemented yet."""
def legacy_total(prices):
    return sum(prices)


def quote(items, coupon=None):
    raise NotImplementedError("new pricing engine pending")
