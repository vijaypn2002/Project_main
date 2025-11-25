from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.db.models import Sum, Q, F
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from drf_spectacular.utils import extend_schema

from orders.models import Order, OrderItem
from payments.models import Payment
from .serializers import (
    ReportsSummaryOutSerializer,
    TopProductsOutSerializer,
)

TIMEZONE = timezone.get_current_timezone()


def _parse_date(s: str | None):
    if not s:
        return None
    try:
        # Expect YYYY-MM-DD
        dt = datetime.strptime(s.strip(), "%Y-%m-%d")
        return timezone.make_aware(dt, TIMEZONE).date()
    except Exception:
        return None


def _round2(x: Decimal | float | int) -> Decimal:
    return Decimal(str(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _default_range():
    # last 30 days inclusive [start, end]
    end = timezone.now().date()
    start = end - timedelta(days=29)
    return start, end


def _paid_like_statuses():
    # treat these as monetized for GMV/top-products
    return [
        Order.Status.PAID,
        Order.Status.PICKING,
        Order.Status.SHIPPED,
        Order.Status.DELIVERED,
        Order.Status.RETURNED,
        Order.Status.REFUNDED,
    ]


class ReportsSummaryView(APIView):
    """
    Staff-only summary metrics.

    GET /api/v1/reports/summary?start=YYYY-MM-DD&end=YYYY-MM-DD
    Returns: orders_created, orders_paid, gmv, aov, refunds_count, refunds_amount
    """
    permission_classes = [IsAdminUser]

    @extend_schema(responses=ReportsSummaryOutSerializer)
    def get(self, request):
        start = _parse_date(request.GET.get("start"))
        end = _parse_date(request.GET.get("end"))
        if not start or not end or start > end:
            start, end = _default_range()

        # Normalize range to whole days in the project TZ
        start_dt = timezone.make_aware(datetime.combine(start, datetime.min.time()), TIMEZONE)
        end_dt = timezone.make_aware(datetime.combine(end, datetime.max.time()), TIMEZONE)

        # Orders created in window
        orders_qs = Order.objects.filter(created_at__range=(start_dt, end_dt))
        orders_created = orders_qs.count()

        # Orders paid in window (by created_at window; adjust if you prefer payment_confirmed_at)
        paid_qs = orders_qs.filter(status__in=_paid_like_statuses())
        orders_paid = paid_qs.count()

        # GMV = sum(Order.total) for monetized statuses
        gmv = paid_qs.aggregate(s=Sum("total")).get("s") or Decimal("0.00")
        gmv = _round2(gmv)

        # AOV = GMV / orders_paid
        aov = _round2(Decimal("0.00") if orders_paid == 0 else (gmv / Decimal(orders_paid)))

        # Refunds (payments)
        refund_qs = Payment.objects.filter(
            updated_at__range=(start_dt, end_dt),
            status__in=[Payment.Status.REFUNDED, Payment.Status.PARTIAL_REFUNDED],
        )
        refunds_count = refund_qs.count()
        refunds_amount_paise = refund_qs.aggregate(s=Sum("refund_amount_paise")).get("s") or 0
        refunds_amount = _round2(Decimal(refunds_amount_paise) / Decimal("100"))

        payload = {
            "start": start,
            "end": end,
            "orders_created": orders_created,
            "orders_paid": orders_paid,
            "gmv": gmv,
            "aov": aov,
            "refunds_count": refunds_count,
            "refunds_amount": refunds_amount,
        }
        return Response(ReportsSummaryOutSerializer(payload).data, status=200)


class TopProductsView(APIView):
    """
    Staff-only top products by quantity & revenue (based on OrderItem).

    GET /api/v1/reports/top-products?start=YYYY-MM-DD&end=YYYY-MM-DD&limit=10
    """
    permission_classes = [IsAdminUser]

    @extend_schema(responses=TopProductsOutSerializer)
    def get(self, request):
        start = _parse_date(request.GET.get("start"))
        end = _parse_date(request.GET.get("end"))
        if not start or not end or start > end:
            start, end = _default_range()

        try:
            limit = int(request.GET.get("limit", "10"))
        except Exception:
            limit = 10
        limit = max(1, min(limit, 50))

        start_dt = timezone.make_aware(datetime.combine(start, datetime.min.time()), TIMEZONE)
        end_dt = timezone.make_aware(datetime.combine(end, datetime.max.time()), TIMEZONE)

        qs = (
            OrderItem.objects
            .filter(
                order__created_at__range=(start_dt, end_dt),
                order__status__in=_paid_like_statuses(),
            )
            .values("sku", "name")
            .annotate(
                qty_sold=Sum("qty"),
                revenue=Sum("line_total"),
            )
            .order_by("-revenue", "-qty_sold")[:limit]
        )

        items = []
        for row in qs:
            items.append({
                "sku": row["sku"],
                "name": row["name"],
                "qty_sold": row["qty_sold"] or 0,
                "revenue": _round2(row["revenue"] or Decimal("0.00")),
            })

        out = {"start": start, "end": end, "limit": limit, "items": items}
        return Response(TopProductsOutSerializer(out).data, status=200)
