from io import StringIO
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from apps.models import Product, Company, User, Category, Markaz, SubscriptionStatus, Sale, SaleItem, Settings
from datetime import timedelta
from django.utils import timezone


class PersonalCashierTenancyTestCase(TestCase):
    def setUp(self):
        self.superadmin = User.objects.create_superuser(
            phone_number="998940656009", password="AdminPass123!", role="superadmin"
        )
        self.company = Company.objects.create(name="Main Company")
        self.superadmin.company = self.company
        self.superadmin.save()

        self.other_superadmin = User.objects.create_superuser(
            phone_number="998900000000", password="AdminPass123!", role="superadmin"
        )
        self.other_company = Company.objects.create(name="Other Company")
        self.other_superadmin.company = self.other_company
        self.other_superadmin.save()

    def test_two_markazless_cashiers_isolation(self):
        # Create two markazless cashiers under superadmin
        client = APIClient()
        client.force_authenticate(user=self.superadmin)

        res_a = client.post(reverse('user-list'), {
            "phone_number": "998991111111",
            "first_name": "Cashier A",
            "password": "CashierPass123!"
        }, format='json')
        self.assertEqual(res_a.status_code, 201)
        data_a = res_a.json()
        cashier_a_id = data_a['id']
        cashier_a = User.objects.get(id=cashier_a_id)

        res_b = client.post(reverse('user-list'), {
            "phone_number": "998992222222",
            "first_name": "Cashier B",
            "password": "CashierPass123!"
        }, format='json')
        self.assertEqual(res_b.status_code, 201)
        data_b = res_b.json()
        cashier_b_id = data_b['id']
        cashier_b = User.objects.get(id=cashier_b_id)

        # Verify personal company & default categories & managed_by
        self.assertIsNotNone(cashier_a.company)
        self.assertNotEqual(cashier_a.company, cashier_b.company)
        self.assertEqual(cashier_a.managed_by, self.superadmin)
        self.assertEqual(cashier_b.managed_by, self.superadmin)

        cat_count_a = Category.objects.filter(company=cashier_a.company).count()
        self.assertGreaterEqual(cat_count_a, 4)

        # Cashier A adds custom category & product A
        client_a = APIClient()
        client_a.force_authenticate(user=cashier_a)
        res_cat_a = client_a.post(reverse('category-list'), {
            "key": "mebel", "label": "Mebel"
        }, format='json')
        self.assertEqual(res_cat_a.status_code, 201)

        res_prod_a = client_a.post(reverse('product-list'), {
            "sku": "SKU-A", "name": "Product A", "category": "mebel", "unit": "dona",
            "price": 1000, "qty": 10, "date_received": "2026-10-08"
        }, format='json')
        self.assertEqual(res_prod_a.status_code, 201)
        prod_a_id = res_prod_a.json()['id']

        # Cashier B checks product list -> empty (200, bo'sh)
        client_b = APIClient()
        client_b.force_authenticate(user=cashier_b)
        res_list_b = client_b.get(reverse('product-list'))
        self.assertEqual(res_list_b.status_code, 200)
        self.assertEqual(len(res_list_b.json()['results']), 0)

        # Cashier B detail request for Product A -> 404
        res_detail_b = client_b.get(f"/api/v1/products/{prod_a_id}/")
        self.assertEqual(res_detail_b.status_code, 404)

        # Categories for B do not contain "mebel"
        res_cats_b = client_b.get(reverse('category-list'))
        self.assertEqual(res_cats_b.status_code, 200)
        self.assertFalse(any(c['key'] == 'mebel' for c in res_cats_b.json()))

    def test_markaz_bound_cashiers_share_products(self):
        markaz = Markaz.objects.create(name="Markaz 1", company=self.company)
        client = APIClient()
        client.force_authenticate(user=self.superadmin)

        res_a = client.post(reverse('user-list'), {
            "phone_number": "998993333333",
            "first_name": "Markaz Cashier A",
            "password": "CashierPass123!",
            "markaz": markaz.id
        }, format='json')
        self.assertEqual(res_a.status_code, 201)
        cashier_a = User.objects.get(id=res_a.json()['id'])

        res_b = client.post(reverse('user-list'), {
            "phone_number": "998994444444",
            "first_name": "Markaz Cashier B",
            "password": "CashierPass123!",
            "markaz": markaz.id
        }, format='json')
        self.assertEqual(res_b.status_code, 201)
        cashier_b = User.objects.get(id=res_b.json()['id'])

        # Both share self.company
        self.assertEqual(cashier_a.company, self.company)
        self.assertEqual(cashier_b.company, self.company)

        # Cashier A adds product
        client_a = APIClient()
        client_a.force_authenticate(user=cashier_a)
        res_prod = client_a.post(reverse('product-list'), {
            "sku": "SKU-SHARED", "name": "Shared Prod", "category": "qurilish", "unit": "dona",
            "price": 2000, "qty": 5, "date_received": "2026-10-08"
        }, format='json')
        self.assertEqual(res_prod.status_code, 201)

        # Cashier B sees product
        client_b = APIClient()
        client_b.force_authenticate(user=cashier_b)
        res_list_b = client_b.get(reverse('product-list'))
        self.assertEqual(res_list_b.status_code, 200)
        self.assertEqual(len(res_list_b.json()['results']), 1)
        self.assertEqual(res_list_b.json()['results'][0]['sku'], "SKU-SHARED")

    def test_markaz_belonging_to_other_company_returns_400(self):
        other_markaz = Markaz.objects.create(name="Other Markaz", company=self.other_company)
        client = APIClient()
        client.force_authenticate(user=self.superadmin)

        res = client.post(reverse('user-list'), {
            "phone_number": "998995555555",
            "first_name": "Bad Markaz Cashier",
            "password": "CashierPass123!",
            "markaz": other_markaz.id
        }, format='json')
        self.assertEqual(res.status_code, 400)
        self.assertIn("markaz", res.json())

    def test_markaz_transition_returns_400(self):
        # Create markazless cashier
        client = APIClient()
        client.force_authenticate(user=self.superadmin)
        res = client.post(reverse('user-list'), {
            "phone_number": "998996666666",
            "first_name": "NoMarkaz",
            "password": "CashierPass123!"
        }, format='json')
        self.assertEqual(res.status_code, 201)
        cashier_id = res.json()['id']

        markaz = Markaz.objects.create(name="Markaz 1", company=self.company)

        # Try to update markazless cashier to have a markaz -> 400
        res_update = client.patch(f"/api/v1/users/{cashier_id}/", {
            "markaz": markaz.id
        }, format='json')
        self.assertEqual(res_update.status_code, 400)
        self.assertIn("markaz", res_update.json())

    def test_superadmin_queryset_visibility(self):
        # Superadmin A creates cashier A
        client = APIClient()
        client.force_authenticate(user=self.superadmin)
        res = client.post(reverse('user-list'), {
            "phone_number": "998997777777",
            "first_name": "Super A Cashier",
            "password": "CashierPass123!"
        }, format='json')
        self.assertEqual(res.status_code, 201)
        cashier_id = res.json()['id']

        # Superadmin B tries to view or update cashier A -> 404
        client_other = APIClient()
        client_other.force_authenticate(user=self.other_superadmin)
        res_list = client_other.get(reverse('user-list'))
        self.assertEqual(res_list.status_code, 200)
        self.assertEqual(len(res_list.json()['results']), 0)

        res_detail = client_other.get(f"/api/v1/users/{cashier_id}/")
        self.assertEqual(res_detail.status_code, 404)

    def test_renew_prevents_free_trial_expiry_block(self):
        client = APIClient()
        client.force_authenticate(user=self.superadmin)
        res = client.post(reverse('user-list'), {
            "phone_number": "998998888888",
            "first_name": "Renewed",
            "password": "CashierPass123!"
        }, format='json')
        self.assertEqual(res.status_code, 201)
        cashier_id = res.json()['id']
        cashier = User.objects.get(id=cashier_id)

        # Renew subscription
        res_renew = client.post(f"/api/v1/users/{cashier.id}/renew-subscription/", {"months": 1}, format='json')
        self.assertEqual(res_renew.status_code, 200)

        # Simulate time passing past free trial days
        cashier.refresh_from_db()
        cashier.subscription_expires_at = timezone.localdate() + timedelta(days=20)
        cashier.save()

        # Login should succeed (200)
        login_res = client.post('/api/token/', {
            "phone_number": "998998888888",
            "password": "CashierPass123!"
        }, format='json')
        self.assertEqual(login_res.status_code, 200)

    def test_two_personal_cashiers_sale_id_uniqueness(self):
        client = APIClient()
        client.force_authenticate(user=self.superadmin)

        # Cashier A
        res_a = client.post(reverse('user-list'), {
            "phone_number": "998991112223", "first_name": "Cashier A", "password": "Pass123!"
        }, format='json')
        self.assertEqual(res_a.status_code, 201)
        cashier_a = User.objects.get(id=res_a.json()['id'])

        # Cashier B
        res_b = client.post(reverse('user-list'), {
            "phone_number": "998992223334", "first_name": "Cashier B", "password": "Pass123!"
        }, format='json')
        self.assertEqual(res_b.status_code, 201)
        cashier_b = User.objects.get(id=res_b.json()['id'])

        # Cashier A creates product & sale
        client_a = APIClient()
        client_a.force_authenticate(user=cashier_a)
        client_a.post(reverse('product-list'), {
            "sku": "A-1", "name": "Prod A", "category": "qurilish", "unit": "dona",
            "price": 100, "qty": 10, "date_received": "2026-10-08"
        }, format='json')
        prod_a = cashier_a.company.products.first()

        sale_a = client_a.post(reverse('sale-list'), {
            "items": [{"product_id": str(prod_a.id), "qty": 1}],
            "cashier": "Cashier A"
        }, format='json')
        self.assertEqual(sale_a.status_code, 201)

        # Cashier B creates product & sale on same day
        client_b = APIClient()
        client_b.force_authenticate(user=cashier_b)
        client_b.post(reverse('product-list'), {
            "sku": "B-1", "name": "Prod B", "category": "qurilish", "unit": "dona",
            "price": 200, "qty": 10, "date_received": "2026-10-08"
        }, format='json')
        prod_b = cashier_b.company.products.first()

        sale_b = client_b.post(reverse('sale-list'), {
            "items": [{"product_id": str(prod_b.id), "qty": 1}],
            "cashier": "Cashier B"
        }, format='json')
        self.assertEqual(sale_b.status_code, 201)

        self.assertNotEqual(sale_a.json()['id'], sale_b.json()['id'])

    def test_split_personal_data_apply_moves_products_and_sales(self):
        comp1 = Company.objects.create(name="Company 1")
        superadmin1 = User.objects.create_superuser(
            phone_number="998901112299", password="Pass!", company=comp1
        )
        cashier_aaaaa = User.objects.create_user(
            phone_number="998997777777", first_name="AAAAA", role="cashier", company=comp1, password="Pass!"
        )
        cashier_add = User.objects.create_user(
            phone_number="998999888888", first_name="add", role="cashier", company=comp1, password="Pass!"
        )
        cashier_other = User.objects.create_user(
            phone_number="998995554444", first_name="Other", role="cashier", company=comp1, password="Pass!"
        )
        cat_qurilish = Category.objects.get(company=comp1, key="qurilish")
        cat_mebel = Category.objects.create(company=comp1, key="mebel", label="Mebel")
        comp1_cat_count_before = Category.objects.filter(company=comp1).count()

        prod_k1 = Product.objects.create(
            company=comp1, category=cat_qurilish, sku="k1", name="Kabel", price=1000, qty=10, date_received="2026-10-01"
        )
        prod_o1 = Product.objects.create(
            company=comp1, category=cat_mebel, sku="o1", name="Oyna", price=2000, qty=5, date_received="2026-10-01"
        )
        sale1 = Sale.objects.create(
            cashier="AAAAA", company=comp1, total=3000
        )
        SaleItem.objects.create(
            sale=sale1, product=prod_k1, product_id_str=str(prod_k1.id),
            name=prod_k1.name, sku=prod_k1.sku, category="qurilish", date_received=prod_k1.date_received,
            unit="dona", price=prod_k1.price, qty=1, subtotal=1000
        )
        SaleItem.objects.create(
            sale=sale1, product=prod_o1, product_id_str=str(prod_o1.id),
            name=prod_o1.name, sku=prod_o1.sku, category="mebel", date_received=prod_o1.date_received,
            unit="dona", price=prod_o1.price, qty=1, subtotal=2000
        )

        out = StringIO()
        call_command(
            'split_personal_data',
            '--cashier-ids', f"{cashier_aaaaa.id},{cashier_add.id}",
            '--assign', 'k1=998997777777',
            '--assign', 'o1=998997777777',
            '--apply',
            stdout=out
        )

        cashier_aaaaa.refresh_from_db()
        cashier_add.refresh_from_db()
        cashier_other.refresh_from_db()
        prod_k1.refresh_from_db()
        prod_o1.refresh_from_db()
        sale1.refresh_from_db()

        comp_aaaaa = cashier_aaaaa.company
        comp_add = cashier_add.company

        # AAAAA company has products and sales and categories
        self.assertNotEqual(comp_aaaaa, comp1)
        self.assertEqual(prod_k1.company, comp_aaaaa)
        self.assertEqual(prod_o1.company, comp_aaaaa)
        self.assertEqual(sale1.company, comp_aaaaa)
        self.assertEqual(prod_k1.category.company, comp_aaaaa)
        self.assertEqual(prod_o1.category.company, comp_aaaaa)
        self.assertTrue(Category.objects.filter(company=comp_aaaaa, key="mebel").exists())
        self.assertEqual(Product.objects.filter(company=comp_aaaaa).count(), 2)
        self.assertEqual(Sale.objects.filter(company=comp_aaaaa).count(), 1)
        self.assertEqual(list(sale1.items.values_list('product_id', flat=True)), [prod_k1.id, prod_o1.id])

        # Company 1 categories unchanged
        self.assertEqual(Category.objects.filter(company=comp1).count(), comp1_cat_count_before)

        # Other cashier remained in comp1
        self.assertEqual(cashier_other.company, comp1)

        # "add" company is empty (no products, no sales)
        self.assertNotEqual(comp_add, comp1)
        self.assertNotEqual(comp_add, comp_aaaaa)
        self.assertEqual(Product.objects.filter(company=comp_add).count(), 0)
        self.assertEqual(Sale.objects.filter(company=comp_add).count(), 0)

    def test_personal_cashier_store_name_settings(self):
        # (c) existing company settings unchanged
        old_settings = Settings.objects.create(company=self.company, store_name="Old Main Store")

        client = APIClient()
        client.force_authenticate(user=self.superadmin)

        # (a) & (b) create two markazless cashiers with names
        res1 = client.post(reverse('user-list'), {
            "phone_number": "998991111222", "first_name": "Vali", "last_name": "Aliyev", "password": "Pass123!"
        }, format='json')
        self.assertEqual(res1.status_code, 201)
        cashier1 = User.objects.get(id=res1.json()['id'])

        res2 = client.post(reverse('user-list'), {
            "phone_number": "998993333444", "first_name": "Botir", "password": "Pass123!"
        }, format='json')
        self.assertEqual(res2.status_code, 201)
        cashier2 = User.objects.get(id=res2.json()['id'])

        # Check store_names
        s1 = Settings.objects.get(company=cashier1.company)
        s2 = Settings.objects.get(company=cashier2.company)
        self.assertEqual(s1.store_name, "Vali Aliyev do'koni")
        self.assertEqual(s2.store_name, "Botir do'koni")

        # Existing company settings unchanged
        old_settings.refresh_from_db()
        self.assertEqual(old_settings.store_name, "Old Main Store")

        # (d) cashier gets company store name via GET /api/v1/settings/
        client_c1 = APIClient()
        client_c1.force_authenticate(user=cashier1)
        res_settings = client_c1.get('/api/v1/settings/')
        self.assertEqual(res_settings.status_code, 200)
        self.assertEqual(res_settings.json()['storeName'], "Vali Aliyev do'koni")
