from rest_framework import viewsets
from apps.models import User, Markaz
from apps.permissions import IsSuperAdmin
from apps.serializers import (
    UserCreateSerializer, UserSerializer, UserUpdateByAdminSerializer, MarkazSerializer,
)
from drf_spectacular.utils import extend_schema

@extend_schema(tags=["Users"])
class UserViewSet(viewsets.ModelViewSet):
    """Superadmin uchun: kassir yaratish/tahrirlash/o'chirish."""
    queryset = User.objects.filter(role="cashier")
    permission_classes = [IsSuperAdmin]

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        if self.action in ("update", "partial_update"):
            return UserUpdateByAdminSerializer
        return UserSerializer

@extend_schema(tags=["Markazlar"])
class MarkazViewSet(viewsets.ModelViewSet):
    queryset = Markaz.objects.all()
    serializer_class = MarkazSerializer
    permission_classes = [IsSuperAdmin]
