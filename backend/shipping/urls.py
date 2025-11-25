from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import QuoteView, ShipmentViewSet

app_name = "shipping"

router = DefaultRouter()
router.register(r"shipping/shipments", ShipmentViewSet, basename="shipment")

urlpatterns = [
    path("shipping/quote/", QuoteView.as_view(), name="shipping-quote"),
    path("", include(router.urls)),
]
