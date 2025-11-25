from __future__ import annotations

from django.contrib import admin
from .models import Order, OrderItem, Address, ReturnRequest, ReturnRequestAttachment, OrderEvent


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    can_delete = False
    readonly_fields = ("variant_id", "sku", "name", "attributes", "price", "qty", "line_total")


class OrderEventInline(admin.TabularInline):
    model = OrderEvent
    extra = 0
    can_delete = False
    readonly_fields = ("type", "message", "actor", "created_at")
    ordering = ("-id",)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "email", "status", "total", "payment_provider", "payment_reference", "created_at")
    list_filter = ("status", "created_at", "payment_provider")
    search_fields = ("email", "id", "payment_reference", "tracking_number")
    date_hierarchy = "created_at"
    inlines = [OrderItemInline, OrderEventInline]
    readonly_fields = ()
    ordering = ("-id",)


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ("full_name", "city", "state", "country", "postal_code")
    search_fields = ("full_name", "phone", "line1", "city", "postal_code")
    list_filter = ("state", "country")


class ReturnRequestAttachmentInline(admin.TabularInline):
    model = ReturnRequestAttachment
    extra = 0
    fields = ("file", "mime", "size", "created_at")
    readonly_fields = ("created_at",)
    ordering = ("-id",)


@admin.register(ReturnRequest)
class ReturnRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "order_id_display", "order_item_id", "qty", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("order_item__order__id", "order_item__sku", "order_item__order__email")
    date_hierarchy = "created_at"
    ordering = ("-id",)
    inlines = [ReturnRequestAttachmentInline]

    def order_id_display(self, obj: ReturnRequest):
        return getattr(getattr(obj.order_item, "order", None), "id", None)
    order_id_display.short_description = "order_id"
    order_id_display.admin_order_field = "order_item__order__id"


@admin.register(ReturnRequestAttachment)
class ReturnRequestAttachmentAdmin(admin.ModelAdmin):
    list_display = ("id", "return_request_id", "mime", "size", "created_at")
    list_filter = ("mime", "created_at")
    search_fields = ("return_request__order_item__order__id",)
    date_hierarchy = "created_at"
    ordering = ("-id",)
