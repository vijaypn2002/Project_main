from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CartView, CartItemViewSet, ApplyCouponView, CartClearView

app_name = "cart"

router = DefaultRouter()
router.register(r"cart/items", CartItemViewSet, basename="cart-item")

urlpatterns = [
    path("cart/", CartView.as_view(), name="cart"),
    path("cart/clear/", CartClearView.as_view(), name="cart-clear"),
    path("cart/apply-coupon/", ApplyCouponView.as_view(), name="cart-apply-coupon"),
    path("", include(router.urls)),
]
