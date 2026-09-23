from django.db import transaction
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.utils import timezone
from apps.models import Sale, SaleItem, Product, Settings
from apps.serializers import SaleSerializer, SaleCheckoutSerializer
from django.db.models import Sum
from decimal import Decimal

class InsufficientStockError(Exception):
    def __init__(self, product, requested):
        self.product = product
        self.requested = requested
        super().__init__(f"Insufficient stock for {product.name}")

class SaleViewSet(viewsets.ModelViewSet):
    queryset = Sale.objects.all()
    serializer_class = SaleSerializer
    http_method_names = ['get', 'post', 'head']

    def create(self, request, *args, **kwargs):
        serializer = SaleCheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        items_data = serializer.validated_data['items']
        
        try:
            with transaction.atomic():
                store_name = Settings.objects.first().store_name if Settings.objects.exists() else "MUSTAHKAM SAVDO MARKAZI"
                
                sale = Sale.objects.create(
                    cashier=serializer.validated_data.get('cashier'),
                    store_name=store_name
                )
                total = 0
                
                for item in items_data:
                    qty = Decimal(str(item['qty']))
                    product = Product.objects.select_for_update().get(pk=item['product_id'])
                    if product.qty < qty:
                        raise InsufficientStockError(product, qty)
                    
                    subtotal = product.price * qty
                    total += subtotal
                    
                    SaleItem.objects.create(
                        sale=sale,
                        product=product,
                        product_id_str=product.id,
                        name=product.name,
                        sku=product.sku,
                        category=product.category,
                        date_received=product.date_received,
                        unit=product.unit,
                        price=product.price,
                        qty=qty,
                        subtotal=subtotal
                    )
                    
                    product.qty -= qty
                    product.save()
                
                sale.total = total
                sale.save()
                
            return Response(SaleSerializer(sale).data, status=status.HTTP_201_CREATED)
        except InsufficientStockError as e:
            return Response({
                "error": "INSUFFICIENT_STOCK",
                "message": "Omborda yetarli mahsulot yo'q",
                "details": [{"productId": e.product.id, "requested": float(e.requested), "available": float(e.product.qty)}]
            }, status=status.HTTP_409_CONFLICT)

    @action(detail=False, methods=['get'], url_path='stats/today')
    def stats_today(self, request):
        today = timezone.now().date()
        sales = Sale.objects.filter(date__date=today)
        count = sales.count()
        total = sales.aggregate(Sum('total'))['total__sum'] or 0
        return Response({"count": count, "total": total})
