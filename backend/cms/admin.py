from django.contrib import admin
from django.utils.html import format_html
from .models import HomeBanner, HomeRail


@admin.register(HomeBanner)
class HomeBannerAdmin(admin.ModelAdmin):
    list_display = ("id", "thumb", "title", "href", "sort", "is_active", "updated_at")
    list_editable = ("sort", "is_active")
    list_filter = ("is_active",)
    search_fields = ("title", "alt", "href")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("sort", "id")

    def thumb(self, obj):
        try:
            return format_html('<img src="{}" style="height:36px;border-radius:6px" />', obj.image.url)
        except Exception:
            return "—"
    thumb.short_description = "Preview"


@admin.register(HomeRail)
class HomeRailAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "view_all", "sort", "is_active", "updated_at")
    list_editable = ("sort", "is_active")
    list_filter = ("is_active",)
    search_fields = ("title", "view_all")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("sort", "id")
