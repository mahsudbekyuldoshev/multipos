from rest_framework import viewsets, filters
from django.db import models
from django_filters.rest_framework import DjangoFilterBackend
from apps.models import Product
from apps.serializers import ProductSerializer

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    search_fields = ['name', 'sku']
    filterset_fields = ['category']

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.query_params.get('lowStockOnly') == 'true':
            queryset = queryset.filter(qty__lte=models.F('min'))
        return queryset
