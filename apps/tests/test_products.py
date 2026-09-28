from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from apps.models import Product, Company, User, Category

class ProductTestCase(TestCase):
    def test_product_creation(self):
        company = Company.objects.create(name="Test Company")
        category = Category.objects.get(company=company, key="qurilish")
        product = Product.objects.create(
            company=company, category=category, sku="TEST-001", name="Test Product",
            price=1000, date_received="2026-09-20"
        )
        self.assertEqual(product.sku, "TEST-001")

    def test_cashier_cannot_create_product(self):
        company = Company.objects.create(name="Test Company")
        category = Category.objects.get(company=company, key="qurilish")
        cashier = User.objects.create_user(phone_number="998955556666", password="pass123!", company=company)
        client = APIClient()
        client.force_authenticate(user=cashier)
        response = client.post(reverse('product-list'), {
            "sku": "X-001", "name": "X", "category": category.key, "unit": "dona",
            "price": 100, "qty": 1, "min": 1, "date_received": "2026-09-20"
        }, format='json')
        self.assertEqual(response.status_code, 403)
