from datetime import timedelta

from django.contrib import admin
from django.db.models import Count
from django.utils import timezone

from .models import Cart, CartItem


class ItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ("price_at_add", "attributes_snapshot")


@admin.action(description="Purge stale empty carts (30+ days)")
def purge_stale_empty(modeladmin, request, queryset):
    """
    Deletes carts that have no items and haven't been updated in 30+ days.
    Operates on the full Cart table (ignores the current queryset filters).
    """
    cutoff = timezone.now() - timedelta(days=30)
    qs = (
        Cart.objects.filter(updated_at__lt=cutoff)
        .annotate(item_count=Count("items"))
        .filter(item_count=0)
    )
    deleted, _ = qs.delete()
    modeladmin.message_user(request, f"Deleted {deleted} stale empty carts.")


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "session_id", "applied_coupon", "item_count", "updated_at")
    search_fields = ("session_id",)
    list_filter = ("applied_coupon", "updated_at")
    date_hierarchy = "updated_at"
    inlines = [ItemInline]
    actions = [purge_stale_empty]

    def item_count(self, obj: Cart) -> int:
        return obj.items.count()

    item_count.short_description = "Items"
