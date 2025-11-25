from django.conf import settings
from rest_framework import serializers
from catalog.models import ProductVariant

from .models import CartItem

MAX_QTY = getattr(settings, "CART_MAX_QTY", 99)


class CartItemCreateSerializer(serializers.Serializer):
    variant_id = serializers.IntegerField()
    qty = serializers.IntegerField(min_value=1, max_value=MAX_QTY)
    mode = serializers.ChoiceField(choices=("set", "inc"), required=False, default="set")  # NEW

    def validate(self, data):
        variant_id = data["variant_id"]
        qty = data["qty"]

        try:
            variant = ProductVariant.objects.select_related("inventory", "product").get(pk=variant_id)
        except ProductVariant.DoesNotExist:
            raise serializers.ValidationError({"variant_id": "Variant not found"})

        # Respect backorder policy server-side
        inv = getattr(variant, "inventory", None)
        stock = getattr(inv, "qty_available", None)
        backorder_policy = getattr(inv, "backorder_policy", "block")

        # Treat 'notify' like 'allow' (accepted qty, UI will show backordered flag)
        if backorder_policy not in ("allow", "notify") and stock is not None and stock < 1:
            raise serializers.ValidationError({"qty": "Out of stock"})

        if backorder_policy not in ("allow", "notify") and stock is not None and qty > stock:
            data["qty"] = int(stock)

        data["variant"] = variant  # pass through for view
        return data


class CartItemUpdateSerializer(serializers.Serializer):
    qty = serializers.IntegerField(min_value=1, max_value=MAX_QTY)


class CartItemOutSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    variant_id = serializers.IntegerField(source="variant.id")
    sku = serializers.CharField(source="variant.sku")
    name = serializers.CharField(source="variant.product.name")
    attributes = serializers.JSONField(source="attributes_snapshot")
    price = serializers.DecimalField(source="price_at_add", max_digits=10, decimal_places=2)
    qty = serializers.IntegerField()
    backordered = serializers.SerializerMethodField()
    expected_date = serializers.SerializerMethodField()

    def get_backordered(self, obj: CartItem):
        # Prefer model helper if present
        if hasattr(obj, "is_backordered") and callable(obj.is_backordered):
            try:
                return obj.is_backordered()
            except Exception:
                pass
        inv = getattr(obj.variant, "inventory", None)
        if not inv:
            return False
        policy = getattr(inv, "backorder_policy", "block")
        stock = int(getattr(inv, "qty_available", 0) or 0)
        return policy in ("allow", "notify") and stock < int(obj.qty or 0)

    def get_expected_date(self, obj: CartItem):
        inv = getattr(obj.variant, "inventory", None)
        # If your Inventory model exposes an ETA; otherwise returns None
        return getattr(inv, "expected_restock_date", None)


class CartOutSerializer(serializers.Serializer):
    version = serializers.DateTimeField()  # send cart.updated_at from the view
    items = CartItemOutSerializer(many=True)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2)
    discount_total = serializers.DecimalField(max_digits=10, decimal_places=2)
    tax_total = serializers.DecimalField(max_digits=10, decimal_places=2)
    shipping_total = serializers.DecimalField(max_digits=10, decimal_places=2)
    grand_total = serializers.DecimalField(max_digits=10, decimal_places=2)
    coupon = serializers.CharField(allow_null=True, required=False)
