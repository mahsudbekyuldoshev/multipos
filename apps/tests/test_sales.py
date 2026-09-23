from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from apps.models import Product, User

class SaleTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="testuser", password="testpass123")
        self.client.force_authenticate(user=self.user)
        self.product = Product.objects.create(
            sku="TEST-001",
            name="Test Product",
            price=1000,
            qty=10,
            date_received="2026-09-20"
        )

    def test_checkout(self):
        data = {
            "items": [{"product_id": str(self.product.id), "qty": "2.0"}],
            "cashier": "Test Cashier"
        }
        response = self.client.post(reverse('sale-list'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
