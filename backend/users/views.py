from django.contrib.auth.models import User
from rest_framework import generics, permissions, viewsets, decorators, response, status
from .serializers import RegisterSerializer, UserSerializer, AddressSerializer
from .models import Address

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer

class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

class AddressViewSet(viewsets.ModelViewSet):
    serializer_class = AddressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Defaults first, newest first
        return (
            Address.objects.filter(user=self.request.user)
            .order_by("-is_default", "-id")
            .select_related("user")
        )

    def perform_create(self, serializer):
        obj = serializer.save(user=self.request.user)
        if obj.is_default:
            Address.objects.filter(user=self.request.user).exclude(id=obj.id).update(is_default=False)

    def perform_update(self, serializer):
        obj = serializer.save()
        if obj.is_default:
            Address.objects.filter(user=self.request.user).exclude(id=obj.id).update(is_default=False)

    @decorators.action(detail=True, methods=["post"])
    def set_default(self, request, pk=None):
        """
        POST /api/v1/users/addresses/{id}/set_default/
        """
        try:
            addr = self.get_queryset().get(pk=pk)
        except Address.DoesNotExist:
            return response.Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        if not addr.is_default:
            Address.objects.filter(user=request.user).update(is_default=False)
            addr.is_default = True
            addr.save(update_fields=["is_default"])
        return response.Response(AddressSerializer(addr).data)
