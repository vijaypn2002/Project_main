from __future__ import annotations

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.core.exceptions import ValidationError
from catalog.models import Product, ProductVariant


class Wishlist(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="wishlist",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Wishlist({self.user_id})"


class WishlistItem(models.Model):
    """
    A wishlist entry can target either:
      - a specific variant, or
      - a product (no variant chosen yet)

    Rules:
      - At least one of (product, variant) must be set.
      - If variant is set, product is auto-derived from variant.product.
      - No duplicates:
          * unique (wishlist, variant) when variant IS NOT NULL
          * unique (wishlist, product) when product IS NOT NULL AND variant IS NULL
    """
    wishlist = models.ForeignKey(
        Wishlist, on_delete=models.CASCADE, related_name="items"
    )
    product = models.ForeignKey(Product, null=True, blank=True, on_delete=models.CASCADE)
    variant = models.ForeignKey(ProductVariant, null=True, blank=True, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["wishlist", "created_at"]),
            models.Index(fields=["wishlist", "variant"]),
            models.Index(fields=["wishlist", "product"]),
        ]
        constraints = [
            # Must have at least one of product/variant
            models.CheckConstraint(
                check=Q(product__isnull=False) | Q(variant__isnull=False),
                name="wishlistitem_has_target",
            ),
            # If variant provided, (wishlist, variant) must be unique
            models.UniqueConstraint(
                fields=["wishlist", "variant"],
                name="uq_wishlist_variant",
                condition=Q(variant__isnull=False),
            ),
            # If only product provided (no variant), (wishlist, product) must be unique
            models.UniqueConstraint(
                fields=["wishlist", "product"],
                name="uq_wishlist_product_when_no_variant",
                condition=Q(product__isnull=False, variant__isnull=True),
            ),
        ]

    def __str__(self) -> str:
        if self.variant_id:
            return f"{self.wishlist_id}: VAR {self.variant_id}"
        if self.product_id:
            return f"{self.wishlist_id}: PROD {self.product_id}"
        return f"{self.wishlist_id}: <empty>"

    # -------- validation & normalization --------
    def clean(self):
        # Require at least one
        if not self.product_id and not self.variant_id:
            raise ValidationError("Provide either product or variant.")

        # If variant is set, ensure product (if provided) matches; otherwise auto-derive.
        if self.variant_id:
            v_product_id = self.variant.product_id if self.variant_id and self.variant else None
            if self.product_id and v_product_id and self.product_id != v_product_id:
                raise ValidationError("Product does not match the selected variant.")
            # Normalize to keep product in sync for easy filtering
            if v_product_id and not self.product_id:
                self.product_id = v_product_id

        # If only product is set, keep variant null (pure product-level wish)
        if self.product_id and not self.variant_id:
            # nothing more to enforce here
            pass

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)
