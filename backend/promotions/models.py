from decimal import Decimal
from django.db import models, transaction
from django.db.models import F, Q
from django.core.exceptions import ValidationError
from django.utils import timezone


class CouponQuerySet(models.QuerySet):
    def active(self):
        """
        Active now, not past ends_at, not before starts_at,
        is_active=True, and (if capped) not exhausted.
        """
        now = timezone.now()
        qs = self.filter(
            is_active=True
        ).filter(
            Q(starts_at__isnull=True) | Q(starts_at__lte=now),
            Q(ends_at__isnull=True) | Q(ends_at__gte=now),
        )
        # If max_uses is set, exclude exhausted codes
        return qs.filter(Q(max_uses__isnull=True) | Q(used_count__lt=F("max_uses")))


class Coupon(models.Model):
    TYPE_PERCENTAGE = "percentage"
    TYPE_FIXED = "fixed"

    TYPE_CHOICES = [
        (TYPE_PERCENTAGE, "Percentage"),
        (TYPE_FIXED, "Fixed amount"),
    ]

    code = models.CharField(max_length=40, unique=True, db_index=True)
    discount_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    value = models.DecimalField(max_digits=10, decimal_places=2)  # percent or fixed ₹
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    min_subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    max_uses = models.PositiveIntegerField(null=True, blank=True)
    used_count = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    objects = CouponQuerySet.as_manager()

    class Meta:
        indexes = [
            models.Index(fields=["is_active", "starts_at", "ends_at"]),
        ]

    def __str__(self):
        return self.code

    # -------- Normalization & Validation --------
    def clean(self):
        # Normalize code early (upper + trim)
        if self.code:
            self.code = self.code.strip().upper()

        if self.ends_at and self.starts_at and self.ends_at < self.starts_at:
            raise ValidationError({"ends_at": "End date must be after start date."})

        if self.discount_type == self.TYPE_PERCENTAGE:
            if self.value <= 0 or self.value > 100:
                raise ValidationError({"value": "Percentage must be between 0 and 100."})
        else:
            if self.value < 0:
                raise ValidationError({"value": "Fixed discount must be ≥ 0."})

        if self.min_subtotal is None or self.min_subtotal < 0:
            raise ValidationError({"min_subtotal": "Min subtotal must be ≥ 0."})

        if self.max_uses is not None and self.used_count > self.max_uses:
            raise ValidationError({"used_count": "Used count exceeds max uses."})

    def save(self, *args, **kwargs):
        # ensure normalized code even if .clean() wasn't called externally
        if self.code:
            self.code = self.code.strip().upper()
        super().save(*args, **kwargs)

    # -------- Business helpers --------
    def can_apply(self, subtotal: Decimal) -> tuple[bool, str | None]:
        """Pure check (no DB writes)."""
        now = timezone.now()
        if not self.is_active:
            return False, "Coupon is inactive."
        if self.starts_at and now < self.starts_at:
            return False, "Coupon not started yet."
        if self.ends_at and now > self.ends_at:
            return False, "Coupon has expired."
        if self.max_uses is not None and self.used_count >= self.max_uses:
            return False, "Coupon usage limit reached."
        if subtotal < (self.min_subtotal or Decimal("0.00")):
            return False, "Order does not meet minimum subtotal."
        return True, None

    def compute_discount(self, subtotal: Decimal) -> Decimal:
        """Return the discount amount, capped to subtotal."""
        if self.discount_type == self.TYPE_PERCENTAGE:
            amt = (subtotal * self.value) / Decimal("100")
        else:
            amt = Decimal(self.value)
        return min(amt, subtotal)

    @transaction.atomic
    def redeem(self, email: str, order_id: int | None = None) -> bool:
        """
        Atomically record a redemption (+1 used_count) if allowed.
        Returns True if recorded, False if exhausted.
        """
        # Reload current row with lock to avoid race
        c = Coupon.objects.select_for_update().get(pk=self.pk)
        if c.max_uses is not None and c.used_count >= c.max_uses:
            return False
        c.used_count = F("used_count") + 1
        c.save(update_fields=["used_count"])
        # refresh to get real integer value
        c.refresh_from_db(fields=["used_count"])

        CouponRedemption.objects.create(coupon=c, email=email, order_id=order_id)
        # mirror state onto self
        self.used_count = c.used_count
        return True


class CouponRedemption(models.Model):
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE, related_name="redemptions")
    email = models.EmailField()
    order_id = models.IntegerField(null=True, blank=True)
    used_at = models.DateTimeField(default=timezone.now)

    class Meta:
        indexes = [
            models.Index(fields=["email", "used_at"]),
        ]

    def __str__(self):
        return f"{self.coupon.code} -> {self.email}"
