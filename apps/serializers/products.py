from rest_framework import serializers
from apps.models import Product

class ProductSerializer(serializers.ModelSerializer):
    low_stock = serializers.ReadOnlyField()

    class Meta:
        model = Product
        fields = '__all__'
