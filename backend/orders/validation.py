from __future__ import annotations

from decimal import Decimal
from typing import Tuple, Optional
from django.utils import timezone

from orders.pricing import price_cart, _to_decimal


def _safe_get(obj, name, default=None):
    return getattr(obj, name, default)


def _coerce_dt_aware(dt) -> Optional[timezone.datetime]:
    """
    Ensure a datetime is timezone-aware (to compare with timezone.now()).
    If it's naive, assume settings.TIME_ZONE.
    """
    if not dt:
        return dt
    if timezone.is_naive(dt):
        return timezone.make_aware(dt, timezone.get_current_timezone())
    return dt


def _fmt_money(v: Decimal) -> str:
    # Keep copy short & INR-like without localization overhead
    return f"{_to_decimal(v):.2f}"


def validate_coupon_for_cart(cart, subtotal: Decimal | None = None) -> Tuple[bool, str]:
    """
    Validate the coupon currently attached to `cart` against common constraints.
    Returns (ok, message).
    If `subtotal` isn't provided, it will be derived using price_cart(cart).
    """
    coupon = getattr(cart, "applied_coupon", None)
    if not coupon:
        return True, ""

    # Compute subtotal if not supplied
    if subtotal is None:
        totals = price_cart(cart)
        subtotal = totals["subtotal"]
    else:
        subtotal = _to_decimal(subtotal)

    # Active flag (support either `is_active` or `active`)
    is_active = True
    if hasattr(coupon, "is_active"):
        is_active = bool(coupon.is_active)
    elif hasattr(coupon, "active"):
        is_active = bool(coupon.active)
    if not is_active:
        return False, "Coupon is not active."

    # Date window checks (normalize naive datetimes)
    now = timezone.now()
    starts_at = _coerce_dt_aware(_safe_get(coupon, "starts_at"))
    ends_at = _coerce_dt_aware(_safe_get(coupon, "ends_at"))
    if starts_at and now < starts_at:
        return False, "Coupon is not active yet."
    if ends_at and now > ends_at:
        return False, "Coupon has expired."

    # Min / max order value
    mov = _safe_get(coupon, "min_order_value")
    if mov is not None and mov != "":
        mov_dec = _to_decimal(mov)
        if subtotal < mov_dec:
            return False, f"Order subtotal must be at least ₹{_fmt_money(mov_dec)} for this coupon."

    max_ord_val = _safe_get(coupon, "max_order_value")
    if max_ord_val is not None and max_ord_val != "":
        max_dec = _to_decimal(max_ord_val)
        if subtotal > max_dec:
            return False, "Order subtotal is too high for this coupon."

    # Model-specific hook
    if hasattr(coupon, "can_apply"):
        try:
            ok, msg = coupon.can_apply(subtotal)
        except Exception:
            # Defensive: if custom hook blows up, fail gracefully
            return False, "Coupon validation failed."
        if not ok:
            return False, (msg or "Coupon not applicable for this order.")

    # Global usage limit
    max_uses = _safe_get(coupon, "max_uses")
    times_used = _safe_get(coupon, "times_used", 0)
    if max_uses is not None and str(max_uses) != "" and int(times_used or 0) >= int(max_uses):
        return False, "Coupon usage limit reached."

    return True, ""
