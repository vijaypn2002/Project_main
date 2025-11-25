# backoffice/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    StaffMeView,
    BannerViewSet,
    CouponViewSet,
    ShippingMethodViewSet,   # NEW
)

router = DefaultRouter()
router.register(r"backoffice/banners", BannerViewSet, basename="bo-banners")
router.register(r"backoffice/coupons",  CouponViewSet,  basename="bo-coupons")
router.register(r"backoffice/shipping-methods", ShippingMethodViewSet, basename="bo-shipping")  # NEW

urlpatterns = [
    path("backoffice/me", StaffMeView.as_view(), name="backoffice-me"),
    path("", include(router.urls)),
]
