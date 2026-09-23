from rest_framework import serializers
from decimal import Decimal
from apps.models import Sale, SaleItem, Product

class SaleItemInputSerializer(serializers.Serializer):
    product_id = serializers.CharField()
    qty = serializers.DecimalField(max_digits=12, decimal_places=3, min_value=Decimal("0.01"))

class SaleCheckoutSerializer(serializers.Serializer):
    items = SaleItemInputSerializer(many=True, min_length=1)
    cashier = serializers.CharField(required=False, allow_blank=True)

class SaleItemSerializer(serializers.ModelSerializer):
    product_id = serializers.CharField(source='product_id_str')

    class Meta:
        model = SaleItem
        fields = ['product_id', 'name', 'sku', 'category', 'date_received', 'unit', 'price', 'qty', 'subtotal']

class SaleSerializer(serializers.ModelSerializer):
    items = SaleItemSerializer(many=True)

    class Meta:
        model = Sale
        fields = '__all__'
        read_only_fields = ['id', 'date', 'total', 'store_name']
