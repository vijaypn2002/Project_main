from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema
from django.utils.cache import patch_response_headers

from .models import HomeBanner, HomeRail
from .serializers import HomeContentOut


class HomeContentView(APIView):
    """
    Public endpoint used by the frontend homepage.

    GET /api/v1/content/home  -> { "banners": [...], "rails": [...] }
    (Also available at /api/v1/cms/home.)
    """
    permission_classes = [AllowAny]  # explicit + clearer in schema

    @extend_schema(responses=HomeContentOut)
    def get(self, request):
        def abs_url(ff):
            try:
                url = ff.url
            except Exception:
                return ""
            return request.build_absolute_uri(url)

        banners = [
            {
                "id": b.id,
                "image": abs_url(b.image) if b.image else "",
                "title": b.title or "",
                "alt": b.alt or "",
                "href": b.href or "",
                # optional timestamps surfaced by serializer
                "createdAt": b.created_at,
                "updatedAt": b.updated_at,
            }
            for b in HomeBanner.objects.filter(is_active=True).order_by("sort", "id")
        ]

        # Rails: title + viewAll; items left empty for now (frontend can still render the section)
        rails = [
            {
                "id": r.id,
                "title": r.title,
                "viewAll": r.view_all or "",
                "sort": r.sort,
                "items": [],  # can hydrate later server-side if needed
            }
            for r in HomeRail.objects.filter(is_active=True).order_by("sort", "id")
        ]

        payload = {"banners": banners, "rails": rails}
        resp = Response(HomeContentOut(payload).data)

        # Light caching to speed up home loads (tune as you like)
        resp["Cache-Control"] = "public, max-age=60"
        patch_response_headers(resp, cache_timeout=60)
        return resp
