# payments/serializers.py
from __future__ import annotations

from rest_framework import serializers

from .models import PaymentProvider


class CreateIntentSerializer(serializers.Serializer):
    """
    Input for creating a payment intent/order at the gateway.
    - If the request user is not authenticated, `email` is required (guest checkout).
    - `provider` defaults to Razorpay but is extensible.
    - `capture` allows you to request immediate capture (if supported by provider).
    """
    order_id = serializers.IntegerField()
    email = serializers.EmailField(required=False)  # required for guests; validated in `validate`
    provider = serializers.ChoiceField(
        choices=PaymentProvider.choices, default=PaymentProvider.RAZORPAY
    )
    capture = serializers.BooleanField(required=False, default=True)

    def validate(self, attrs):
        request = self.context.get("request")
        is_auth = bool(getattr(getattr(request, "user", None), "is_authenticated", False))
        if not is_auth and not attrs.get("email"):
            raise serializers.ValidationError({"email": "Required for guest checkout."})
        return attrs


class PaymentIntentOutSerializer(serializers.Serializer):
    """
    Output for the client to initialize the payment SDK.
    Keep this generic so frontends can render different providers.
    """
    provider = serializers.CharField()
    provider_order_id = serializers.CharField()
    amount_paise = serializers.IntegerField()
    currency = serializers.CharField()
    public_key = serializers.CharField()  # publishable key (safe for frontend)
    # Optional provider-specific extras (e.g., Razorpay: name, description, prefill, notes)
    meta = serializers.DictField(child=serializers.JSONField(), required=False)


class RefundSerializer(serializers.Serializer):
    """
    Request a refund against an order/payment.
    - If `amount` omitted => full refund.
    - You may optionally pass `provider_payment_id` to target a specific charge.
    """
    order_id = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    provider_payment_id = serializers.CharField(required=False, allow_blank=True)
    reason = serializers.CharField(required=False, allow_blank=True, max_length=200)

    def validate_amount(self, value):
        if value is not None and value <= 0:
            raise serializers.ValidationError("Amount must be greater than 0.")
        return value
