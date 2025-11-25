from __future__ import annotations

from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Wishlist, WishlistItem
from .serializers import WishlistItemIn, WishlistItemOut


def _get_wishlist(user):
    wishlist, _ = Wishlist.objects.get_or_create(user=user)
    return wishlist


class WishlistListCreateView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = WishlistItemIn

    def get(self, request):
        w = _get_wishlist(request.user)
        qs = (
            w.items.select_related("product", "variant")
            .order_by("-created_at")
        )
        return Response(WishlistItemOut(qs, many=True).data, status=status.HTTP_200_OK)

    def post(self, request):
        w = _get_wishlist(request.user)
        ser = self.get_serializer(data=request.data)  # includes request in context
        ser.is_valid(raise_exception=True)

        # race-safe insert even if two requests try to add the same item
        obj, created = WishlistItem.objects.get_or_create(
            wishlist=w,
            product_id=ser.validated_data.get("product_id"),
            variant_id=ser.validated_data.get("variant_id"),
        )
        if not created:
            # serializer already guards duplicates, but if a race sneaks in:
            return Response(
                {"detail": "This item is already in your wishlist."},
                status=status.HTTP_200_OK,
            )
        return Response(WishlistItemOut(obj).data, status=status.HTTP_201_CREATED)


class WishlistItemDeleteView(generics.DestroyAPIView):
    """
    Deletes only items that belong to the authenticated user's wishlist.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = WishlistItemOut  # for schema clarity
    lookup_url_kwarg = "item_id"

    def get_queryset(self):
        w = _get_wishlist(self.request.user)
        return w.items.all()
