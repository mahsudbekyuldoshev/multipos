from rest_framework import viewsets, status, serializers
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from apps.permissions import IsSubscriptionValid
from drf_spectacular.utils import extend_schema
from apps.models import Category
from apps.serializers import CategorySerializer
from django.db import IntegrityError


@extend_schema(tags=["Categories"])
class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsSubscriptionValid]
    pagination_class = None
    lookup_field = "key"

    def get_queryset(self):
        user = self.request.user
        if not user or not user.is_authenticated or not user.company:
            return Category.objects.none()
        return Category.objects.filter(company=user.company)

    def perform_create(self, serializer):
        user = self.request.user
        if not user or not user.is_authenticated or not user.company:
            raise PermissionDenied("Hisobingiz kompaniyaga biriktirilmagan. Administratorga murojaat qiling.")
        try:
            serializer.save(company=user.company)
        except IntegrityError:
            raise serializers.ValidationError({"key": ["Bu kalit allaqachon mavjud."]})

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        company = request.user.company
        if not company:
            raise PermissionDenied("Hisobingiz kompaniyaga biriktirilmagan. Administratorga murojaat qiling.")
        product_count = instance.products.filter(company=company).count()
        if product_count > 0:
            return Response({
                "error": "CATEGORY_IN_USE",
                "message": f"Bu kategoriyada {product_count} ta mahsulot bor, avval ularni boshqa kategoriyaga o'tkazing yoki o'chiring."
            }, status=status.HTTP_409_CONFLICT)
        return super().destroy(request, *args, **kwargs)
