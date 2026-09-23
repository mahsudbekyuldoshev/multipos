from django.test import TestCase
from apps.models import Product

class ProductTestCase(TestCase):
    def test_product_creation(self):
        product = Product.objects.create(
            sku="TEST-001",
            name="Test Product",
            price=1000,
            date_received="2026-09-20"
        )
        self.assertEqual(product.sku, "TEST-001")
