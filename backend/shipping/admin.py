from django.contrib import admin
from django.utils.html import format_html
from .models import ShippingMethod, Shipment

@admin.register(ShippingMethod)
class ShippingMethodAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "code", "rate_type", "base_rate", "per_kg", "free_over", "is_active")
    search_fields = ("name", "code")
    list_filter = ("is_active", "rate_type")
    ordering = ("name",)
    readonly_fields = ()
    # normalize code is handled in model.save()

# ---- Shipment helpers ----

def _advance_queryset(qs, to_status: str) -> int:
    updated = 0
    for shp in qs:
        # enforce allowed transitions roughly like in the view; keep simple here
        allowed = {
            "created": {"picked"},
            "picked": {"in_transit"},
            "in_transit": {"delivered", "returned"},
            "delivered": set(),
            "returned": set(),
        }.get(shp.status, set())
        if to_status in allowed:
            ev = list(shp.events or [])
            ev.append({"ts": shp.created_at.isoformat(), "event": f"status:{to_status}"})
            shp.status = to_status
            shp.events = ev
            shp.save(update_fields=["status", "events"])
            updated += 1
    return updated

@admin.action(description="Advance → Picked")
def action_mark_picked(modeladmin, request, queryset):
    n = _advance_queryset(queryset, "picked")
    modeladmin.message_user(request, f"Moved {n} shipment(s) to Picked.")

@admin.action(description="Advance → In Transit")
def action_mark_in_transit(modeladmin, request, queryset):
    n = _advance_queryset(queryset, "in_transit")
    modeladmin.message_user(request, f"Moved {n} shipment(s) to In Transit.")

@admin.action(description="Advance → Delivered")
def action_mark_delivered(modeladmin, request, queryset):
    n = _advance_queryset(queryset, "delivered")
    modeladmin.message_user(request, f"Moved {n} shipment(s) to Delivered.")

@admin.action(description="Advance → Returned")
def action_mark_returned(modeladmin, request, queryset):
    n = _advance_queryset(queryset, "returned")
    modeladmin.message_user(request, f"Moved {n} shipment(s) to Returned.")

@admin.register(Shipment)
class ShipmentAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "method", "status", "tracking_no", "created_at", "last_event")
    search_fields = ("tracking_no", "order__id")
    list_filter = ("status", "method")
    date_hierarchy = "created_at"
    ordering = ("-id",)
    autocomplete_fields = ("order", "method")
    readonly_fields = ("created_at",)
    list_select_related = ("order", "method")
    actions = [
        action_mark_picked,
        action_mark_in_transit,
        action_mark_delivered,
        action_mark_returned,
    ]

    def last_event(self, obj: Shipment):
        ev = (obj.events or [])
        if not ev:
            return "-"
        e = ev[-1]
        label = e.get("event", "")
        ts = e.get("ts", "")
        return format_html("<span title='{}'>{}</span>", ts, label)
    last_event.short_description = "Last event"
