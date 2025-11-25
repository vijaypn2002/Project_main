# core/notifications.py
from __future__ import annotations

from typing import Iterable, Optional
from django.core.mail import EmailMultiAlternatives, send_mail
from django.conf import settings


# ------------------------------------------------------------
# Low-level helpers
# ------------------------------------------------------------
def _send_email(
    subject: str,
    body_text: str,
    to: str | Iterable[str],
    *,
    body_html: Optional[str] = None,
    reply_to: Optional[Iterable[str]] = None,
    fail_silently: bool = True,
) -> None:
    """
    Centralized email sender.
    - Uses DEFAULT_FROM_EMAIL from settings
    - Supports optional HTML alternative
    - Swallows errors by default (fail_silently=True)
    """
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@ecommerce.local")

    # If no HTML given and EMAIL_BACKEND is console, simple send_mail is fine
    if not body_html:
        send_mail(
            subject=subject,
            message=body_text,
            from_email=from_email,
            recipient_list=[to] if isinstance(to, str) else list(to),
            fail_silently=fail_silently,
            reply_to=list(reply_to) if reply_to else None,
        )
        return

    # Multipart with HTML
    msg = EmailMultiAlternatives(
        subject=subject,
        body=body_text,
        from_email=from_email,
        to=[to] if isinstance(to, str) else list(to),
        reply_to=list(reply_to) if reply_to else None,
    )
    msg.attach_alternative(body_html, "text/html")
    try:
        msg.send(fail_silently=fail_silently)
    except Exception:
        if not fail_silently:
            raise


# ------------------------------------------------------------
# Message builders (keep text simple; add HTML when needed)
# ------------------------------------------------------------
def _greeting(name: Optional[str]) -> str:
    name = (name or "").strip()
    return f"Hi {name}," if name else "Hi,"


def _signature() -> str:
    brand = getattr(settings, "BRAND_NAME", "Our Store")
    return f"\n\n— {brand} Team"


# ------------------------------------------------------------
# Public notification functions
# ------------------------------------------------------------
def send_order_confirmed(order) -> None:
    """
    Payment succeeded / order moved to 'paid'.
    """
    subject = f"Order #{order.id} confirmed"
    body = (
        f"{_greeting(getattr(order, 'customer_name', None))}\n\n"
        f"Thanks! Your payment for Order #{order.id} has been received.\n"
        f"We'll begin processing your order shortly.\n"
        f"Order total: ₹{order.total}\n"
        f"Order status: {order.status.capitalize()}"
        f"{_signature()}"
    )
    _send_email(subject, body, order.email)


def send_shipped(order, shipment) -> None:
    """
    Shipment moved to 'in_transit'.
    """
    subject = f"Order #{order.id} shipped"
    tracking = shipment.tracking_no or "TBD"
    carrier = shipment.carrier or "Carrier"
    body = (
        f"{_greeting(getattr(order, 'customer_name', None))}\n\n"
        f"Good news! Your order is on the way.\n"
        f"Carrier: {carrier}\n"
        f"Tracking: {tracking}\n"
        f"Current status: In transit"
        f"{_signature()}"
    )
    _send_email(subject, body, order.email)


def send_delivered(order, shipment) -> None:
    """
    Shipment moved to 'delivered'.
    """
    subject = f"Order #{order.id} delivered"
    body = (
        f"{_greeting(getattr(order, 'customer_name', None))}\n\n"
        f"We're happy to let you know your order has been delivered.\n"
        f"Hope you enjoy your purchase!"
        f"{_signature()}"
    )
    _send_email(subject, body, order.email)


def send_refund_processed(order, payment, *, amount_rupees: str | float | int) -> None:
    """
    Refund (full or partial) processed.
    """
    subject = f"Refund processed for Order #{order.id}"
    body = (
        f"{_greeting(getattr(order, 'customer_name', None))}\n\n"
        f"A refund of ₹{amount_rupees} has been processed for Order #{order.id}.\n"
        f"Payment ref: {getattr(payment, 'provider_payment_id', '-')}\n"
        f"If you have any questions, just reply to this email."
        f"{_signature()}"
    )
    _send_email(subject, body, order.email)


def send_return_requested(order, order_item, return_request) -> None:
    """
    Customer submitted an RMA request.
    """
    subject = f"Return requested for Order #{order.id}"
    body = (
        f"{_greeting(getattr(order, 'customer_name', None))}\n\n"
        f"We've received your return request for item {order_item.sku} (qty {return_request.qty}).\n"
        f"Our team will review it and update you shortly."
        f"{_signature()}"
    )
    _send_email(subject, body, order.email)
