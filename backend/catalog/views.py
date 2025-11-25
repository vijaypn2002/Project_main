from __future__ import annotations

from django.db.models import Min, Prefetch, Q
from django.db.models.functions import Coalesce
from django.utils.text import slugify

from django_filters import rest_framework as filters  # for DjangoFilterBackend & FilterSet
from rest_framework import viewsets
from rest_framework import filters as drf_filters     # SearchFilter, OrderingFilter
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.decorators import action
from drf_spectacular.utils import extend_schema

from .models import Category, Product, ProductVariant, ProductImage
from .serializers import (
    CategorySerializer,
    CategoryNavSerializer,
    ProductListSerializer,
    ProductDetailSerializer,
    BrandOutSerializer,
)


# ---------- filters ----------

class ProductFilter(filters.FilterSet):
    # Use annotated min_price (sale if present else mrp)
    price_min = filters.NumberFilter(method="filter_price_min")
    price_max = filters.NumberFilter(method="filter_price_max")
    category = filters.CharFilter(field_name="category__slug", lookup_expr="iexact")
    brand = filters.CharFilter(field_name="brand", lookup_expr="icontains")
    q = filters.CharFilter(method="filter_q")

    class Meta:
        model = Product
        fields = ["category", "brand"]

    def filter_price_min(self, qs, name, value):
        return qs.filter(min_price__gte=value)

    def filter_price_max(self, qs, name, value):
        return qs.filter(min_price__lte=value)

    def filter_q(self, qs, name, value):
        return qs.filter(
            Q(name__icontains=value) |
            Q(description__icontains=value) |
            Q(brand__icontains=value)
        )


# ---------- categories ----------

class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET /api/v1/catalog/categories/             → full list
    GET /api/v1/catalog/categories/<slug>/      → one
    GET /api/v1/catalog/categories/nav/         → top belt (label + icon + order)
    """
    queryset = Category.objects.all().order_by("name")
    serializer_class = CategorySerializer
    lookup_field = "slug"
    permission_classes = [AllowAny]

    @action(detail=False, methods=["get"], url_path="nav")
    def nav(self, request):
        qs = Category.objects.filter(show_in_nav=True).order_by("nav_order", "name")
        data = CategoryNavSerializer(qs, many=True, context={"request": request}).data
        return Response(data)


# ---------- products ----------

class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET /api/v1/catalog/products/
    GET /api/v1/catalog/products/<slug>/
    GET /api/v1/catalog/products/trending/
    GET /api/v1/catalog/products/new/
    """
    lookup_field = "slug"
    permission_classes = [AllowAny]

    # enable filters/search/order
    filter_backends = [filters.DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_class = ProductFilter
    search_fields = ["name", "brand", "description"]
    ordering_fields = ["name", "id", "min_price"]

    def get_queryset(self):
        """
        Public catalog: only ACTIVE products.
        Annotate each product with:
          min_price = min(variant.price_sale or variant.price_mrp)
        Prefetch:
          - all images (ordered) for detail pages
          - primary image to `_primary_images` for list pages
        """
        variant_prices = Coalesce(Min("variants__price_sale"), Min("variants__price_mrp"))
        primary_image_qs = ProductImage.objects.filter(is_primary=True).order_by("id")

        return (
            Product.objects.select_related("category")
            .filter(status=Product.Status.ACTIVE)  # NEW: hide drafts/archived in public API
            .prefetch_related(
                Prefetch("variants", queryset=ProductVariant.objects.select_related("inventory")),
                Prefetch("images", queryset=ProductImage.objects.order_by("sort", "id")),
                Prefetch("images", queryset=primary_image_qs, to_attr="_primary_images"),
            )
            .annotate(min_price=variant_prices)
            .distinct()
        )

    def get_serializer_class(self):
        return ProductDetailSerializer if self.action == "retrieve" else ProductListSerializer

    # Ensure list responses always have a single `_primary_image` set (taken from `_primary_images` prefetch)
    def _attach_primary_image(self, iterable):
        for p in iterable:
            if getattr(p, "_primary_images", None):
                p._primary_image = p._primary_images[0]
            else:
                p._primary_image = None

    def list(self, request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(qs)
        if page is not None:
            self._attach_primary_image(page)
            ser = ProductListSerializer(page, many=True, context={"request": request})
            return self.get_paginated_response(ser.data)
        self._attach_primary_image(qs)
        ser = ProductListSerializer(qs, many=True, context={"request": request})
        return Response(ser.data)

    @action(detail=False, methods=["get"])
    def trending(self, request):
        # Placeholder heuristic: latest 8 active products (replace with analytics as needed)
        qs = (
            self.get_queryset()
            .order_by("-id")[:8]
        )
        self._attach_primary_image(qs)
        serializer = ProductListSerializer(qs, many=True, context={"request": request})
        return Response(serializer.data)

    @action(detail=False, methods=["get"], url_path="new")
    def new(self, request):
        # New arrivals rail: latest 12 by created/ID
        qs = (
            self.get_queryset()
            .order_by("-id")[:12]
        )
        self._attach_primary_image(qs)
        serializer = ProductListSerializer(qs, many=True, context={"request": request})
        return Response(serializer.data)


# ---------- brands (derived from Product.brand) ----------

class BrandListView(APIView):
    """
    Public: derive distinct brand names from Product.brand.
    Shape: { name, slug, logo }
    """
    permission_classes = [AllowAny]

    @extend_schema(responses=BrandOutSerializer(many=True))
    def get(self, request):
        names = (
            Product.objects
            .exclude(Q(brand__isnull=True) | Q(brand__iexact=""))
            .values_list("brand", flat=True)
            .distinct()
        )
        items = [{
            "name": name,
            "slug": slugify(name or "") or "",
            "logo": "",  # attach real logo later if you add a Brand model
        } for name in names]
        items.sort(key=lambda x: x["name"].lower())
        return Response(BrandOutSerializer(items, many=True).data)
