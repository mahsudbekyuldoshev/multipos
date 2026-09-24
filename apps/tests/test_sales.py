from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from apps.models import Product, User, Company

class SaleTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.company = Company.objects.create(name="Test Company")
        self.user = User.objects.create_user(
            phone_number="998900000000", password="TestPass123!", company=self.company
        )
        self.client.force_authenticate(user=self.user)
        self.product = Product.objects.create(
            company=self.company, sku="TEST-001", name="Test Product",
            price=1000, qty=10, date_received="2026-09-20"
        )

    def test_checkout(self):
        data = {
            "items": [{"product_id": str(self.product.id), "qty": "2.0"}],
            "cashier": "Test Cashier"
        }
        response = self.client.post(reverse('sale-list'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_checkout_partial_failure_does_not_commit(self):
        self.product.qty = 10
        self.product.save()
        response = self.client.post(reverse('sale-list'), {
            "items": [
                {"product_id": self.product.id, "qty": 2},
                {"product_id": 999999, "qty": 1}
            ]
        }, format='json')
        self.assertEqual(response.status_code, 404)
        self.product.refresh_from_db()
        self.assertEqual(self.product.qty, 10)  # o'zgarmagan bo'lishi kerak
