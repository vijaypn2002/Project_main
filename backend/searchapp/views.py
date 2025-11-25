from typing import List, Dict, Any, Optional
from django.db.models import Min, Prefetch, Q
from django.db.models.functions import Coalesce
from rest_framework.views import APIView
from rest_framework.response import Response

from catalog.models import Product, ProductVariant, ProductImage
from .serializers import ProductHitSerializer, SuggestionOutSerializer


def _parse_int(val, default: int) -> int:
    try:
        v = int(val)
        return v if v >= 0 else default
    except Exception:
        return default


def _abs_url(request, maybe_file_or_url: Optional[str]) -> str:
    """
    Accepts either a FileField (FieldFile) or a string path/URL.
    Returns an absolute URL or "".
    """
    if not maybe_file_or_url:
        return ""
    try:
        url = getattr(maybe_file_or_url, "url", None) or str(maybe_file_or_url)
    except Exception:
        url = ""
    if not url:
        return ""
    if url.startswith(("http://", "https://")):
        return url
    return request.build_absolute_uri(url)


class SearchView(APIView):
    """
    GET /api/v1/search
      ?q=&brand=&category=&price_min=&price_max=&limit=&offset=
    Returns: { count, next_offset, prev_offset, results: [...] }
    """
    def get(self, request):
        q = (request.GET.get("q") or "").strip()
        brand = (request.GET.get("brand") or "").strip()
        category = (request.GET.get("category") or "").strip()
        price_min = (request.GET.get("price_min") or "").strip()
        price_max = (request.GET.get("price_max") or "").strip()

        limit = min(max(_parse_int(request.GET.get("limit"), 12), 1), 50)
        offset = max(_parse_int(request.GET.get("offset"), 0), 0)

        # Annotate min_price = min(variant.price_sale or variant.price_mrp)
        variant_prices = Coalesce(Min("variants__price_sale"), Min("variants__price_mrp"))

        # Prefetch only the primary image (to_attr gives us a list on each product)
        primary_image_qs = ProductImage.objects.filter(is_primary=True).order_by("id")

        qs = (
            Product.objects
            .select_related("category")
            .filter(status=Product.Status.ACTIVE)  # 🔹 Only active products in search
            .prefetch_related(
                Prefetch(
                    "variants",
                    queryset=ProductVariant.objects.only("id", "product_id", "price_mrp", "price_sale"),
                ),
                Prefetch("images", queryset=primary_image_qs, to_attr="_primary_images"),
            )
            .annotate(min_price=variant_prices)
        )

        if q:
            qs = qs.filter(
                Q(name__icontains=q) |
                Q(brand__icontains=q) |
                Q(description__icontains=q)
            )
        if brand:
            qs = qs.filter(brand__icontains=brand)
        if category:
            qs = qs.filter(category__slug__iexact=category)

        if price_min:
            try:
                qs = qs.filter(min_price__gte=price_min)
            except Exception:
                pass
        if price_max:
            try:
                qs = qs.filter(min_price__lte=price_max)
            except Exception:
                pass

        qs = qs.order_by("name").distinct()

        total = qs.count()
        page = list(qs[offset: offset + limit])

        results: List[Dict[str, Any]] = []
        for p in page:
            pim = getattr(p, "_primary_images", None)
            pim = pim[0] if pim else None

            primary_image = None
            if pim:
                primary_image = {
                    "id": pim.id,
                    "image": _abs_url(request, pim.image),  # absolute URL string
                    "alt_text": pim.alt_text or "",
                }

            results.append({
                "id": p.id,
                "name": p.name,
                "slug": p.slug,
                "brand": p.brand or "",
                "category": (
                    {"name": p.category.name, "slug": p.category.slug}
                    if p.category_id else None
                ),
                "min_price": p.min_price or 0,
                "primary_image": primary_image,
            })

        payload = {
            "count": total,
            "next_offset": (offset + limit) if (offset + limit) < total else None,
            "prev_offset": (offset - limit) if (offset - limit) >= 0 else None,
            "results": ProductHitSerializer(results, many=True, context={"request": request}).data,
        }
        return Response(payload)


class SuggestView(APIView):
    """
    GET /api/v1/search/suggest?q=
    Returns: { suggestions: ["…"] }
    Strategy:
      - Top 8 product names that start with q (istartswith)
      - Fallback to icontains if < 8
    """
    def get(self, request):
        q = (request.GET.get("q") or "").strip()
        if not q:
            return Response(SuggestionOutSerializer({"suggestions": []}).data)

        base = (
            Product.objects
            .filter(status=Product.Status.ACTIVE)  # 🔹 Only active products for suggestions
            .only("name")
            .order_by("name")
        )

        names = list(base.filter(name__istartswith=q).values_list("name", flat=True)[:8])
        if len(names) < 8:
            extra = list(
                base.filter(name__icontains=q)
                .exclude(name__in=names)
                .values_list("name", flat=True)[: 8 - len(names)]
            )
            names.extend(extra)

        return Response(SuggestionOutSerializer({"suggestions": names}).data)
