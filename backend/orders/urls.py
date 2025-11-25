# orders/urls.py
from django.urls import path
from .views import (
    CheckoutView,
    OrderListView, OrderDetailView,
    MyOrdersView, MyOrderDetailView,
    ReturnRequestView, ReturnAttachmentView,
    OrderTransitionView,
)

app_name = "orders"

urlpatterns = [
    # Checkout
    path("checkout/", CheckoutView.as_view(), name="checkout"),

    # Public-by-email
    path("orders/", OrderListView.as_view(), name="order-list"),
    path("orders/<int:pk>/", OrderDetailView.as_view(), name="order-detail"),

    # Authenticated (JWT)
    path("orders/me/", MyOrdersView.as_view(), name="my-order-list"),
    path("orders/me/<int:pk>/", MyOrderDetailView.as_view(), name="my-order-detail"),

    # Returns
    path("orders/<int:pk>/returns/", ReturnRequestView.as_view(), name="order-returns"),
    path(
        "orders/<int:pk>/returns/<int:return_id>/attachments/",
        ReturnAttachmentView.as_view(),
        name="order-return-attachments",
    ),

    # Staff transitions
    path("orders/<int:pk>/transition/", OrderTransitionView.as_view(), name="order-transition"),
]
