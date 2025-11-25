from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone


class ShippingMethod(models.Model):
    RATE_FLAT = "flat"
    RATE_TABLE = "table"

    name = models.CharField(max_length=120)
    code = models.CharField(max_length=60, unique=True, db_index=True)
    rate_type = models.CharField(
        max_length=20,
        choices=[(RATE_FLAT, "Flat"), (RATE_TABLE, "Table")],
        default=RATE_FLAT,
    )
    base_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    per_kg = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    free_over = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)])
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [
            models.Index(fields=["is_active"]),
            models.Index(fields=["rate_type"]),
        ]
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if self.code:
            self.code = self.code.strip().upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.code})"


class Shipment(models.Model):
    STATUS = [
        ("created", "Created"),
        ("picked", "Picked"),
        ("in_transit", "In Transit"),
        ("delivered", "Delivered"),
        ("returned", "Returned"),
    ]

    order = models.ForeignKey("orders.Order", on_delete=models.CASCADE, related_name="shipments")
    method = models.ForeignKey(ShippingMethod, on_delete=models.PROTECT)
    carrier = models.CharField(max_length=60, blank=True)
    tracking_no = models.CharField(max_length=120, blank=True, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS, default="created", db_index=True)
    events = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=["order", "created_at"]),
            models.Index(fields=["status", "created_at"]),
        ]
        ordering = ["-id"]

    def __str__(self):
        return f"Shipment #{self.id} for Order {self.order_id}"
