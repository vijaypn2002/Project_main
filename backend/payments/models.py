# payments/models.py
from __future__ import annotations

from django.db import models
from django.utils import timezone

from orders.models import Order


class PaymentProvider(models.TextChoices):
    RAZORPAY = "razorpay", "Razorpay"
    # STRIPE   = "stripe", "Stripe"  # future-ready


class PaymentConfig(models.Model):
    """
    Admin-managed gateway configuration (one row per provider).
    Only the 'public_key' is safe to expose to clients.
    Secrets must never be returned to the frontend.
    """
    provider = models.CharField(
        max_length=32, choices=PaymentProvider.choices, unique=True, db_index=True
    )

    # Public/publishable identifier (safe for frontend)
    public_key = models.CharField(max_length=200, blank=True)

    # Secrets (keep server-side only). If you prefer field-level encryption,
    # swap CharField -> EncryptedTextField from a lib like django-fernet-fields.
    secret_key = models.CharField(max_length=500, blank=True)
    webhook_secret = models.CharField(max_length=500, blank=True)

    # Operational flags
    live_mode = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)

    # Audit
    updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Payment Configuration"
        verbose_name_plural = "Payment Configurations"

    def __str__(self) -> str:
        mode = "Live" if self.live_mode else "Test"
        state = "Active" if self.is_active else "Disabled"
        return f"{self.get_provider_display()} · {mode} · {state}"


class PaymentStatus(models.TextChoices):
    CREATED = "created", "Created"
    AUTHORIZED = "authorized", "Authorized"
    CAPTURED = "captured", "Captured"
    FAILED = "failed", "Failed"
    REFUNDED = "refunded", "Refunded"
    PARTIAL_REFUNDED = "partial_refunded", "Partial Refunded"


class Payment(models.Model):
    """
    One payment intent/charge per provider 'order'. Amounts stored in paise to avoid
    rounding issues; use helpers to view in rupees.
    """

    # Back-compat aliases so other code can use Payment.Provider / Payment.Status
    Provider = PaymentProvider
    Status = PaymentStatus

    order = models.ForeignKey(
        Order, related_name="payments", on_delete=models.CASCADE
    )
    provider = models.CharField(
        max_length=30,
        choices=PaymentProvider.choices,
        default=PaymentProvider.RAZORPAY,
        db_index=True,
    )

    # Provider identifiers
    # Not globally unique because different providers can reuse same shape of ids.
    provider_order_id = models.CharField(max_length=120, db_index=True)
    provider_payment_id = models.CharField(
        max_length=120, null=True, blank=True, db_index=True
    )

    status = models.CharField(
        max_length=30,
        choices=PaymentStatus.choices,
        default=PaymentStatus.CREATED,
        db_index=True,
    )

    # Amounts in **paise**
    amount_paise = models.PositiveIntegerField(help_text="Total charge amount in paise")
    currency = models.CharField(max_length=10, default="INR")

    # Refund bookkeeping (aggregated across events)
    refund_id = models.CharField(max_length=120, blank=True)
    refund_amount_paise = models.PositiveIntegerField(default=0)

    # For debugging/auditing
    raw_payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)  # useful as status changes

    class Meta:
        indexes = [
            models.Index(fields=["provider", "status"]),
            models.Index(fields=["order", "provider"]),
            models.Index(fields=["provider_order_id"]),
            models.Index(fields=["provider_payment_id"]),
        ]
        constraints = [
            # A given provider_order_id must be unique per provider
            models.UniqueConstraint(
                fields=["provider", "provider_order_id"],
                name="uniq_provider_order_per_provider",
            ),
            # provider_payment_id (when present) must be unique per provider
            models.UniqueConstraint(
                fields=["provider", "provider_payment_id"],
                name="uniq_provider_payment_per_provider",
                condition=models.Q(provider_payment_id__isnull=False),
            ),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.provider}:{self.provider_order_id} ({self.status})"

    # ---- Helpers ----
    @property
    def amount_rupees(self) -> float:
        return round(self.amount_paise / 100.0, 2)

    @property
    def refund_amount_rupees(self) -> float:
        return round(self.refund_amount_paise / 100.0, 2)

    @property
    def fully_refunded(self) -> bool:
        return self.refund_amount_paise >= self.amount_paise


class PaymentEvent(models.Model):
    """
    Stores raw webhook/intent events for idempotency and audit.
    Keep a copy even if we can't yet resolve to a Payment (payment=null).
    """
    payment = models.ForeignKey(
        Payment, null=True, blank=True, on_delete=models.SET_NULL, related_name="events"
    )
    provider = models.CharField(
        max_length=30,
        choices=PaymentProvider.choices,
        default=PaymentProvider.RAZORPAY,
        db_index=True,
    )
    event_id = models.CharField(max_length=128, db_index=True)   # e.g., Razorpay event.id
    event_type = models.CharField(max_length=60, db_index=True)
    signature = models.CharField(max_length=256, blank=True)
    payload = models.JSONField(default=dict, blank=True)
    headers = models.JSONField(default=dict, blank=True)         # optional: store request headers
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("provider", "event_id")]  # idempotency per provider
        indexes = [
            models.Index(fields=["provider", "event_type"]),
            models.Index(fields=["created_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.provider}:{self.event_type}:{self.event_id}"
