from django.contrib import admin
from .models import Category, Product, ProductVariant, Inventory, ProductImage


class ImageInline(admin.TabularInline):
    model = ProductImage
    extra = 0
    fields = ("image", "alt_text", "is_primary", "sort")
    ordering = ("sort", "id")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "parent", "show_in_nav", "nav_order")
    list_filter = ("show_in_nav", "parent")
    list_editable = ("show_in_nav", "nav_order")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    fieldsets = (
        (None, {"fields": ("name", "slug", "parent")}),
        ("Navigation", {"fields": ("show_in_nav", "nav_label", "nav_order", "icon")}),
    )


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "category", "status")
    list_filter = ("status", "category")
    search_fields = ("name", "brand", "slug")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [ImageInline]


@admin.register(ProductVariant)
class VariantAdmin(admin.ModelAdmin):
    list_display = ("id", "product", "sku", "price_mrp", "price_sale")
    search_fields = ("sku", "product__name")
    list_filter = ("product__category",)


@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ("id", "variant", "qty_available", "backorder_policy")
    list_filter = ("backorder_policy",)
    search_fields = ("variant__sku",)
