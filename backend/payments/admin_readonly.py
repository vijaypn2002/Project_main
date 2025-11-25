from django.contrib import admin
from .models import Payment, PaymentEvent

class ReadOnlyAdmin(admin.ModelAdmin):
    def has_add_permission(self, *a, **kw): return False
    def has_change_permission(self, *a, **kw): return False
    def has_delete_permission(self, *a, **kw): return False

class PaymentROAdmin(ReadOnlyAdmin):
    list_display = ("id","order","provider","status","amount_paise","currency","created_at")

class PaymentEventROAdmin(ReadOnlyAdmin):
    list_display = ("id","event_id","event_type","payment","created_at")
