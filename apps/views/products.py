from rest_framework import viewsets, filters, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from django.db import models
from django_filters.rest_framework import DjangoFilterBackend
from apps.models import Product
from apps.serializers import ProductSerializer
from apps.permissions import IsSubscriptionValid
from drf_spectacular.utils import extend_schema

@extend_schema(tags=["Products"])
class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated, IsSubscriptionValid]
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    search_fields = ['name', 'sku']
    filterset_fields = ['category']

    def get_queryset(self):
        user = self.request.user
        if not user or not user.is_authenticated or not user.company:
            return Product.objects.none()
        queryset = Product.objects.filter(company=user.company)
        
        if self.request.query_params.get('lowStockOnly') == 'true':
            queryset = queryset.filter(qty__lte=models.F('min'))
        return queryset

    def create(self, request, *args, **kwargs):
        user = request.user
        if not user or not user.is_authenticated or not user.company:
            raise PermissionDenied("Hisobingiz kompaniyaga biriktirilmagan. Administratorga murojaat qiling.")
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        user = self.request.user
        if not user or not user.is_authenticated or not user.company:
            raise PermissionDenied("Hisobingiz kompaniyaga biriktirilmagan. Administratorga murojaat qiling.")
        serializer.save(company=user.company)
