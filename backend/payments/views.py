# payments/views.py
from __future__ import annotations

import json
import hmac
import hashlib
import time
from decimal import Decimal
from typing import Optional

try:
    import razorpay  # optional at dev time
except Exception:  # pragma: no cover
    razorpay = None  # allow running without the package in mock mode

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAdminUser
from drf_spectacular.utils import extend_schema

from .models import Payment, PaymentEvent, PaymentProvider
from .serializers import CreateIntentSerializer, RefundSerializer
from orders.models import Order


# ----------------- helpers -----------------

def _rupees_to_paise(amount_rupees: Decimal | float | str | int) -> int:
    return int(Decimal(str(amount_rupees)) * 100)


def _use_mock_mode() -> bool:
    """Decide if we should run without contacting Razorpay."""
    if getattr(settings, "PAYMENTS_MOCK", False):
        return True
    # If keys are missing/blank, fall back to mock
    key_id = getattr(settings, "RAZORPAY_KEY_ID", "") or ""
    key_secret = getattr(settings, "RAZORPAY_KEY_SECRET", "") or ""
    return not (key_id and key_secret)


def _currency() -> str:
    return getattr(settings, "PAYMENT_CURRENCY", "INR") or "INR"


def _find_order_for_request(request, order_id: int) -> Optional[Order]:
    """
    Authorize access to the order:
    - If authenticated: allow when order.email == request.user.email.
      (Code also tolerates a future order.user FK via getattr checks.)
    - Else (guest): require ?email=<email> matching order.email.
    Returns the order or None.
    """
    email_param = (request.query_params.get("email") or request.GET.get("email") or "").strip()
    try:
        order = Order.objects.get(pk=order_id)
    except Order.DoesNotExist:
        return None

    user = getattr(request, "user", None)
    if user and getattr(user, "is_authenticated", False):
        if getattr(order, "user_id", None) == getattr(user, "id", None):
            return order
        if getattr(order, "email", "") and getattr(user, "email", "") and order.email.lower() == user.email.lower():
            return order
        if email_param and getattr(order, "email", "").lower() == email_param.lower():
            return order
        return None

    # guest path
    if email_param and getattr(order, "email", "").lower() == email_param.lower():
        return order
    return None


# ----------------- views -----------------

class CreateIntentView(GenericAPIView):
    """
    Create a provider order/intent.
    - Works for authenticated users OR guests (provide ?email=<order_email>)
    - When Razorpay keys are not configured, runs in MOCK mode and fabricates an order id.
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = CreateIntentSerializer  # for schema

    @extend_schema(
        request=CreateIntentSerializer,
        responses={
            200: None,
            400: None,
            403: None,
            404: None,
            409: None,
        },
    )
    def post(self, request):
        ser = CreateIntentSerializer(data=request.data, context={"request": request})
        ser.is_valid(raise_exception=True)

        order_id = ser.validated_data["order_id"]
        provider = ser.validated_data.get("provider", PaymentProvider.RAZORPAY)
        capture = ser.validated_data.get("capture", True)

        order = _find_order_for_request(request, order_id)
        if not order:
            return Response({"detail": "order not found or not permitted"}, status=404)

        if order.status != Order.Status.CREATED:
            return Response({"detail": f"order status is {order.status}"}, status=400)

        if order.total is None:
            return Response({"detail": "order.total missing"}, status=400)

        amount_paise = _rupees_to_paise(order.total)
        currency = _currency()

        # ----- MOCK MODE -----
        if _use_mock_mode():
            mock_provider_order_id = f"order_MOCK_{order.id}_{int(time.time())}"
            rp_order = {
                "id": mock_provider_order_id,
                "amount": amount_paise,
                "currency": currency,
                "status": "created",
                "notes": {"mock": True, "order_id": order.id},
            }
            with transaction.atomic():
                payment, created = Payment.objects.get_or_create(
                    provider_order_id=mock_provider_order_id,
                    defaults={
                        "order": order,
                        "provider": provider,
                        "status": Payment.Status.CREATED,
                        "amount_paise": amount_paise,
                        "currency": currency,
                        "raw_payload": rp_order,
                    },
                )
                if not created:
                    if payment.order_id != order.id:
                        return Response({"detail": "payment already bound to another order"}, status=409)
                    if payment.amount_paise != amount_paise:
                        payment.amount_paise = amount_paise
                        payment.raw_payload = rp_order
                        payment.save(update_fields=["amount_paise", "raw_payload"])

                PaymentEvent.objects.get_or_create(
                    provider=provider,
                    event_id=rp_order["id"],
                    defaults={
                        "payment": payment,
                        "event_type": "intent.create.mock",
                        "payload": rp_order,
                    },
                )

            return Response(
                {
                    "provider": provider,
                    "key": "rzp_test_mock",
                    "currency": currency,
                    "amount": amount_paise,
                    "razorpay_order_id": rp_order["id"],
                    "meta": {"mock": True, "capture": bool(capture)},
                },
                status=200,
            )

        # ----- REAL RAZORPAY -----
        if not razorpay:
            return Response({"detail": "Razorpay SDK not installed and mock mode is off"}, status=500)

        client = razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )
        rp_order = client.order.create(
            {
                "amount": amount_paise,
                "currency": currency,
                "payment_capture": 1 if capture else 0,
                "notes": {"order_id": order.id},
            }
        )

        with transaction.atomic():
            payment, created = Payment.objects.get_or_create(
                provider_order_id=rp_order["id"],
                defaults={
                    "order": order,
                    "provider": provider,
                    "status": Payment.Status.CREATED,
                    "amount_paise": amount_paise,
                    "currency": currency,
                    "raw_payload": rp_order,
                },
            )
            if not created:
                if payment.order_id != order.id:
                    return Response({"detail": "payment already bound to another order"}, status=409)
                if payment.amount_paise != amount_paise or payment.currency != currency:
                    payment.amount_paise = amount_paise
                    payment.currency = currency
                    payment.raw_payload = rp_order
                    payment.save(update_fields=["amount_paise", "currency", "raw_payload"])

            PaymentEvent.objects.get_or_create(
                provider=provider,
                event_id=rp_order.get("id", f"intent:{rp_order['id']}"),
                defaults={
                    "payment": payment,
                    "event_type": "intent.create",
                    "payload": rp_order,
                },
            )

        return Response(
            {
                "provider": provider,
                "key": settings.RAZORPAY_KEY_ID,
                "currency": currency,
                "amount": amount_paise,
                "razorpay_order_id": rp_order["id"],
            },
            status=200,
        )


class RazorpayWebhookView(APIView):
    """
    Handles Razorpay webhooks. In MOCK mode we skip signature verification.
    """
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def _verify_signature(self, body: bytes, signature: str) -> bool:
        if _use_mock_mode():
            return True

        secret = getattr(settings, "RAZORPAY_WEBHOOK_SECRET", "") or ""
        if not secret:
            return False

        if razorpay:
            try:
                razorpay.Utility.verify_webhook_signature(
                    body.decode("utf-8"), signature, secret
                )
                return True
            except Exception:
                pass

        digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(digest, signature or "")

    @extend_schema(exclude=True)  # keep webhook out of public docs
    @transaction.atomic
    def post(self, request):
        body = request.body
        signature = request.headers.get("X-Razorpay-Signature", "") or request.META.get(
            "HTTP_X_RAZORPAY_SIGNATURE", ""
        )
        if not self._verify_signature(body, signature):
            return Response({"detail": "invalid signature"}, status=400)

        try:
            event = json.loads(body.decode("utf-8"))
        except Exception:
            return Response({"detail": "invalid payload"}, status=400)

        event_id = event.get("id") or f"evt:{int(time.time())}"
        etype = event.get("event", "")

        # Idempotency: use (provider, event_id)
        ev, created = PaymentEvent.objects.get_or_create(
            provider=PaymentProvider.RAZORPAY,
            event_id=event_id,
            defaults={
                "event_type": f"webhook.{etype or 'unknown'}",
                "payload": event,
                "signature": signature,
            },
        )
        if not created:
            return Response({"ok": True, "idempotent": True}, status=200)

        # Attach / update payment when captured
        if etype == "payment.captured" or (_use_mock_mode() and etype in ("payment.captured", "mock.captured")):
            try:
                ent = event["payload"]["payment"]["entity"]
            except Exception:
                return Response({"detail": "missing payment entity"}, status=400)

            rp_order_id = ent.get("order_id")
            payment_id = ent.get("id") or f"pay_mock_{int(time.time())}"
            amount = int(ent.get("amount", 0))
            currency = ent.get("currency", _currency())

            try:
                payment = Payment.objects.select_for_update().get(provider_order_id=rp_order_id)
            except Payment.DoesNotExist:
                ev.payment = None
                ev.save(update_fields=["payment"])
                return Response({"detail": "payment not found"}, status=404)

            ev.payment = payment
            ev.provider = payment.provider
            ev.save(update_fields=["payment", "provider"])

            if payment.provider_payment_id == payment_id and payment.status == Payment.Status.CAPTURED:
                return Response({"ok": True, "idempotent": True}, status=200)

            payment.status = Payment.Status.CAPTURED
            payment.provider_payment_id = payment_id
            if amount:
                payment.amount_paise = amount
            if currency:
                payment.currency = currency
            payment.raw_payload = ent
            payment.save(update_fields=["status", "provider_payment_id", "amount_paise", "currency", "raw_payload"])

            order = payment.order
            if order.status != Order.Status.PAID:
                order.status = Order.Status.PAID
                order.payment_confirmed_at = timezone.now()
                order.save(update_fields=["status", "payment_confirmed_at"])

            PaymentEvent.objects.create(
                payment=payment,
                provider=payment.provider,
                event_id=f"{event_id}:captured",
                event_type="payment.captured",
                payload=ent,
            )
            return Response({"ok": True}, status=200)

        # Unhandled events are recorded already; acknowledge
        return Response({"ignored": etype or "unknown"}, status=200)


class RefundView(APIView):
    """
    Admin-initiated refund. Works in real and mock modes.
    """
    permission_classes = [IsAdminUser]
    serializer_class = RefundSerializer  # for schema

    @extend_schema(request=RefundSerializer, responses={200: None, 400: None, 404: None})
    @transaction.atomic
    def post(self, request):
        ser = RefundSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        order_id = ser.validated_data["order_id"]
        amount_rupees = ser.validated_data.get("amount")  # optional (full refund if None)
        target_pay_id = ser.validated_data.get("provider_payment_id") or ""

        try:
            order = Order.objects.select_for_update().get(pk=order_id)
            qs = order.payments.select_for_update().filter(status=Payment.Status.CAPTURED)
            if target_pay_id:
                payment = qs.get(provider_payment_id=target_pay_id)
            else:
                payment = qs.latest("id")
        except (Order.DoesNotExist, Payment.DoesNotExist):
            return Response({"detail": "captured payment not found"}, status=404)

        remaining = payment.amount_paise - payment.refund_amount_paise
        if remaining <= 0:
            return Response({"detail": "nothing left to refund"}, status=400)

        amount_paise = _rupees_to_paise(amount_rupees) if amount_rupees is not None else remaining
        if amount_paise <= 0 or amount_paise > remaining:
            return Response({"detail": "invalid refund amount"}, status=400)

        # MOCK
        if _use_mock_mode():
            resp = {
                "id": f"rfnd_mock_{int(time.time())}",
                "amount": amount_paise,
                "currency": payment.currency,
                "payment_id": payment.provider_payment_id or "pay_mock",
                "notes": {"mock": True},
                "status": "processed",
            }

            payment.refund_amount_paise += amount_paise
            payment.refund_id = resp["id"]
            payment.status = Payment.Status.REFUNDED if payment.fully_refunded else Payment.Status.PARTIAL_REFUNDED
            payment.save(update_fields=["refund_amount_paise", "refund_id", "status"])

            if payment.status == Payment.Status.REFUNDED and order.status != Order.Status.REFUNDED:
                order.status = Order.Status.REFUNDED
                order.save(update_fields=["status"])

            PaymentEvent.objects.create(
                payment=payment,
                provider=payment.provider,
                event_id=resp["id"],
                event_type="refund.mock",
                payload=resp,
            )
            return Response({"ok": True, "refund_id": payment.refund_id, "mock": True}, status=200)

        # REAL
        if not razorpay:
            return Response({"detail": "Razorpay SDK not installed and mock mode is off"}, status=500)

        client = razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )
        resp = client.payment.refund(payment.provider_payment_id, {"amount": amount_paise})

        payment.refund_amount_paise += int(resp.get("amount", 0))
        payment.refund_id = resp.get("id", "") or payment.refund_id
        payment.status = Payment.Status.REFUNDED if payment.fully_refunded else Payment.Status.PARTIAL_REFUNDED
        payment.save(update_fields=["refund_amount_paise", "refund_id", "status"])

        if payment.status == Payment.Status.REFUNDED and order.status != Order.Status.REFUNDED:
            order.status = Order.Status.REFUNDED
            order.save(update_fields=["status"])

        PaymentEvent.objects.create(
            payment=payment,
            provider=payment.provider,
            event_id=resp.get("id", f"refund:{payment.id}:{payment.refund_amount_paise}"),
            event_type="refund",
            payload=resp,
        )
        return Response({"ok": True, "refund_id": payment.refund_id}, status=200)
