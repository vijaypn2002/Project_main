from __future__ import annotations
from rest_framework import serializers

# ---------- Checkout ----------

class AddressInputSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=120)
    phone = serializers.CharField(max_length=30)
    line1 = serializers.CharField(max_length=180)
    line2 = serializers.CharField(max_length=180, required=False, allow_blank=True)
    city = serializers.CharField(max_length=120)
    state = serializers.CharField(max_length=120)
    postal_code = serializers.CharField(max_length=20)
    country = serializers.CharField(max_length=2, default="IN")

    def validate_country(self, v: str) -> str:
        v = (v or "").strip().upper()
        # Keep it permissive for now; just normalize to 2-char upper like "IN"
        if len(v) != 2:
            raise serializers.ValidationError("Country must be a 2-letter ISO code.")
        return v


class CheckoutSerializer(serializers.Serializer):
    email = serializers.EmailField()
    shipping_address = AddressInputSerializer()
    shipping_method_id = serializers.IntegerField(required=False)
    coupon_code = serializers.CharField(required=False, allow_blank=True)

    def validate_coupon_code(self, value: str) -> str:
        if value is None:
            return ""
        value = value.strip()
        return value.upper() if value else ""

    def validate_shipping_method_id(self, v: int) -> int:
        if v is None:
            return v
        if v <= 0:
            raise serializers.ValidationError("Invalid shipping method.")
        return v


# ---------- Order output ----------

class OrderItemOutSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    sku = serializers.CharField()
    name = serializers.CharField()
    attributes = serializers.JSONField()
    price = serializers.DecimalField(max_digits=10, decimal_places=2)
    qty = serializers.IntegerField()
    line_total = serializers.DecimalField(max_digits=10, decimal_places=2)
    # snapshot captured at checkout; FE uses this for thumbnails
    image_url = serializers.CharField(required=False, allow_blank=True)


class OrderOutSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    status = serializers.CharField()
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2)
    discount_total = serializers.DecimalField(max_digits=10, decimal_places=2)
    tax_total = serializers.DecimalField(max_digits=10, decimal_places=2)
    shipping_total = serializers.DecimalField(max_digits=10, decimal_places=2)
    total = serializers.DecimalField(max_digits=10, decimal_places=2)
    coupon_code = serializers.CharField(required=False, allow_blank=True)
    tracking_number = serializers.CharField(required=False, allow_blank=True)
    items = OrderItemOutSerializer(many=True)


# ---------- Returns (RMA) ----------

class ReturnRequestInSerializer(serializers.Serializer):
    """
    Create a return for a single order item.
    Example: { "order_item_id": 12, "qty": 1, "reason": "Too small" }
    """
    order_item_id = serializers.IntegerField()
    qty = serializers.IntegerField(min_value=1)
    reason = serializers.CharField(required=False, allow_blank=True)


class ReturnRequestOutSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    order_item_id = serializers.IntegerField()
    qty = serializers.IntegerField()
    status = serializers.CharField()
    reason = serializers.CharField()


# ---------- Return attachments ----------

class ReturnAttachmentInSerializer(serializers.Serializer):
    file = serializers.FileField()


class ReturnAttachmentOutSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    file = serializers.FileField()  # absolute URL patched in view
    mime = serializers.CharField()
    size = serializers.IntegerField()
    created_at = serializers.DateTimeField()
