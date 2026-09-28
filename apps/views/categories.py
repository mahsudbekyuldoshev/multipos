from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema
from apps.models import Category
from apps.serializers import CategorySerializer


@extend_schema(tags=["Categories"])
class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None
    lookup_field = "key"

    def get_queryset(self):
        return Category.objects.filter(company=self.request.user.company)

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        product_count = instance.products.filter(company=request.user.company).count()
        if product_count > 0:
            return Response({
                "error": "CATEGORY_IN_USE",
                "message": f"Bu kategoriyada {product_count} ta mahsulot bor, avval ularni boshqa kategoriyaga o'tkazing yoki o'chiring."
            }, status=status.HTTP_409_CONFLICT)
        return super().destroy(request, *args, **kwargs)
