from rest_framework import serializers

class CategoryMiniSerializer(serializers.Serializer):
    name = serializers.CharField()
    slug = serializers.CharField()

class ImageMiniSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    # We return an absolute URL string from the view, so use CharField here.
    image = serializers.CharField()
    alt_text = serializers.CharField(allow_blank=True)

class ProductHitSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    slug = serializers.CharField()
    brand = serializers.CharField(allow_blank=True)
    category = CategoryMiniSerializer()
    min_price = serializers.DecimalField(max_digits=10, decimal_places=2)
    primary_image = ImageMiniSerializer(required=False, allow_null=True)

class SuggestionOutSerializer(serializers.Serializer):
    suggestions = serializers.ListField(child=serializers.CharField())
