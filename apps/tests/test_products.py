from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from apps.models import Product, Company, User, Category, SubscriptionStatus
from datetime import timedelta
from django.utils import timezone

class ProductTestCase(TestCase):
    def test_product_creation(self):
        company = Company.objects.create(name="Test Company")
        category = Category.objects.get(company=company, key="qurilish")
        product = Product.objects.create(
            company=company, category=category, sku="TEST-001", name="Test Product",
            price=1000, date_received="2026-09-20"
        )
        self.assertEqual(product.sku, "TEST-001")

    def test_cashier_can_create_product(self):
        company = Company.objects.create(name="Test Company")
        category = Category.objects.get(company=company, key="qurilish")
        cashier = User.objects.create_user(
            phone_number="998955556666", password="pass123!", company=company, role="cashier",
            subscription_status=SubscriptionStatus.ACTIVE,
            subscription_expires_at=timezone.localdate() + timedelta(days=30)
        )
        client = APIClient()
        client.force_authenticate(user=cashier)
        response = client.post(reverse('product-list'), {
            "sku": "X-001", "name": "X", "category": category.key, "unit": "dona",
            "price": 100, "qty": 1, "min": 1, "date_received": "2026-09-20"
        }, format='json')
        self.assertEqual(response.status_code, 201)

    def test_company_cashier_can_create_category_and_product(self):
        company = Company.objects.create(name="Comp A")
        cashier = User.objects.create_user(
            phone_number="998901112233", password="pass", company=company, role="cashier",
            subscription_status=SubscriptionStatus.ACTIVE,
            subscription_expires_at=timezone.localdate() + timedelta(days=30)
        )
        client = APIClient()
        client.force_authenticate(user=cashier)
        res_cat = client.post(reverse('category-list'), {"key": "test-cat", "label": "Test Cat"}, format='json')
        self.assertEqual(res_cat.status_code, 201)
        res_prod = client.post(reverse('product-list'), {
            "sku": "P-1", "name": "Prod", "category": "test-cat", "unit": "dona",
            "price": 500, "qty": 10, "date_received": "2026-10-03"
        }, format='json')
        self.assertEqual(res_prod.status_code, 201)

    def test_company_less_cashier_forbidden(self):
        cashier = User.objects.create_user(phone_number="998902223344", password="pass", company=None, role="cashier")
        client = APIClient()
        client.force_authenticate(user=cashier)
        res_cat = client.post(reverse('category-list'), {"key": "bad-cat", "label": "Bad"}, format='json')
        self.assertEqual(res_cat.status_code, 403)
        res_prod = client.post(reverse('product-list'), {
            "sku": "P-2", "name": "Prod", "category": "qurilish", "unit": "dona",
            "price": 500, "qty": 10, "date_received": "2026-10-03"
        }, format='json')
        self.assertEqual(res_prod.status_code, 403)

    def test_cross_tenant_isolation(self):
        comp_a = Company.objects.create(name="Comp A")
        comp_b = Company.objects.create(name="Comp B")
        cat_b = Category.objects.create(company=comp_b, key="cat-b", label="Cat B")
        prod_b = Product.objects.create(company=comp_b, category=cat_b, sku="PROD-B", name="Prod B", price=100, date_received="2026-10-03")

        cashier_a = User.objects.create_user(
            phone_number="998903334455", password="pass", company=comp_a, role="cashier",
            subscription_status=SubscriptionStatus.ACTIVE,
            subscription_expires_at=timezone.localdate() + timedelta(days=30)
        )
        client = APIClient()
        client.force_authenticate(user=cashier_a)

        res_cats = client.get(reverse('category-list'))
        self.assertFalse(any(c['key'] == 'cat-b' for c in res_cats.json()))

        res_prod_detail = client.get(f"/api/v1/products/{prod_b.id}/")
        self.assertEqual(res_prod_detail.status_code, 404)

    def test_duplicate_category_key_returns_400(self):
        company = Company.objects.create(name="Comp A")
        cashier = User.objects.create_user(
            phone_number="998904445566", password="pass", company=company, role="cashier",
            subscription_status=SubscriptionStatus.ACTIVE,
            subscription_expires_at=timezone.localdate() + timedelta(days=30)
        )
        Category.objects.create(company=company, key="dup-key", label="Existing")
        client = APIClient()
        client.force_authenticate(user=cashier)

        res = client.post(reverse('category-list'), {"key": "dup-key", "label": "Duplicate"}, format='json')
        self.assertEqual(res.status_code, 400)
        self.assertIn("key", res.json())

    def test_company_less_superadmin_cannot_create_cashier(self):
        superadmin = User.objects.create_superuser(phone_number="998905556677", password="pass", company=None, role="superadmin")
        client = APIClient()
        client.force_authenticate(user=superadmin)

        res = client.post(reverse('user-list'), {
            "phone_number": "998906667788", "password": "CashierPass123!"
        }, format='json')
        self.assertEqual(res.status_code, 400)
        self.assertIn("detail", res.json())
