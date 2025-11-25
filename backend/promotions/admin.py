from django.contrib import admin
from .models import Coupon, CouponRedemption


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ("code","discount_type","value","is_active","starts_at","ends_at","used_count","max_uses")
    search_fields = ("code",)
    list_filter = ("discount_type","is_active")
    readonly_fields = ("used_count",)

    def save_model(self, request, obj, form, change):
        # normalize on admin saves too
        if obj.code:
            obj.code = obj.code.strip().upper()
        super().save_model(request, obj, form, change)


@admin.register(CouponRedemption)
class CouponRedemptionAdmin(admin.ModelAdmin):
    list_display = ("coupon","email","order_id","used_at")
    search_fields = ("email","order_id")
    list_filter = ("coupon",)
