from django.urls import path
from .views import CreateIntentView, RazorpayWebhookView, RefundView

urlpatterns = [
    path("create-intent/", CreateIntentView.as_view(), name="payments-create-intent"),
    path("webhook/", RazorpayWebhookView.as_view(), name="payments-webhook"),
    path("refund/", RefundView.as_view(), name="payments-refund"),
]
