from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone


class Address(models.Model):
    full_name = models.CharField(max_length=120)
    phone = models.CharField(max_length=30)
    line1 = models.CharField(max_length=180)
    line2 = models.CharField(max_length=180, blank=True)
    city = models.CharField(max_length=120)
    state = models.CharField(max_length=120)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=2, default="IN")

    def __str__(self):
        return f"{self.full_name}, {self.line1}, {self.city}"

    class Meta:
        indexes = [
            models.Index(fields=["postal_code"]),
            models.Index(fields=["city", "state"]),
        ]


class Order(models.Model):
    class Status(models.TextChoices):
        CREATED = "created", "Created"
        PAID = "paid", "Paid"
        PICKING = "picking", "Picking"
        SHIPPED = "shipped", "Shipped"
        DELIVERED = "delivered", "Delivered"
        CANCELLED = "cancelled", "Cancelled"
        RETURNED = "returned", "Returned"
        REFUNDED = "refunded", "Refunded"

    # Who/where
    email = models.EmailField(db_index=True)
    shipping_address = models.ForeignKey(Address, on_delete=models.PROTECT, related_name="orders")

    # Status + key timestamps
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.CREATED, db_index=True)
    payment_confirmed_at = models.DateTimeField(null=True, blank=True)
    shipped_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    # Money snapshot (persisted for reconciliation)
    subtotal = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00"), validators=[MinValueValidator(0)]
    )
    discount_total = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00"), validators=[MinValueValidator(0)]
    )
    tax_total = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00"), validators=[MinValueValidator(0)]
    )
    shipping_total = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00"), validators=[MinValueValidator(0)]
    )
    total = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00"), validators=[MinValueValidator(0)]
    )
    currency = models.CharField(max_length=3, default="INR")

    # Shipping & coupon snapshot
    shipping_method = models.ForeignKey("shipping.ShippingMethod", null=True, blank=True, on_delete=models.PROTECT)
    coupon_code = models.CharField(max_length=40, blank=True)

    # Payment & fulfillment metadata
    payment_provider = models.CharField(max_length=20, blank=True)  # razorpay/stripe/cod
    payment_reference = models.CharField(max_length=80, blank=True, db_index=True)
    tracking_number = models.CharField(max_length=80, blank=True, db_index=True)
    refund_total = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00"), validators=[MinValueValidator(0)]
    )

    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["email", "created_at"]),
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["payment_reference"]),
            models.Index(fields=["tracking_number"]),
        ]

    def __str__(self):
        return f"Order #{self.id} ({self.status})"

    # ----- State machine -----
    ALLOWED_TRANSITIONS = {
        "created": {"paid", "cancelled"},
        "paid": {"picking", "cancelled", "refunded"},
        "picking": {"shipped", "cancelled"},
        "shipped": {"delivered"},
        "delivered": {"returned", "refunded"},
        "returned": {"refunded"},
        "cancelled": set(),
        "refunded": set(),
    }

    def can_transition(self, new_status: str) -> bool:
        return new_status in self.ALLOWED_TRANSITIONS.get(self.status, set())

    def transition(self, new_status: str, *, actor: str = "", note: str = ""):
        if not self.can_transition(new_status):
            raise ValueError(f"Invalid transition {self.status} → {new_status}")
        prev = self.status
        self.status = new_status
        now = timezone.now()
        if new_status == self.Status.PAID and not self.payment_confirmed_at:
            self.payment_confirmed_at = now
        if new_status == self.Status.SHIPPED and not self.shipped_at:
            self.shipped_at = now
        if new_status == self.Status.DELIVERED and not self.delivered_at:
            self.delivered_at = now
        if new_status == self.Status.CANCELLED and not self.cancelled_at:
            self.cancelled_at = now
        self.save(
            update_fields=[
                "status",
                "payment_confirmed_at",
                "shipped_at",
                "delivered_at",
                "cancelled_at",
                "updated_at",
            ]
        )
        OrderEvent.log(self, "transition", f"{prev} → {new_status}", actor=actor, note=note)


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    # immutable snapshot
    variant_id = models.IntegerField()
    sku = models.CharField(max_length=64)
    name = models.CharField(max_length=180)
    attributes = models.JSONField(default=dict, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    qty = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    line_total = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])

    # NEW: product image snapshot for rendering orders UI
    image_url = models.URLField(max_length=500, blank=True, default="")

    def __str__(self):
        return f"{self.sku} x {self.qty}"


class ReturnRequest(models.Model):
    class Status(models.TextChoices):
        REQUESTED = "requested", "Requested"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        RECEIVED = "received", "Received"
        REFUNDED = "refunded", "Refunded"

    order_item = models.ForeignKey(OrderItem, on_delete=models.CASCADE, related_name="returns")
    qty = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    reason = models.CharField(max_length=180, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.REQUESTED, db_index=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    received_at = models.DateTimeField(null=True, blank=True)
    refunded_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"RMA#{self.pk} {self.status}"


class ReturnRequestAttachment(models.Model):
    return_request = models.ForeignKey(ReturnRequest, on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(upload_to="returns/")
    mime = models.CharField(max_length=100, blank=True)
    size = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        indexes = [models.Index(fields=["return_request", "created_at"])]

    def __str__(self):
        return f"RMA#{self.return_request_id} file#{self.pk}"


class OrderEvent(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="events")
    type = models.CharField(max_length=32)
    message = models.TextField(blank=True)
    actor = models.CharField(max_length=80, blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        indexes = [models.Index(fields=["order", "created_at"])]

    @classmethod
    def log(cls, order: Order, event_type: str, message: str, *, actor: str = "", note: str = ""):
        msg = message if not note else f"{message} :: {note}"
        return cls.objects.create(order=order, type=event_type, message=msg, actor=actor)


# --- Idempotency for payment webhooks ---
class PaymentIdempotency(models.Model):
    """Simple idempotency record for processed gateway events."""
    event_id = models.CharField(max_length=120, unique=True)
    received_at = models.DateTimeField(default=timezone.now)

    class Meta:
        indexes = [models.Index(fields=["event_id"])]
        verbose_name = "Payment Idempotency"
        verbose_name_plural = "Payment Idempotency"
