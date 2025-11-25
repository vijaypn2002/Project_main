from __future__ import annotations

from rest_framework import serializers
from django.core.exceptions import ObjectDoesNotExist

from catalog.models import Product, ProductVariant
from .models import Wishlist, WishlistItem


class WishlistItemIn(serializers.Serializer):
    product_id = serializers.IntegerField(required=False)
    variant_id = serializers.IntegerField(required=False)

    def validate(self, attrs):
        product_id = attrs.get("product_id")
        variant_id = attrs.get("variant_id")

        # must provide at least one
        if not product_id and not variant_id:
            raise serializers.ValidationError("Provide either product_id or variant_id.")

        # resolve variant and normalize product_id from it
        variant = None
        if variant_id:
            try:
                variant = ProductVariant.objects.select_related("product").get(pk=variant_id)
            except ObjectDoesNotExist:
                raise serializers.ValidationError({"variant_id": "Variant not found."})
            # if product_id not provided, derive from variant
            if not product_id:
                product_id = variant.product_id
            else:
                # if product provided, ensure it matches variant's product
                if product_id != variant.product_id:
                    raise serializers.ValidationError({"product_id": "Product does not match the given variant."})

        else:
            # no variant, ensure the product exists when only product_id given
            try:
                Product.objects.only("id").get(pk=product_id)
            except ObjectDoesNotExist:
                raise serializers.ValidationError({"product_id": "Product not found."})

        # de-dup within this user's wishlist
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            # view already requires auth, but keep a clear message if misused
            raise serializers.ValidationError("Authentication required.")

        wishlist, _ = Wishlist.objects.get_or_create(user=user)

        exists = False
        if variant_id:
            exists = WishlistItem.objects.filter(wishlist=wishlist, variant_id=variant_id).exists()
        else:
            exists = WishlistItem.objects.filter(wishlist=wishlist, product_id=product_id, variant__isnull=True).exists()

        if exists:
            raise serializers.ValidationError("This item is already in your wishlist.")

        # pass normalized ids forward for the view
        attrs["product_id"] = product_id
        if variant:
            attrs["variant_id"] = variant.id
        return attrs


class WishlistItemOut(serializers.ModelSerializer):
    class Meta:
        model = WishlistItem
        fields = ["id", "product_id", "variant_id", "created_at"]
