from decimal import Decimal, ROUND_HALF_UP
from django.conf import settings

ZERO = Decimal("0.00")

# e.g., 18 → 18%
GST_RATE = Decimal(str(getattr(settings, "GST_RATE_PERCENT", 0)))

# Configurable fallbacks (keep your previous defaults)
SHIPPING_FALLBACK_RATE = Decimal(str(getattr(settings, "SHIPPING_FALLBACK_RATE", "49.00")))
FREE_SHIPPING_THRESHOLD = Decimal(str(getattr(settings, "FREE_SHIPPING_THRESHOLD", "999.00")))


def _to_decimal(v):
    if v is None:
        return ZERO
    if isinstance(v, Decimal):
        return v
    return Decimal(str(v))


def _round2(x: Decimal) -> Decimal:
    return x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def price_cart(cart, shipping_method=None) -> dict:
    """
    Compute totals for a cart.

    Returns:
      dict(subtotal, discount_total, tax_total, shipping_total, grand_total)
    """
    items = cart.items.select_related("variant", "variant__product")

    # Subtotal
    subtotal = ZERO
    for it in items:
        price = _to_decimal(it.price_at_add or getattr(it.variant, "price_sale", None) or it.variant.price_mrp)
        subtotal += (price * int(it.qty or 0))

    # Discount (cap to [0, subtotal])
    discount_total = ZERO
    c = getattr(cart, "applied_coupon", None)
    if c:
        if getattr(c, "discount_type", None) == "percentage":
            pct = _to_decimal(getattr(c, "value", ZERO))
            # guard weird negatives
            pct = max(pct, ZERO)
            discount_total = _round2(subtotal * pct / Decimal("100"))
        else:
            discount_total = _to_decimal(getattr(c, "value", ZERO))
        if discount_total < ZERO:
            discount_total = ZERO
        if discount_total > subtotal:
            discount_total = subtotal

    taxable = max(subtotal - discount_total, ZERO)

    # GST (flat percent for phase-1)
    tax_total = _round2(taxable * GST_RATE / Decimal("100")) if GST_RATE else ZERO

    # Shipping
    if taxable == ZERO:
        shipping_total = ZERO  # nothing to ship
    elif shipping_method:
        rate = _to_decimal(getattr(shipping_method, "base_rate", ZERO))
        free_over = _to_decimal(getattr(shipping_method, "free_over", ZERO)) or ZERO
        if free_over and taxable >= free_over:
            rate = ZERO
        shipping_total = _round2(rate)
    else:
        # Fallback rule (cart page): free over threshold else flat
        shipping_total = ZERO if taxable >= FREE_SHIPPING_THRESHOLD else _round2(SHIPPING_FALLBACK_RATE)

    grand_total = max(taxable + tax_total + shipping_total, ZERO)

    return {
        "subtotal": _round2(subtotal),
        "discount_total": _round2(discount_total),
        "tax_total": _round2(tax_total),
        "shipping_total": _round2(shipping_total),
        "grand_total": _round2(grand_total),
    }
