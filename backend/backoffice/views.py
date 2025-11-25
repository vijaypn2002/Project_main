# backoffice/views.py
from __future__ import annotations

from rest_framework.views import APIView
from rest_framework import viewsets, serializers, filters
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser

from backoffice.permissions import IsStaff
from cms.models import HomeBanner
from promotions.models import Coupon
from shipping.models import ShippingMethod
from .serializers import StaffMeOut


# ---------- Staff identity ----------
class StaffMeView(APIView):
    """
    GET /api/v1/backoffice/me
    Returns basic info for staff-only frontend gating.
    """
    permission_classes = [IsStaff]

    def get(self, request):
        u = request.user
        payload = {
            "id": u.id,
            "username": u.username,
            "email": u.email or "",
            "first_name": u.first_name or "",
            "last_name": u.last_name or "",
            "is_staff": bool(u.is_staff),
        }
        return Response(StaffMeOut(payload).data, status=200)


# ---------- CMS: Banners CRUD ----------
class BannerIn(serializers.ModelSerializer):
    class Meta:
        model = HomeBanner
        fields = ["id", "image", "title", "alt", "href", "sort", "is_active"]


class BannerOut(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = HomeBanner
        fields = ["id", "image", "title", "alt", "href", "sort", "is_active"]

    def get_image(self, obj):
        try:
            req = self.context.get("request")
            return req.build_absolute_uri(obj.image.url) if obj.image else ""
        except Exception:
            return ""


class BannerViewSet(viewsets.ModelViewSet):
    """
    /api/v1/backoffice/banners/ [GET, POST]
    /api/v1/backoffice/banners/<id>/ [GET, PATCH, DELETE]
    """
    queryset = HomeBanner.objects.all().order_by("sort", "id")
    permission_classes = [IsStaff]
    parser_classes = [MultiPartParser, FormParser]

    def get_serializer_class(self):
        return BannerOut if self.action in ("list", "retrieve") else BannerIn

    def get_serializer_context(self):
        return {"request": self.request}


# ---------- Promotions: Coupons CRUD ----------
class CouponIn(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = [
            "id", "code", "discount_type", "value",
            "starts_at", "ends_at", "min_subtotal",
            "max_uses", "is_active",
        ]

    def validate(self, attrs):
        # normalize code to UPPER
        code = attrs.get("code")
        if code:
            attrs["code"] = code.strip().upper()
        return super().validate(attrs)


class CouponOut(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = [
            "id", "code", "discount_type", "value",
            "starts_at", "ends_at", "min_subtotal",
            "max_uses", "used_count", "is_active",
        ]


class CouponViewSet(viewsets.ModelViewSet):
    """
    /api/v1/backoffice/coupons/ [GET, POST]
    /api/v1/backoffice/coupons/<id>/ [GET, PATCH, DELETE]
    """
    queryset = Coupon.objects.all().order_by("-is_active", "code")
    permission_classes = [IsStaff]

    def get_serializer_class(self):
        return CouponOut if self.action in ("list", "retrieve") else CouponIn


# ---------- Shipping: ShippingMethod CRUD ----------
class ShippingMethodIn(serializers.ModelSerializer):
    class Meta:
        model = ShippingMethod
        # Use REAL fields from shipping.models.ShippingMethod
        fields = [
            "id",
            "name",
            "code",
            "rate_type",
            "base_rate",
            "per_kg",
            "free_over",
            "is_active",
        ]


class ShippingMethodOut(serializers.ModelSerializer):
    class Meta:
        model = ShippingMethod
        fields = [
            "id",
            "name",
            "code",
            "rate_type",
            "base_rate",
            "per_kg",
            "free_over",
            "is_active",
        ]


class ShippingMethodViewSet(viewsets.ModelViewSet):
    """
    /api/v1/backoffice/shipping-methods/ [GET, POST]
    /api/v1/backoffice/shipping-methods/<id>/ [GET, PATCH, DELETE]
    """
    # ❗ FIXED: order_by uses existing fields ("name", "id"),
    # not non-existent "sort".
    queryset = ShippingMethod.objects.all().order_by("name", "id")
    permission_classes = [IsStaff]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "code"]
    ordering_fields = [
        "name",
        "code",
        "base_rate",
        "per_kg",
        "free_over",
        "is_active",
        "id",
    ]

    def get_serializer_class(self):
        return ShippingMethodOut if self.action in ("list", "retrieve") else ShippingMethodIn
