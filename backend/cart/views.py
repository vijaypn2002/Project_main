import logging
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework import viewsets, mixins, permissions, status, serializers as rf_serializers
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.throttling import ScopedRateThrottle
from drf_spectacular.utils import extend_schema

from orders.pricing import price_cart
from orders.validation import validate_coupon_for_cart
from promotions.models import Coupon
from catalog.models import ProductVariant
from .models import Cart, CartItem
from .serializers import (
    CartItemCreateSerializer,
    CartItemUpdateSerializer,
    CartOutSerializer,
    CartItemOutSerializer,
)

log = logging.getLogger(__name__)

CART_SESSION_KEY = getattr(settings, "CART_SESSION_ID", "cart_session_id")


def _ensure_session_id(request) -> str:
    """Always return a stable session id."""
    sid = request.session.get(CART_SESSION_KEY)
    if sid:
        return sid
    if not request.session.session_key:
        request.session.create()
    sid = request.session.session_key
    request.session[CART_SESSION_KEY] = sid
    request.session.modified = True
    return sid


def _get_or_create_cart(request) -> Cart:
    user = request.user if request.user.is_authenticated else None
    session_id = _ensure_session_id(request)

    if user:
        # Prefer user's most recent cart; merge a guest cart bound to this session if present
        cart = Cart.objects.filter(user=user).order_by("-updated_at").first()
        guest = Cart.objects.filter(user__isnull=True, session_id=session_id).first()
        if not cart:
            cart = guest or Cart.objects.create(user=user, session_id=session_id)
        elif guest and guest.id != cart.id:
            cart.merge_from(guest)
            if cart.session_id != session_id:
                cart.session_id = session_id
                cart.save(update_fields=["session_id"])
        return cart

    cart, _ = Cart.objects.get_or_create(user=None, session_id=session_id)
    return cart


def _touch_cart(cart: Cart) -> None:
    """Bump cart.updated_at without changing business fields (for versioning/ETag)."""
    Cart.objects.filter(pk=cart.pk).update(updated_at=timezone.now())


# ---------- Cart ----------
class CartView(APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = CartOutSerializer  # for drf-spectacular

    @extend_schema(responses=CartOutSerializer)
    def get(self, request):
        cart = _get_or_create_cart(request)
        totals = price_cart(cart)

        # IMPORTANT: pass model instances/queryset; don't pre-serialize
        items_qs = cart.items.select_related("variant", "variant__product")

        payload = {
            "version": cart.updated_at,  # <--- expose cart 'version' to clients
            "items": items_qs,
            **totals,
            "coupon": (cart.applied_coupon.code if cart.applied_coupon else None),
        }
        return Response(CartOutSerializer(instance=payload).data)


# ---------- Items ----------
class CartItemViewSet(
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "cart-items"
    queryset = CartItem.objects.none()  # safety: require get_queryset

    def get_queryset(self):
        cart = _get_or_create_cart(self.request)
        return cart.items.select_related("variant", "variant__product")

    # Tell schema which serializer is used for each action
    def get_serializer_class(self):
        if self.action == "create":
            return CartItemCreateSerializer
        if self.action in ("partial_update", "update"):
            return CartItemUpdateSerializer
        return CartItemOutSerializer

    @transaction.atomic
    @extend_schema(request=CartItemCreateSerializer, responses={201: CartItemOutSerializer})
    def create(self, request, *args, **kwargs):
        cart = _get_or_create_cart(request)
        ser = CartItemCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        # Support either 'variant' (PKRelatedField) or 'variant_id' (IntegerField)
        v = ser.validated_data.get("variant")
        if v is None:
            variant_id = ser.validated_data.get("variant_id")
            v = ProductVariant.objects.get(pk=variant_id)

        qty = ser.validated_data["qty"]
        mode = ser.validated_data.get("mode", "set")

        item, created = CartItem.objects.select_for_update().get_or_create(
            cart=cart,
            variant=v,
            defaults={
                "qty": qty,
                "price_at_add": v.price_sale or v.price_mrp,
                "attributes_snapshot": getattr(v, "attributes", {}) or {},
            },
        )
        if not created:
            if mode == "inc":
                item.qty = item.qty + qty
            else:
                item.qty = qty
            item.save(update_fields=["qty"])

        _touch_cart(cart)  # keep version fresh for clients
        log.info("cart_item_add cart=%s variant=%s qty=%s mode=%s", cart.id, v.id, qty, mode)
        out = CartItemOutSerializer(item).data
        return Response(out, status=status.HTTP_201_CREATED)

    @transaction.atomic
    @extend_schema(request=CartItemUpdateSerializer, responses=CartItemOutSerializer)
    def partial_update(self, request, pk=None):
        item = self.get_queryset().select_for_update().get(pk=pk)
        ser = CartItemUpdateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        item.qty = ser.validated_data["qty"]
        item.save(update_fields=["qty"])
        _touch_cart(item.cart)
        log.info("cart_item_update cart=%s item=%s qty=%s", item.cart_id, item.id, item.qty)
        return Response(CartItemOutSerializer(item).data)

    @transaction.atomic
    @extend_schema(responses={204: None})
    def destroy(self, request, pk=None):
        item = self.get_queryset().select_for_update().get(pk=pk)
        cid = item.cart_id
        cart = item.cart
        iid = item.id
        item.delete()
        _touch_cart(cart)
        log.info("cart_item_delete cart=%s item=%s", cid, iid)
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------- Coupons ----------
class ApplyCouponInSerializer(rf_serializers.Serializer):
    code = rf_serializers.CharField(required=False, allow_blank=True)


class ApplyCouponOutSerializer(rf_serializers.Serializer):
    detail = rf_serializers.CharField()
    code = rf_serializers.CharField(required=False)


class ApplyCouponView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_scope = "apply-coupon"
    serializer_class = ApplyCouponInSerializer

    @extend_schema(
        request=ApplyCouponInSerializer,
        responses={200: ApplyCouponOutSerializer, 400: ApplyCouponOutSerializer},
    )
    def post(self, request):
        code = str(request.data.get("code", "")).strip()
        cart = _get_or_create_cart(request)

        # Remove coupon
        if not code:
            cart.applied_coupon = None
            cart.save(update_fields=["applied_coupon"])
            _touch_cart(cart)
            log.info(
                "coupon_removed cart=%s session=%s user=%s",
                cart.id,
                getattr(request.session, "session_key", None),
                getattr(request.user, "id", None),
            )
            return Response({"detail": "Coupon removed."})

        # Lookup active coupon
        try:
            coupon = Coupon.objects.active().get(code__iexact=code)
        except Coupon.DoesNotExist:
            log.warning("coupon_invalid code=%s cart=%s", code, cart.id)
            return Response({"detail": "Invalid or expired coupon."}, status=400)

        # Temporarily attach, recompute totals, validate, then finalize or rollback
        prev_coupon_id = cart.applied_coupon_id
        cart.applied_coupon = coupon
        cart.save(update_fields=["applied_coupon"])

        try:
            totals = price_cart(cart)
            ok, reason = validate_coupon_for_cart(cart, subtotal=totals["subtotal"])
            if not ok:
                # rollback
                cart.applied_coupon_id = prev_coupon_id
                cart.save(update_fields=["applied_coupon"])
                log.info(
                    "coupon_rejected code=%s cart=%s reason=%s",
                    coupon.code, cart.id, reason
                )
                return Response({"detail": reason or "Coupon not applicable."}, status=400)

            _touch_cart(cart)
            log.info("coupon_applied code=%s cart=%s", coupon.code, cart.id)
            return Response({"detail": "Coupon applied.", "code": coupon.code})

        except Exception as e:
            # defensive rollback
            cart.applied_coupon_id = prev_coupon_id
            cart.save(update_fields=["applied_coupon"])
            log.exception("coupon_apply_error code=%s cart=%s err=%s", code, cart.id, e)
            return Response({"detail": "Coupon processing failed."}, status=400)


# ---------- Utilities (QA/UAT) ----------
class CartClearView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(responses={200: rf_serializers.DictField()})
    def post(self, request):
        # Guard this endpoint in production
        if not settings.DEBUG:
            return Response({"detail": "Disabled in production."}, status=403)

        cart = _get_or_create_cart(request)
        deleted_count, _ = cart.items.all().delete()
        _touch_cart(cart)
        return Response({"detail": "Cart cleared.", "deleted": deleted_count})
