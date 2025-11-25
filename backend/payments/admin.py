# payments/admin.py
from __future__ import annotations

import json
from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .models import Payment, PaymentEvent, PaymentConfig


# ---------- helpers ----------

def _paise_to_rupees(paise: int | None) -> str:
    if paise is None:
        return "—"
    return f"{paise/100:.2f}"


def _pretty_json(data) -> str:
    try:
        return json.dumps(data, indent=2, ensure_ascii=False)
    except Exception:
        return str(data)


# ---------- inlines ----------

class PaymentEventInline(admin.TabularInline):
    model = PaymentEvent
    extra = 0
    fields = ("event_id", "event_type", "created_at", "signature_short", "payload_preview")
    readonly_fields = ("event_id", "event_type", "created_at", "signature_short", "payload_preview")
    ordering = ("-created_at",)

    def signature_short(self, obj: PaymentEvent) -> str:
        if not obj.signature:
            return "—"
        return obj.signature[:10] + "…"
    signature_short.short_description = "Signature"

    def payload_preview(self, obj: PaymentEvent) -> str:
        text = _pretty_json(obj.payload)
        return mark_safe(
            f'<pre style="max-height:180px; overflow:auto; padding:8px; background:#f6f8fa; border:1px solid #e1e4e8;">{admin.utils.display_for_value(text)}</pre>'
        )
    payload_preview.short_description = "Payload (preview)"


# ---------- Payment admin ----------

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "order_link",
        "provider",
        "status_badge",
        "amount_rupees",
        "refund_rupees",
        "currency",
        "created_at",
    )
    list_filter = ("provider", "status", "currency", "created_at")
    search_fields = (
        "provider_order_id",
        "provider_payment_id",
        "order__id",
        "order__email",
    )
    ordering = ("-id",)
    date_hierarchy = "created_at"
    list_select_related = ("order",)

    readonly_fields = (
        "order",
        "provider",
        "status",
        "provider_order_id",
        "provider_payment_id",
        "amount_paise",
        "currency",
        "refund_id",
        "refund_amount_paise",
        "created_at",
        "raw_payload_pretty",
        "amount_rupees",
        "refund_rupees",
        "fully_refunded_flag",
    )

    inlines = (PaymentEventInline,)

    fieldsets = (
        ("Linkage", {"fields": ("order", "provider")}),
        ("Identifiers", {"fields": ("provider_order_id", "provider_payment_id", "refund_id")}),
        ("Amounts", {"fields": ("amount_paise", "amount_rupees", "currency", "refund_amount_paise", "refund_rupees", "fully_refunded_flag")}),
        ("Status", {"fields": ("status", "created_at")}),
        ("Raw Payload", {"fields": ("raw_payload_pretty",)}),
    )

    def order_link(self, obj: Payment) -> str:
        if not obj.order_id:
            return "—"
        url = f"/admin/orders/order/{obj.order_id}/change/"
        return format_html('<a href="{}">Order #{}</a>', url, obj.order_id)
    order_link.short_description = "Order"

    def amount_rupees(self, obj: Payment) -> str:
        return _paise_to_rupees(obj.amount_paise)
    amount_rupees.short_description = "Amount (₹)"

    def refund_rupees(self, obj: Payment) -> str:
        return _paise_to_rupees(obj.refund_amount_paise)
    refund_rupees.short_description = "Refunded (₹)"

    def fully_refunded_flag(self, obj: Payment) -> str:
        return "Yes" if obj.fully_refunded else "No"
    fully_refunded_flag.short_description = "Fully refunded?"

    def status_badge(self, obj: Payment) -> str:
        color = {
            Payment.Status.CREATED: "#6c757d",
            Payment.Status.AUTHORIZED: "#0d6efd",
            Payment.Status.CAPTURED: "#198754",
            Payment.Status.FAILED: "#dc3545",
            Payment.Status.REFUNDED: "#20c997",
            Payment.Status.PARTIAL_REFUNDED: "#fd7e14",
        }.get(obj.status, "#6c757d")
        return format_html(
            '<span style="display:inline-block;padding:2px 8px;border-radius:12px;background:{};color:#fff;font-size:12px;">{}</span>',
            color,
            obj.get_status_display(),
        )
    status_badge.short_description = "Status"
    status_badge.admin_order_field = "status"

    def raw_payload_pretty(self, obj: Payment) -> str:
        text = _pretty_json(obj.raw_payload)
        return mark_safe(
            f'<pre style="max-height:320px; overflow:auto; padding:8px; background:#f6f8fa; border:1px solid #e1e4e8;">{admin.utils.display_for_value(text)}</pre>'
        )
    raw_payload_pretty.short_description = "Raw payload"

    def has_add_permission(self, request) -> bool:
        return False


# ---------- PaymentEvent admin ----------

@admin.register(PaymentEvent)
class PaymentEventAdmin(admin.ModelAdmin):
    list_display = ("id", "event_id", "event_type", "payment_link", "created_at")
    list_filter = ("event_type", "created_at")
    search_fields = (
        "event_id",
        "event_type",
        "payment__provider_order_id",
        "payment__provider_payment_id",
        "payment__order__id",
        "payment__order__email",
    )
    ordering = ("-id",)
    date_hierarchy = "created_at"
    readonly_fields = ("event_id", "event_type", "payment", "signature", "payload_pretty", "created_at")

    fields = ("event_id", "event_type", "payment", "signature", "payload_pretty", "created_at")

    def payment_link(self, obj: PaymentEvent) -> str:
        if not obj.payment_id:
            return "—"
        url = f"/admin/payments/payment/{obj.payment_id}/change/"
        return format_html('<a href="{}">Payment #{}</a>', url, obj.payment_id)
    payment_link.short_description = "Payment"

    def payload_pretty(self, obj: PaymentEvent) -> str:
        text = _pretty_json(obj.payload)
        return mark_safe(
            f'<pre style="max-height:320px; overflow:auto; padding:8px; background:#f6f8fa; border:1px solid #e1e4e8;">{admin.utils.display_for_value(text)}</pre>'
        )
    payload_pretty.short_description = "Payload"


# ---------- PaymentConfig admin ----------

@admin.register(PaymentConfig)
class PaymentConfigAdmin(admin.ModelAdmin):
    list_display = ("provider", "live_mode", "is_active", "updated_at")
    readonly_fields = ("updated_at",)
