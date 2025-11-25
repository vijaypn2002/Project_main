from django.conf import settings
from django.db import models, transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from catalog.models import ProductVariant, Inventory
from promotions.models import Coupon

User = settings.AUTH_USER_MODEL


class Cart(models.Model):
    user = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.CASCADE, related_name="carts"
    )
    session_id = models.CharField(max_length=64, blank=True, db_index=True)
    applied_coupon = models.ForeignKey(Coupon, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["session_id"]),
            models.Index(fields=["updated_at"]),
        ]

    def __str__(self):
        who = self.user or self.session_id or "guest"
        return f"Cart({who})"

    @transaction.atomic
    def merge_from(self, other: "Cart"):
        """
        Merge another cart's items into self.
        Strategy:
          - settings.CART_MERGE_STRATEGY = "sum" (default) or "max"
        Atomic to avoid races.
        """
        if not other or other.id == self.id:
            return

        strategy = getattr(settings, "CART_MERGE_STRATEGY", "sum")

        other_items = (
            CartItem.objects.select_for_update()
            .filter(cart=other)
            .select_related("variant", "variant__inventory")
        )
        mine_map = {ci.variant_id: ci for ci in self.items.select_for_update()}

        for oi in other_items:
            if oi.variant_id in mine_map:
                mi = mine_map[oi.variant_id]
                if strategy == "sum":
                    mi.qty = mi.qty + oi.qty
                else:  # "max"
                    mi.qty = max(mi.qty, oi.qty)
                mi.full_clean()
                mi.save(update_fields=["qty"])
            else:
                # Avoid ignore_conflicts: handle any race explicitly.
                ci, created = CartItem.objects.select_for_update().get_or_create(
                    cart=self,
                    variant=oi.variant,
                    defaults={
                        "qty": oi.qty,
                        "price_at_add": oi.price_at_add,
                        "attributes_snapshot": oi.attributes_snapshot,
                    },
                )
                if not created:
                    if strategy == "sum":
                        ci.qty = ci.qty + oi.qty
                    else:
                        ci.qty = max(ci.qty, oi.qty)
                    ci.full_clean()
                    ci.save(update_fields=["qty"])

        if other.applied_coupon and not self.applied_coupon:
            self.applied_coupon = other.applied_coupon
        self.save(update_fields=["applied_coupon", "updated_at"])
        other.delete()


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, related_name="items", on_delete=models.CASCADE)
    variant = models.ForeignKey(ProductVariant, on_delete=models.PROTECT, related_name="+")
    qty = models.PositiveIntegerField(default=1)
    price_at_add = models.DecimalField(max_digits=10, decimal_places=2)
    attributes_snapshot = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["cart", "variant"], name="uq_cart_variant")
        ]
        indexes = [
            models.Index(fields=["cart", "variant"]),
        ]

    def __str__(self):
        return f"{self.variant.sku} x {self.qty}"

    # ---- Inventory / backorder helpers ----
    def _cap_qty_against_stock(self) -> int:
        inv: Inventory | None = getattr(self.variant, "inventory", None)
        stock = getattr(inv, "qty_available", None)
        backorder_policy = getattr(inv, "backorder_policy", "block")
        if stock is None:
            return self.qty  # no inventory record -> don't cap here
        if backorder_policy in ("allow", "notify"):
            # 'notify' behaves like 'allow' for quantity acceptance; UI can show expected date
            return self.qty
        # block backorder: cap to stock (may be zero)
        return min(self.qty, max(int(stock), 0))

    def is_backordered(self) -> bool:
        inv: Inventory | None = getattr(self.variant, "inventory", None)
        if not inv:
            return False
        policy = getattr(inv, "backorder_policy", "block")
        stock = getattr(inv, "qty_available", 0)
        return policy in ("allow", "notify") and int(stock or 0) < int(self.qty or 0)

    # ---- Validation / normalization ----
    def clean(self):
        # Normalize qty
        if self.qty is None or self.qty < 1:
            self.qty = 1

        # Hard cap to avoid abuse / unrealistic quantities
        max_qty = getattr(settings, "CART_MAX_QTY", 99)
        if self.qty > max_qty:
            self.qty = max_qty

        # Price/attributes defaults
        if not self.price_at_add:
            self.price_at_add = self.variant.price_sale or self.variant.price_mrp
        if not self.attributes_snapshot:
            self.attributes_snapshot = getattr(self.variant, "attributes", {}) or {}

        # Stock policy
        capped = self._cap_qty_against_stock()
        if capped < 1:
            # No stock and no backorders; tell the client
            raise ValidationError({"qty": "This item is out of stock."})
        # Keep requested qty if backorders allowed/notify, otherwise cap
        if capped != self.qty:
            self.qty = capped

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
