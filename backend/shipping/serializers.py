from rest_framework import serializers
from .models import ShippingMethod, Shipment


class ShippingQuoteInSerializer(serializers.Serializer):
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2)
    # Optional weight-based pricing
    total_weight_kg = serializers.DecimalField(max_digits=10, decimal_places=3, required=False)


class ShippingMethodQuoteSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    code = serializers.CharField()
    rate = serializers.DecimalField(max_digits=10, decimal_places=2)


class ShipmentCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shipment
        fields = ["id", "order", "method", "carrier", "tracking_no", "status"]


class ShipmentOutSerializer(serializers.ModelSerializer):
    method = serializers.StringRelatedField()

    class Meta:
        model = Shipment
        fields = ["id", "order", "method", "status", "carrier", "tracking_no", "events", "created_at"]
