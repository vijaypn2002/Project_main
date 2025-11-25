from django.contrib import admin
from .models import Address

@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "full_name", "city", "state", "postal_code", "country", "is_default", "created_at")
    list_filter = ("is_default", "country", "state")
    search_fields = ("full_name", "phone", "line1", "city", "state", "postal_code", "user__username", "user__email")
    list_select_related = ("user",)
    ordering = ("-is_default", "-created_at")
    autocomplete_fields = ("user",)   # nicer user picker
