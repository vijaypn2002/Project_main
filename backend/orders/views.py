# orders/views.py
from __future__ import annotations

import base64
import hashlib
import hmac
from decimal import Decimal
from typing import Dict, Optional, Tuple

from django.conf import settings
from django.db import transaction, IntegrityError
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.utils.encoding import force_bytes

from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.throttling import ScopedRateThrottle
from drf_spectacular.utils import extend_schema

from catalog.models import ProductVariant, Inventory
from promotions.models import Coupon
from .models import (
    Order, OrderItem, Address,
    ReturnRequest, ReturnRequestAttachment, OrderEvent,
    PaymentIdempotency,
)
from .serializers import (
    CheckoutSerializer, OrderOutSerializer,
    ReturnRequestInSerializer, ReturnRequestOutSerializer,
    ReturnAttachmentInSerializer, ReturnAttachmentOutSerializer,
)
from orders.pricing import price_cart, _to_decimal, _round2
from cart.views import _get_or_create_cart
from .validation import validate_coupon_for_cart


# ---------- Image helpers ----------

def _safe_filefield_url(f) -> str:
    """Return a FileField/FieldFile URL if resolvable, else empty string."""
    try:
        return f.url
    except Exception:
        return ""


def _callable_str(obj, name) -> str:
    val = getattr(obj, name, None)
    if callable(val):
        try:
            out = val()
            return str(out or "")
        except Exception:
            return ""
    return ""


def _string_attr(obj, *names) -> str:
    """Return first non-empty string or file URL for the given attribute names."""
    for n in names:
        if hasattr(obj, n):
            v = getattr(obj, n)
            if isinstance(v, str) and v:
                return v
            if hasattr(v, "url"):
                u = _safe_filefield_url(v)
                if u:
                    return u
    return ""


def _best_variant_image(variant: ProductVariant) -> str:
    """
    Choose the best image for a variant.
    Priority:
      1) Product.images primary (is_primary=True)
      2) Product.images first by (sort, id)
      3) Variant single-file fields / URL strings
      4) Product single-file fields / URL strings
      5) Helper methods returning URL
      6) Variant.attributes JSON URL keys
    """
    product = getattr(variant, "product", None)

    # 1) ProductImage relation (prefer primary)
    if product and hasattr(product, "images"):
        primary = product.images.filter(is_primary=True).first()
        if primary and getattr(primary, "image", None):
            u = _safe_filefield_url(primary.image)
            if u:
                return u
        any_img = product.images.order_by("sort", "id").first()
        if any_img and getattr(any_img, "image", None):
            u = _safe_filefield_url(any_img.image)
            if u:
                return u

    # 3) Variant-level fields (file or string)
    s = _string_attr(
        variant,
        "image", "primary_image", "thumbnail", "thumb",
        "photo", "image1", "image_url", "primary_image_url"
    )
    if s:
        return s

    # 4) Product-level fields (file or string)
    if product:
        s = _string_attr(
            product,
            "image", "primary_image", "thumbnail", "cover",
            "thumb", "photo", "image1", "image_url", "primary_image_url"
        )
        if s:
            return s

    # 5) Helper methods returning URL
    for obj in (variant, product):
        if not obj:
            continue
        for m in ("get_image_url", "get_primary_image_url", "image_url", "primary_image_url"):
            cs = _callable_str(obj, m)
            if cs:
                return cs

    # 6) Attributes fallback
    attrs = getattr(variant, "attributes", None) or {}
    for key in ("image_url", "primary_image_url", "thumbnail_url", "thumb_url", "img", "url"):
        val = attrs.get(key)
        if isinstance(val, str) and val:
            return val

    return ""


def _abs_url(request, url: str) -> str:
    if not url:
        return ""
    if url.startswith(("http://", "https://")):
        return url
    return request.build_absolute_uri(url)


def _ensure_item_image_url(request, item: OrderItem) -> str:
    """Prefer snapshot; if missing (legacy rows), resolve live from variant/product."""
    snap = (getattr(item, "image_url", "") or "").strip()
    if snap:
        return snap if snap.startswith(("http://", "https://")) else _abs_url(request, snap)
    try:
        v = ProductVariant.objects.select_related("product").get(pk=item.variant_id)
    except ProductVariant.DoesNotExist:
        return ""
    return _abs_url(request, _best_variant_image(v))


# ---------- Serialization ----------

def _serialize_order(order: Order, request=None) -> dict:
    """
    Serialize an Order with preloaded items. Callers should prefetch `items`
    on the queryset to avoid N+1 queries.
    """
    items = []
    # order.items is expected to be prefetched by caller for performance
    for it in order.items.all():
        items.append({
            "id": it.id,
            "sku": it.sku,
            "name": it.name,
            "attributes": it.attributes or {},
            "price": it.price,
            "qty": it.qty,
            "line_total": it.line_total,
            "image_url": _ensure_item_image_url(request, it) if request else (getattr(it, "image_url", "") or ""),
        })
    return {
        "id": order.id,
        "status": order.status,
        "subtotal": order.subtotal,
        "discount_total": order.discount_total,
        "tax_total": order.tax_total,
        "shipping_total": order.shipping_total,
        "total": order.total,
        "coupon_code": order.coupon_code,
        "tracking_number": order.tracking_number,
        "items": items,
    }


def _get_order_for_returns(request, pk: int) -> Optional[Order]:
    """
    Resolve an order for return operations.
    - Staff: by id
    - Auth user: by id & their email
    - Anonymous: by id & ?email=
    """
    qs = Order.objects.filter(pk=pk)
    user = getattr(request, "user", None)
    qp_email = (request.query_params.get("email") or "").strip().lower()
    if user and user.is_authenticated:
        if getattr(user, "is_staff", False):
            return qs.first()
        return qs.filter(email__iexact=getattr(user, "email", "")).first()
    if qp_email:
        return qs.filter(email__iexact=qp_email).first()
    return None


# ---------- Checkout ----------

class CheckoutView(APIView):
    """
    POST /checkout/  → create order from current cart
    """
    authentication_classes = []
    permission_classes = []
    serializer_class = CheckoutSerializer

    @extend_schema(request=CheckoutSerializer, responses={201: OrderOutSerializer})
    def post(self, request):
        ser = CheckoutSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        cart = _get_or_create_cart(request)
        if not cart.items.exists():
            return Response({"detail": "Cart is empty."}, status=400)

        # Coupon
        req_code = ser.validated_data.get("coupon_code", "") or ""
        if req_code == "":
            if cart.applied_coupon_id:
                cart.applied_coupon = None
                cart.save(update_fields=["applied_coupon"])
        else:
            try:
                coupon = Coupon.objects.active().get(code__iexact=req_code)
                cart.applied_coupon = coupon
                cart.save(update_fields=["applied_coupon"])
            except Coupon.DoesNotExist:
                return Response({"detail": "Invalid or expired coupon.", "code": req_code}, status=400)

        # Shipping method
        shipping_method = None
        sm_id = ser.validated_data.get("shipping_method_id")
        if sm_id:
            from shipping.models import ShippingMethod
            try:
                shipping_method = ShippingMethod.objects.get(pk=sm_id, is_active=True)
            except ShippingMethod.DoesNotExist:
                return Response({"detail": "Invalid shipping method."}, status=400)

        # Variants
        variant_ids = list(cart.items.values_list("variant_id", flat=True))
        variants = (
            ProductVariant.objects
            .select_related("product")
            .prefetch_related("inventory")
            .filter(id__in=variant_ids)
        )
        vmap: Dict[int, ProductVariant] = {v.id: v for v in variants}

        # Stock pre-check (non-locking pass for quick failures)
        for ci in cart.items.all():
            v = vmap.get(ci.variant_id)
            if not v:
                return Response({"detail": f"Variant {ci.variant_id} not found."}, status=400)
            inv = getattr(v, "inventory", None)
            stock = getattr(inv, "qty_available", 0)
            backorder = getattr(inv, "backorder_policy", "block")
            # treat 'notify' like 'allow' here
            if backorder not in {"allow", "notify"} and ci.qty > stock:
                return Response({"detail": f"Insufficient stock for {v.sku}. Available: {stock}."}, status=400)

        # Totals & coupon validation
        totals = price_cart(cart, shipping_method=shipping_method)
        ok, msg = validate_coupon_for_cart(cart, subtotal=totals["subtotal"])
        if not ok:
            return Response({"detail": msg or "Coupon not applicable."}, status=400)

        with transaction.atomic():
            # Lock inventory rows for race-free decrement
            inv_qs = Inventory.objects.select_for_update().filter(variant_id__in=variant_ids)
            inv_map: Dict[int, Inventory] = {inv.variant_id: inv for inv in inv_qs}

            for ci in cart.items.all():
                inv = inv_map.get(ci.variant_id)
                # treat 'notify' like 'allow' in the locked pass too
                if inv and inv.backorder_policy not in {"allow", "notify"} and ci.qty > inv.qty_available:
                    return Response(
                        {"detail": f"Insufficient stock for item {ci.variant_id}."},
                        status=status.HTTP_409_CONFLICT,
                    )

            addr = Address.objects.create(**(ser.validated_data["shipping_address"]))
            order = Order.objects.create(
                email=ser.validated_data["email"],
                shipping_address=addr,
                subtotal=_round2(totals["subtotal"]),
                discount_total=_round2(totals["discount_total"]),
                tax_total=_round2(totals["tax_total"]),
                shipping_total=_round2(totals["shipping_total"]),
                total=_round2(totals["grand_total"]),
                shipping_method=shipping_method,
                coupon_code=getattr(cart.applied_coupon, "code", "") or "",
                status=Order.Status.CREATED,
            )

            # Items (+ image snapshot)
            for it in cart.items.select_related("variant", "variant__product"):
                v = vmap[it.variant_id]
                unit_price = _to_decimal(it.price_at_add or v.price_sale or v.price_mrp)
                line_total = _round2(unit_price * it.qty)

                raw_img = _best_variant_image(v)
                img_abs = _abs_url(request, raw_img)

                OrderItem.objects.create(
                    order=order,
                    variant_id=v.id,
                    sku=v.sku,
                    name=v.product.name,
                    attributes=it.attributes_snapshot or {},
                    price=unit_price,
                    qty=it.qty,
                    line_total=line_total,
                    image_url=img_abs,
                )

                inv = inv_map.get(v.id)
                # only decrement when backorders are NOT allowed/notify
                if inv and inv.backorder_policy not in {"allow", "notify"}:
                    if it.qty > inv.qty_available:
                        # Race detected between pre-check and locked pass
                        return Response(
                            {"detail": f"Race detected for {v.sku}; try again."},
                            status=status.HTTP_409_CONFLICT,
                        )
                    inv.qty_available = inv.qty_available - it.qty
                    inv.save(update_fields=["qty_available"])

            # Clear cart
            cart.items.all().delete()
            cart.applied_coupon = None
            cart.save(update_fields=["applied_coupon"])

            OrderEvent.log(order, "created", "Order created via checkout")

        return Response(_serialize_order(order, request), status=201)


# ---------- Public (by email) ----------

class OrderListView(APIView):
    """GET /orders/?email=<email> — public lookup by email."""
    authentication_classes = []
    permission_classes = []
    throttle_scope = "orders-public"
    throttle_classes = [ScopedRateThrottle]

    @extend_schema(responses={200: OrderOutSerializer(many=True)})
    def get(self, request):
        email = (request.query_params.get("email") or "").strip()
        if not email:
            return Response({"detail": "email query param is required"}, status=400)
        orders = (
            Order.objects
            .filter(email=email)
            .order_by("-id")
            .prefetch_related("items")
        )
        data = [_serialize_order(o, request) for o in orders]
        return Response(data, status=200)


class OrderDetailView(APIView):
    """GET /orders/<id>/?email=<email> — public order by id+email."""
    authentication_classes = []
    permission_classes = []
    throttle_scope = "orders-public"
    throttle_classes = [ScopedRateThrottle]

    @extend_schema(responses={200: OrderOutSerializer})
    def get(self, request, pk: int):
        email = (request.query_params.get("email") or "").strip()
        if not email:
            return Response({"detail": "email query param is required"}, status=400)
        try:
            order = (
                Order.objects
                .filter(pk=pk, email=email)
                .prefetch_related("items")
                .get()
            )
        except Order.DoesNotExist:
            return Response({"detail": "Order not found"}, status=404)
        return Response(_serialize_order(order, request), status=200)


# ---------- Authenticated (by JWT user) ----------

class MyOrdersView(APIView):
    """GET /orders/me/ — authenticated user's orders."""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: OrderOutSerializer(many=True)})
    def get(self, request):
        orders = (
            Order.objects
            .filter(email=request.user.email)
            .order_by("-id")
            .prefetch_related("items")
        )
        data = [_serialize_order(o, request) for o in orders]
        return Response(data, status=200)


class MyOrderDetailView(APIView):
    """GET /orders/me/<id>/ — authenticated user's single order."""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: OrderOutSerializer})
    def get(self, request, pk: int):
        try:
            order = (
                Order.objects
                .filter(pk=pk, email=request.user.email)
                .prefetch_related("items")
                .get()
            )
        except Order.DoesNotExist:
            return Response({"detail": "Not found"}, status=404)
        return Response(_serialize_order(order, request), status=200)


# ---------- Returns ----------

class ReturnRequestView(APIView):
    """POST/GET returns for a given order id (auth required)."""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(request=ReturnRequestInSerializer, responses={201: ReturnRequestOutSerializer})
    def post(self, request, pk: int):
        rser = ReturnRequestInSerializer(data=request.data)
        rser.is_valid(raise_exception=True)

        order = _get_order_for_returns(request, pk)
        if not order:
            return Response({"detail": "Order not found or not permitted"}, status=404)

        if order.status not in {"paid", "delivered"}:
            return Response({"detail": f"Order not returnable in status '{order.status}'"}, status=400)

        try:
            item = order.items.get(pk=rser.validated_data["order_item_id"])
        except OrderItem.DoesNotExist:
            return Response({"detail": "Order item not found on this order"}, status=404)

        qty = rser.validated_data["qty"]
        if qty < 1 or qty > item.qty:
            return Response({"detail": "invalid return quantity"}, status=400)

        rr = ReturnRequest.objects.create(
            order_item=item,
            qty=qty,
            reason=rser.validated_data.get("reason", "") or "",
        )
        OrderEvent.log(order, "rma_requested", f"RMA {rr.id} requested for item {item.id}")
        out = {
            "id": rr.id,
            "order_item_id": item.id,
            "qty": rr.qty,
            "status": rr.status,
            "reason": rr.reason,
        }
        return Response(out, status=201)

    @extend_schema(responses={200: ReturnRequestOutSerializer(many=True)})
    def get(self, request, pk: int):
        order = _get_order_for_returns(request, pk)
        if not order:
            return Response({"detail": "Order not found or not permitted"}, status=404)
        q = ReturnRequest.objects.filter(order_item__order=order).order_by("-id")
        data = [
            {
                "id": r.id,
                "order_item_id": r.order_item_id,
                "qty": r.qty,
                "status": r.status,
                "reason": r.reason,
            }
            for r in q
        ]
        return Response(data, status=200)


# ---------- Return Attachments ----------

class ReturnAttachmentView(APIView):
    """GET/POST attachments on a specific return (auth required)."""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def _get_return_for_user(self, request, order_id: int, return_id: int) -> Tuple[Optional[Order], Optional[ReturnRequest]]:
        try:
            if request.user.is_staff:
                order = Order.objects.get(pk=order_id)
            else:
                order = Order.objects.get(pk=order_id, email=request.user.email)
            rr = ReturnRequest.objects.get(pk=return_id, order_item__order=order)
            return order, rr
        except (Order.DoesNotExist, ReturnRequest.DoesNotExist):
            return None, None

    def _abs_url(self, request, filefield) -> str:
        try:
            url = filefield.url
        except Exception:
            return ""
        return request.build_absolute_uri(url)

    @extend_schema(responses={200: ReturnAttachmentOutSerializer(many=True)})
    def get(self, request, pk: int, return_id: int):
        order, rr = self._get_return_for_user(request, pk, return_id)
        if not rr:
            return Response({"detail": "Not found"}, status=404)
        qs = rr.attachments.order_by("-created_at").all()
        ser = ReturnAttachmentOutSerializer(qs, many=True)
        data = ser.data
        for i, a in enumerate(qs):
            data[i]["file"] = self._abs_url(request, a.file)
        return Response(data, status=200)

    @extend_schema(request=ReturnAttachmentInSerializer, responses={201: ReturnAttachmentOutSerializer})
    def post(self, request, pk: int, return_id: int):
        order, rr = self._get_return_for_user(request, pk, return_id)
        if not rr:
            return Response({"detail": "Not found"}, status=404)

        ser = ReturnAttachmentInSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        f = ser.validated_data["file"]
        att = ReturnRequestAttachment.objects.create(
            return_request=rr,
            file=f,
            mime=getattr(f, "content_type", "") or "",
            size=getattr(f, "size", 0) or 0,
        )
        out = ReturnAttachmentOutSerializer(att).data
        out["file"] = self._abs_url(request, att.file)
        return Response(out, status=201)


# ---------- Staff transition & Payment webhook ----------

class OrderTransitionView(APIView):
    """POST /orders/<id>/transition/ — staff-only state changes."""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdminUser]

    @extend_schema(request=None, responses={200: OrderOutSerializer})
    def post(self, request, pk: int):
        new_status = (request.data.get("status") or "").strip().lower()
        if not new_status:
            return Response({"detail": "status is required"}, status=400)
        try:
            order = (
                Order.objects
                .filter(pk=pk)
                .prefetch_related("items")
                .get()
            )
        except Order.DoesNotExist:
            return Response({"detail": "Order not found"}, status=404)

        try:
            prev = order.status
            order.transition(new_status, actor=str(request.user), note=request.data.get("note", ""))
            # If staff marks the order as PAID, redeem any coupon used
            if prev != Order.Status.PAID and new_status == Order.Status.PAID:
                code = (order.coupon_code or "").strip().upper()
                if code:
                    try:
                        c = Coupon.objects.get(code=code)
                        c.redeem(email=order.email, order_id=order.id)
                    except Coupon.DoesNotExist:
                        OrderEvent.log(order, "coupon_missing", f"Coupon not found at redeem: {code}")
        except ValueError as e:
            return Response({"detail": str(e)}, status=400)
        return Response(_serialize_order(order, request), status=200)


def _verify_razorpay_sig(request) -> bool:
    """
    Verify Razorpay webhook signature when a secret is configured.
    """
    secret = getattr(settings, "RAZORPAY_WEBHOOK_SECRET", "") or ""
    if not secret:
        return True  # dev / no secret configured
    signature = request.headers.get("X-Razorpay-Signature", "")
    body = request.body or b""
    digest = hmac.new(force_bytes(secret), body, hashlib.sha256).digest()
    expected = base64.b64encode(digest).decode()
    return hmac.compare_digest(signature, expected)


@method_decorator(csrf_exempt, name="dispatch")
class PaymentWebhookView(APIView):
    """POST /payments/webhook/ — idempotent gateway callbacks."""
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    parser_classes = [JSONParser]

    @extend_schema(request=None, responses={200: None, 400: None})
    def post(self, request):
        data = request.data or {}
        provider = (data.get("provider") or "").lower()
        event_id = data.get("event_id")
        oid = data.get("order_id")
        pref = data.get("payment_reference")
        status_str = (data.get("status") or "").lower()

        if not all([provider, event_id, oid, status_str]):
            return Response({"detail": "provider, event_id, order_id, status required"}, status=400)

        # Verify signature for Razorpay (if secret configured)
        if provider == "razorpay" and not _verify_razorpay_sig(request):
            return Response({"detail": "invalid signature"}, status=400)

        # Idempotency guard
        try:
            PaymentIdempotency.objects.create(event_id=event_id)
        except IntegrityError:
            return Response({"detail": "duplicate"}, status=200)

        try:
            order = Order.objects.get(pk=oid)
        except Order.DoesNotExist:
            return Response({"detail": "order not found"}, status=404)

        if pref:
            order.payment_reference = pref
        order.payment_provider = provider

        if status_str == "success":
            if order.status == Order.Status.CREATED:
                order.transition(Order.Status.PAID, actor="webhook", note=f"{provider}:{pref}")
                # Redeem coupon when payment succeeds
                code = (order.coupon_code or "").strip().upper()
                if code:
                    try:
                        c = Coupon.objects.get(code=code)
                        c.redeem(email=order.email, order_id=order.id)
                    except Coupon.DoesNotExist:
                        OrderEvent.log(order, "coupon_missing", f"Coupon not found at redeem: {code}")
        elif status_str == "refunded":
            if order.status in {Order.Status.PAID, Order.Status.DELIVERED, Order.Status.RETURNED}:
                order.transition(Order.Status.REFUNDED, actor="webhook", note=f"{provider}:{pref}")
        elif status_str == "failed":
            OrderEvent.log(order, "payment_failed", f"{provider}:{pref}")
        else:
            OrderEvent.log(order, "payment_unknown", f"{provider}:{pref}:{status_str}")

        if pref:
            order.save(update_fields=["payment_provider", "payment_reference", "updated_at"])
        else:
            order.save(update_fields=["payment_provider", "updated_at"])
        return Response(status=200)
