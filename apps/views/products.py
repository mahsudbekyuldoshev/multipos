from rest_framework import viewsets, filters
from django.db import models
from django_filters.rest_framework import DjangoFilterBackend
from apps.models import Product
from apps.serializers import ProductSerializer
from drf_spectacular.utils import extend_schema

@extend_schema(tags=["Products"])
class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    search_fields = ['name', 'sku']
    filterset_fields = ['category']

    def get_queryset(self):
        queryset = super().get_queryset()
        # Filter by company
        queryset = queryset.filter(company=self.request.user.company)
        
        if self.request.query_params.get('lowStockOnly') == 'true':
            queryset = queryset.filter(qty__lte=models.F('min'))
        return queryset

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)
