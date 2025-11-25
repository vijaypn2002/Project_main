from rest_framework import serializers
from .models import Coupon

class CouponOutSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = ["code", "discount_type", "value", "min_subtotal"]
