from typing import Optional
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from .models import Category, Product, ProductVariant, Inventory, ProductImage


# -------- helpers --------

def _abs(request, url: str) -> str:
    """Return absolute URL when request is available."""
    if not url:
        return url
    return request.build_absolute_uri(url) if request else url


# -------- category --------

class CategorySerializer(serializers.ModelSerializer):
    """
    Full category — use this where you need parent/slug etc.
    (Admin flags are intentionally not exposed here.)
    """
    class Meta:
        model = Category
        fields = ["id", "name", "slug", "parent"]


class CategoryNavSerializer(serializers.ModelSerializer):
    """
    Slim serializer for the top navigation belt.
    Shows the label chosen by admin & a small icon.
    """
    label = serializers.SerializerMethodField()
    icon = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ["id", "slug", "label", "icon", "nav_order"]

    def get_label(self, obj) -> str:
        return obj.display_label  # property in the model (nav_label or name)

    def get_icon(self, obj) -> Optional[str]:
        if not obj.icon:
            return None
        request = self.context.get("request")
        return _abs(request, obj.icon.url)


# -------- inventory / images / variants --------

class InventorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Inventory
        fields = ["qty_available", "backorder_policy", "expected_restock_date"]  # added ETA


class ProductImageSerializer(serializers.ModelSerializer):
    # Ensure frontend gets absolute URL irrespective of MEDIA_URL
    image = serializers.SerializerMethodField()

    class Meta:
        model = ProductImage
        fields = ["id", "image", "alt_text", "is_primary"]

    def get_image(self, obj) -> str:
        request = self.context.get("request")
        return _abs(request, getattr(obj.image, "url", ""))


class ProductVariantSerializer(serializers.ModelSerializer):
    inventory = InventorySerializer(read_only=True)

    class Meta:
        model = ProductVariant
        fields = ["id", "sku", "attributes", "price_mrp", "price_sale", "weight", "inventory"]


# -------- products (list/detail) --------

class ProductListSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    min_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    primary_image = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ["id", "name", "slug", "brand", "status", "category", "min_price", "primary_image"]

    @extend_schema_field(ProductImageSerializer)
    def get_primary_image(self, obj) -> Optional[dict]:
        """
        If the view prefetches/annotates `_primary_image`, use it; otherwise
        fall back to the first image marked as primary.
        """
        img = getattr(obj, "_primary_image", None) or obj.images.filter(is_primary=True).first()
        if not img:
            return None
        # pass context so nested serializer can build absolute URL
        return ProductImageSerializer(img, context=self.context).data


class ProductDetailSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    variants = ProductVariantSerializer(many=True, read_only=True)
    images = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ["id", "name", "slug", "description", "brand", "status", "category", "variants", "images"]

    def get_images(self, obj):
        # ensure absolute URLs in detail too
        return ProductImageSerializer(obj.images.all(), many=True, context=self.context).data


# -------- brands (derived from Product.brand) --------

class BrandOutSerializer(serializers.Serializer):
    name = serializers.CharField()
    slug = serializers.CharField()
    logo = serializers.CharField(required=False, allow_blank=True)
