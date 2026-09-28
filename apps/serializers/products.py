from rest_framework import serializers
from apps.models import Product, Category

class ProductSerializer(serializers.ModelSerializer):
    category = serializers.SlugRelatedField(slug_field='key', queryset=Category.objects.all())
    low_stock = serializers.ReadOnlyField()

    class Meta:
        model = Product
        fields = '__all__'
        read_only_fields = ['company']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and hasattr(request.user, 'company') and request.user.company:
            self.fields['category'].queryset = Category.objects.filter(company=request.user.company)
