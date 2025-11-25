from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RegisterView, MeView, AddressViewSet

app_name = "users"

router = DefaultRouter()
router.register(r"users/addresses", AddressViewSet, basename="user-address")

urlpatterns = [
    path("users/register/", RegisterView.as_view(), name="users-register"),
    path("users/me/", MeView.as_view(), name="users-me"),
    path("", include(router.urls)),
]
