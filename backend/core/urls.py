# core/urls.py
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse, HttpResponseRedirect
from django.conf import settings
from django.conf.urls.static import static

from backoffice.client_admin import client_admin_site

from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)


def health_view(_request):
    return JsonResponse({"status": "ok"}, status=200)


def api_root_redirect(_request):
    # Handy root that sends devs to interactive docs
    return HttpResponseRedirect("/api/docs/")


urlpatterns = [
    # Admin sites
    path("admin/", admin.site.urls),
    path("client-admin/", client_admin_site.urls),

    # Health & root
    path("health/", health_view, name="health"),
    path("", api_root_redirect, name="api-root"),

    # OpenAPI schema & docs
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),

    # JWT Auth
    path("api/v1/auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/v1/auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/v1/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh_alias"),
    path("api/v1/auth/verify/", TokenVerifyView.as_view(), name="token_verify"),

    # App APIs (v1)
    path("api/v1/", include("catalog.urls")),
    path("api/v1/", include("cart.urls")),
    path("api/v1/", include("orders.urls")),

    # Payments
    path("api/v1/payments/", include("payments.urls")),

    path("api/v1/", include("users.urls")),
    path("api/v1/", include("shipping.urls")),
    path("api/v1/", include("wishlist.urls")),
    path("api/v1/", include("searchapp.urls")),
    path("api/v1/", include("reports.urls")),
    path("api/v1/", include("cms.urls")),
    path("api/v1/", include("backoffice.urls")),
]

# Serve media (and optional static) in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    if getattr(settings, "STATIC_ROOT", None):
        urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
