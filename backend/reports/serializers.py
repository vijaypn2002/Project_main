from rest_framework import serializers


class ReportsSummaryOutSerializer(serializers.Serializer):
    start = serializers.DateField()
    end = serializers.DateField()
    orders_created = serializers.IntegerField()
    orders_paid = serializers.IntegerField()
    gmv = serializers.DecimalField(max_digits=14, decimal_places=2)
    aov = serializers.DecimalField(max_digits=14, decimal_places=2)
    refunds_count = serializers.IntegerField()
    refunds_amount = serializers.DecimalField(max_digits=14, decimal_places=2)


class TopProductsItemSerializer(serializers.Serializer):
    sku = serializers.CharField()
    name = serializers.CharField()
    qty_sold = serializers.IntegerField()
    revenue = serializers.DecimalField(max_digits=14, decimal_places=2)


class TopProductsOutSerializer(serializers.Serializer):
    start = serializers.DateField()
    end = serializers.DateField()
    limit = serializers.IntegerField()
    items = TopProductsItemSerializer(many=True)
