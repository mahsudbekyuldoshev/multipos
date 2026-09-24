from django.test import TestCase
from apps.models import Product, Company

class ProductTestCase(TestCase):
    def test_product_creation(self):
        company = Company.objects.create(name="Test Company")
        product = Product.objects.create(
            company=company, sku="TEST-001", name="Test Product",
            price=1000, date_received="2026-09-20"
        )
        self.assertEqual(product.sku, "TEST-001")
