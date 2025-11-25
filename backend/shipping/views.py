from decimal import Decimal
from django.utils import timezone
from rest_framework import permissions, status, viewsets, serializers as rf_serializers
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser
from drf_spectacular.utils import extend_schema

from .models import ShippingMethod, Shipment
from .serializers import (
    ShippingQuoteInSerializer, ShippingMethodQuoteSerializer,
    ShipmentCreateUpdateSerializer, ShipmentOutSerializer
)

# --- Safe notifications import (no-op in dev if module not present) ---
try:
    from core.notifications import send_shipped, send_delivered  # type: ignore
except Exception:
    def send_shipped(order, shipment):  # no-op
        pass
    def send_delivered(order, shipment):  # no-op
        pass
# ----------------------------------------------------------------------

ALLOWED_TRANSITIONS = {
    "created": {"picked"},
    "picked": {"in_transit"},
    "in_transit": {"delivered", "returned"},
    "delivered": set(),
    "returned": set(),
}


# ----- Inline input serializers for action endpoints -----
class _SetTrackingInSerializer(rf_serializers.Serializer):
    carrier = rf_serializers.CharField(required=False, allow_blank=True)
    tracking_no = rf_serializers.CharField(required=False, allow_blank=True)


class _AdvanceInSerializer(rf_serializers.Serializer):
    status = rf_serializers.ChoiceField(choices=[c[0] for c in Shipment.STATUS])


# ----- Quote -----
class QuoteView(APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = ShippingQuoteInSerializer  # helps schema

    @extend_schema(
        request=ShippingQuoteInSerializer,
        responses={200: ShippingMethodQuoteSerializer(many=True)}
    )
    def post(self, request):
        ser = ShippingQuoteInSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        subtotal = Decimal(ser.validated_data["subtotal"])
        total_weight = Decimal(ser.validated_data.get("total_weight_kg") or 0)

        # Guard against accidental negative inputs
        if subtotal < 0 or total_weight < 0:
            return Response({"detail": "subtotal/weight cannot be negative"}, status=400)

        out = []
        for m in ShippingMethod.objects.filter(is_active=True):
            rate = Decimal(m.base_rate or 0)

            # weight-based adder if configured
            if (m.per_kg or Decimal("0")) > 0 and total_weight > 0:
                rate += (Decimal(m.per_kg) * total_weight)

            # free-over logic
            if m.free_over and subtotal >= m.free_over:
                rate = Decimal("0.00")

            out.append({
                "id": m.id,
                "name": m.name,
                "code": m.code,
                "rate": rate.quantize(Decimal("0.01")),
            })

        return Response(ShippingMethodQuoteSerializer(out, many=True).data, status=200)


# ----- Shipments (admin) -----
class ShipmentViewSet(viewsets.ModelViewSet):
    """
    Admin-only CRUD for shipments + status transitions.
    """
    queryset = Shipment.objects.select_related("order", "method").all()
    serializer_class = ShipmentCreateUpdateSerializer
    permission_classes = [IsAdminUser]

    def get_serializer_class(self):
        return ShipmentOutSerializer if self.action in ("list", "retrieve") else ShipmentCreateUpdateSerializer

    @extend_schema(request=_SetTrackingInSerializer, responses=ShipmentOutSerializer)
    @action(detail=True, methods=["post"])
    def set_tracking(self, request, pk=None):
        shp = self.get_object()
        shp.carrier = request.data.get("carrier", shp.carrier)
        shp.tracking_no = request.data.get("tracking_no", shp.tracking_no)

        ev = list(shp.events or [])
        ev.append({
            "ts": timezone.now().isoformat(),
            "event": "tracking_set",
            "carrier": shp.carrier,
            "tracking_no": shp.tracking_no,
        })
        shp.events = ev
        shp.save(update_fields=["carrier", "tracking_no", "events"])
        return Response(ShipmentOutSerializer(shp).data)

    @extend_schema(request=_AdvanceInSerializer, responses=ShipmentOutSerializer)
    @action(detail=True, methods=["post"])
    def advance(self, request, pk=None):
        """
        Enforce linear transitions:
        created → picked → in_transit → delivered/returned
        """
        shp = self.get_object()
        next_status = request.data.get("status")
        if next_status not in dict(Shipment.STATUS):
            return Response({"detail": "invalid status"}, status=400)

        allowed = ALLOWED_TRANSITIONS.get(shp.status, set())
        if next_status not in allowed:
            return Response({"detail": f"invalid transition: {shp.status} → {next_status}"}, status=409)

        shp.status = next_status
        ev = list(shp.events or [])
        ev.append({"ts": timezone.now().isoformat(), "event": f"status:{next_status}"})
        shp.events = ev
        shp.save(update_fields=["status", "events"])

        # Notify on shipped and delivered (safe no-ops if notifications missing)
        try:
            if next_status == "in_transit":
                send_shipped(shp.order, shp)
            elif next_status == "delivered":
                send_delivered(shp.order, shp)
        except Exception:
            pass

        return Response(ShipmentOutSerializer(shp).data)
