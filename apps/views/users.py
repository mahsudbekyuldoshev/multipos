from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.models import User, Markaz
from apps.permissions import IsSuperAdmin
from apps.serializers import (
    UserCreateSerializer, UserSerializer, UserUpdateByAdminSerializer, MarkazSerializer, UserSubscriptionSerializer,
)
from drf_spectacular.utils import extend_schema

@extend_schema(tags=["Users"])
class UserViewSet(viewsets.ModelViewSet):
    """Superadmin uchun: kassir yaratish/tahrirlash/o'chirish va obunani boshqarish."""
    queryset = User.objects.filter(role="cashier")
    permission_classes = [IsSuperAdmin]

    def get_queryset(self):
        return User.objects.filter(role="cashier", company=self.request.user.company)

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        if self.action in ("update", "partial_update"):
            return UserUpdateByAdminSerializer
        return UserSerializer

    @action(detail=True, methods=['put', 'patch', 'post'], url_path='subscription')
    def subscription(self, request, pk=None):
        user = self.get_object()
        serializer = UserSubscriptionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if "status" in serializer.validated_data:
            user.subscription_status = serializer.validated_data['status']
        if "expires_at" in serializer.validated_data:
            user.subscription_expires_at = serializer.validated_data['expires_at']
        user.save()
        return Response(UserSerializer(user).data, status=status.HTTP_200_OK)


@extend_schema(tags=["Markazlar"])
class MarkazViewSet(viewsets.ModelViewSet):
    queryset = Markaz.objects.all()
    serializer_class = MarkazSerializer
    permission_classes = [IsSuperAdmin]

    def get_queryset(self):
        return Markaz.objects.filter(company=self.request.user.company)

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)
