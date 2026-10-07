from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from apps.models import Company, User, SubscriptionStatus, SubscriptionAuditLog, SubscriptionPayment, FreeTrialUsage, UserPlan, Category, Product, Markaz
from datetime import timedelta, date
from dateutil.relativedelta import relativedelta
from django.utils import timezone
from django.conf import settings


class SubscriptionTestCase(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Test Company", subscription_status=SubscriptionStatus.ACTIVE)
        self.admin = User.objects.create_superuser(
            phone_number="998901111111", password="AdminPass123!",
            first_name="Admin", last_name="User", company=self.company
        )
        self.company_b = Company.objects.create(name="Company B", subscription_status=SubscriptionStatus.ACTIVE)
        self.admin_b = User.objects.create_superuser(
            phone_number="998902222222", password="AdminPass123!",
            first_name="Admin", last_name="B", company=self.company_b
        )
        self.client = APIClient()

    def test_new_cashier_free_trial(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(reverse('user-list'), {
            "phone_number": "998903333333",
            "first_name": "Cashier",
            "last_name": "Free",
            "password": "CashierPass123!"
        }, format='json')
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data['plan'], 'free')
        self.assertEqual(data['daysLeft'], settings.FREE_TRIAL_DAYS)
        self.assertEqual(data['status'], 'active')

    def test_recreate_cashier_with_phone_normalization(self):
        raw_phone = "+998 90 123 45 67"
        norm_phone = "998901234567"
        
        cashier = User.objects.create_user(
            phone_number=norm_phone, password="Pass123!", role="cashier", company=self.company
        )
        FreeTrialUsage.objects.get_or_create(phone_number=norm_phone)
        cashier.delete()

        self.client.force_authenticate(user=self.admin)
        # Free plan with used phone -> 400
        response_free = self.client.post(reverse('user-list'), {
            "phone_number": raw_phone,
            "first_name": "Cashier",
            "last_name": "RecreatedFree",
            "password": "CashierPass123!",
            "plan": "free"
        }, format='json')
        self.assertEqual(response_free.status_code, 400)

        # Standard plan with used phone -> 201, active
        response_std = self.client.post(reverse('user-list'), {
            "phone_number": raw_phone,
            "first_name": "Cashier",
            "last_name": "RecreatedStd",
            "password": "CashierPass123!",
            "plan": "standard",
            "subscription_months": 1
        }, format='json')
        self.assertEqual(response_std.status_code, 201)
        data = response_std.json()
        self.assertEqual(data['plan'], 'standard')
        self.assertEqual(data['status'], 'active')

    def test_standard_plan_creation_and_validations(self):
        self.client.force_authenticate(user=self.admin)
        # standard without months -> 400
        res_no_months = self.client.post(reverse('user-list'), {
            "phone_number": "998901112233",
            "first_name": "C1",
            "password": "Pass123!",
            "plan": "standard"
        }, format='json')
        self.assertEqual(res_no_months.status_code, 400)

        # standard with invalid months (5) -> 400
        res_bad_months = self.client.post(reverse('user-list'), {
            "phone_number": "998901112233",
            "first_name": "C1",
            "password": "Pass123!",
            "plan": "standard",
            "subscription_months": 5
        }, format='json')
        self.assertEqual(res_bad_months.status_code, 400)

        # standard with 3 months -> 201
        res_ok = self.client.post(reverse('user-list'), {
            "phone_number": "998901112233",
            "first_name": "C1",
            "password": "Pass123!",
            "plan": "standard",
            "subscription_months": 3
        }, format='json')
        self.assertEqual(res_ok.status_code, 201)
        data = res_ok.json()
        self.assertEqual(data['plan'], 'standard')
        self.assertEqual(data['status'], 'active')
        
        user = User.objects.get(id=data['id'])
        payment = SubscriptionPayment.objects.filter(user=user).last()
        self.assertIsNotNone(payment)
        self.assertEqual(payment.amount, 3 * settings.SUBSCRIPTION_PRICE_PER_MONTH)
        self.assertTrue(FreeTrialUsage.objects.filter(phone_number="998901112233").exists())

    def test_9_digit_phone_normalization(self):
        raw_phone = "901234567"
        norm_phone = "998901234567"
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(reverse('user-list'), {
            "phone_number": raw_phone,
            "first_name": "Short",
            "last_name": "Phone",
            "password": "CashierPass123!"
        }, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertTrue(FreeTrialUsage.objects.filter(phone_number=norm_phone).exists())
        user = User.objects.get(id=response.json()['id'])
        self.assertEqual(user.phone_number, norm_phone)

    def test_free_cashier_renew_adds_remaining_days(self):
        today = timezone.localdate()
        cashier = User.objects.create_user(
            phone_number="998905555555", password="Pass123!", role="cashier", company=self.company,
            plan=UserPlan.FREE, subscription_status=SubscriptionStatus.ACTIVE,
            subscription_expires_at=today + timedelta(days=5)
        )
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(f"/api/v1/users/{cashier.id}/renew-subscription/", {"months": 1}, format='json')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['plan'], 'standard')
        expected_date = (today + timedelta(days=5)) + relativedelta(months=1)
        self.assertEqual(data['subscriptionEndDate'], expected_date.isoformat())
        
        payment = SubscriptionPayment.objects.filter(user=cashier).last()
        self.assertIsNotNone(payment)
        self.assertEqual(payment.amount, settings.SUBSCRIPTION_PRICE_PER_MONTH)

    def test_free_cashier_set_date_and_shorten_forbidden(self):
        cashier = User.objects.create_user(
            phone_number="998906666666", password="Pass123!", role="cashier", company=self.company,
            plan=UserPlan.FREE, subscription_status=SubscriptionStatus.ACTIVE,
            subscription_expires_at=timezone.localdate() + timedelta(days=5)
        )
        self.client.force_authenticate(user=self.admin)
        
        resp1 = self.client.post(f"/api/v1/users/{cashier.id}/subscription/set-date/", {"end_date": (timezone.localdate() + timedelta(days=30)).isoformat()}, format='json')
        self.assertEqual(resp1.status_code, 400)

        resp2 = self.client.post(f"/api/v1/users/{cashier.id}/subscription/shorten/", {"months": 1}, format='json')
        self.assertEqual(resp2.status_code, 400)

    def test_activate_expired_cashier_forbidden(self):
        today = timezone.localdate()
        cashier_expired = User.objects.create_user(
            phone_number="99890666677", password="Pass123!", role="cashier", company=self.company,
            plan=UserPlan.FREE, subscription_status=SubscriptionStatus.INACTIVE,
            subscription_expires_at=today - timedelta(days=5)
        )
        self.client.force_authenticate(user=self.admin)
        res1 = self.client.patch(f"/api/v1/users/{cashier_expired.id}/subscription/", {"status": "active"}, format='json')
        self.assertEqual(res1.status_code, 400)
        cashier_expired.refresh_from_db()
        self.assertEqual(cashier_expired.subscription_status, SubscriptionStatus.INACTIVE)

        cashier_none = User.objects.create_user(
            phone_number="99890666678", password="Pass123!", role="cashier", company=self.company,
            plan=UserPlan.STANDARD, subscription_status=SubscriptionStatus.INACTIVE,
            subscription_expires_at=None
        )
        res2 = self.client.patch(f"/api/v1/users/{cashier_none.id}/subscription/", {"status": "active"}, format='json')
        self.assertEqual(res2.status_code, 400)
        cashier_none.refresh_from_db()
        self.assertEqual(cashier_none.subscription_status, SubscriptionStatus.INACTIVE)

        cashier_future = User.objects.create_user(
            phone_number="99890666679", password="Pass123!", role="cashier", company=self.company,
            plan=UserPlan.STANDARD, subscription_status=SubscriptionStatus.INACTIVE,
            subscription_expires_at=today + timedelta(days=10)
        )
        res3 = self.client.patch(f"/api/v1/users/{cashier_future.id}/subscription/", {"status": "active"}, format='json')
        self.assertEqual(res3.status_code, 200)
        cashier_future.refresh_from_db()
        self.assertEqual(cashier_future.subscription_status, SubscriptionStatus.ACTIVE)

    def test_superadmin_works_without_expiry(self):
        self.assertIsNone(self.admin.subscription_expires_at)
        self.assertTrue(self.admin.is_subscription_valid)
        self.assertEqual(self.admin.computed_status, 'active')
        self.client.force_authenticate(user=self.admin)
        res = self.client.get('/api/v1/tariffs/')
        self.assertEqual(res.status_code, 200)

    def test_expired_cashier_login_and_sale_forbidden(self):
        today = timezone.localdate()
        cashier = User.objects.create_user(
            phone_number="998907777777", password="CashierPass123!", role="cashier", company=self.company,
            plan=UserPlan.FREE, subscription_status=SubscriptionStatus.ACTIVE,
            subscription_expires_at=today - timedelta(days=1)
        )
        login_resp = self.client.post('/api/token/', {
            "phone_number": "998907777777",
            "password": "CashierPass123!"
        }, format='json')
        self.assertEqual(login_resp.status_code, 403)

        cashier.subscription_expires_at = today + timedelta(days=10)
        cashier.subscription_status = SubscriptionStatus.INACTIVE
        cashier.save()
        login_resp2 = self.client.post('/api/token/', {
            "phone_number": "998907777777",
            "password": "CashierPass123!"
        }, format='json')
        self.assertEqual(login_resp2.status_code, 403)

        cashier.subscription_status = SubscriptionStatus.ACTIVE
        cashier.subscription_expires_at = today - timedelta(days=1)
        cashier.save()
        self.client.force_authenticate(user=cashier)
        category = Category.objects.create(company=self.company, key="test", label="Test")
        product = Product.objects.create(company=self.company, category=category, sku="S-1", name="Prod", price=100, qty=10, date_received="2026-09-20")
        
        prod_resp = self.client.get(reverse('product-list'))
        self.assertEqual(prod_resp.status_code, 403)

        sale_resp = self.client.post(reverse('sale-list'), {
            "items": [{"product_id": str(product.id), "qty": 1}]
        }, format='json')
        self.assertEqual(sale_resp.status_code, 403)

    def test_subscription_endpoint_rejects_dates(self):
        today = timezone.localdate()
        cashier = User.objects.create_user(
            phone_number="998908888888", password="Pass123!", role="cashier", company=self.company,
            plan=UserPlan.STANDARD, subscription_status=SubscriptionStatus.ACTIVE,
            subscription_expires_at=today + timedelta(days=30)
        )
        self.client.force_authenticate(user=self.admin)
        old_expiry = cashier.subscription_expires_at

        res1 = self.client.patch(f"/api/v1/users/{cashier.id}/subscription/", {"status": "active", "months": 1}, format='json')
        self.assertEqual(res1.status_code, 400)
        self.assertIn("detail", res1.json())

        res2 = self.client.patch(f"/api/v1/users/{cashier.id}/subscription/", {"status": "active", "expires_at": (today + timedelta(days=60)).isoformat()}, format='json')
        self.assertEqual(res2.status_code, 400)

        cashier.refresh_from_db()
        self.assertEqual(cashier.subscription_expires_at, old_expiry)

    def test_admin_patch_ignores_subscription(self):
        today = timezone.localdate()
        cashier = User.objects.create_user(
            phone_number="998909999999", password="Pass123!", role="cashier", company=self.company,
            plan=UserPlan.STANDARD, subscription_status=SubscriptionStatus.ACTIVE,
            subscription_expires_at=today + timedelta(days=30)
        )
        self.client.force_authenticate(user=self.admin)
        old_expiry = cashier.subscription_expires_at

        res = self.client.patch(f"/api/v1/users/{cashier.id}/", {
            "first_name": "UpdatedName",
            "subscription_expires_at": (today + timedelta(days=90)).isoformat()
        }, format='json')
        self.assertEqual(res.status_code, 200)
        cashier.refresh_from_db()
        self.assertEqual(cashier.first_name, "UpdatedName")
        self.assertEqual(cashier.subscription_expires_at, old_expiry)

    def test_tariffs_endpoint(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get('/api/v1/tariffs/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]['code'], 'free')
        self.assertEqual(data[0]['days'], settings.FREE_TRIAL_DAYS)
        self.assertEqual(data[1]['code'], 'standard')
        self.assertEqual(data[1]['pricePerMonth'], settings.SUBSCRIPTION_PRICE_PER_MONTH)

    def test_set_exact_date_decrease_and_increase(self):
        today = timezone.localdate()
        cashier = User.objects.create_user(
            phone_number="998900000010", password="Pass123!", role="cashier", company=self.company,
            plan=UserPlan.STANDARD, subscription_status=SubscriptionStatus.ACTIVE,
            subscription_expires_at=today + timedelta(days=122)
        )
        self.client.force_authenticate(user=self.admin)

        target_30 = today + timedelta(days=30)
        res1 = self.client.post(f"/api/v1/users/{cashier.id}/subscription/set-date/", {"end_date": target_30.isoformat()}, format='json')
        self.assertEqual(res1.status_code, 200)
        self.assertEqual(res1.json()['daysLeft'], 30)

        log = SubscriptionAuditLog.objects.filter(user=cashier, action='set-date').last()
        self.assertEqual(log.admin, self.admin)
        self.assertEqual(log.old_date, today + timedelta(days=122))
        self.assertEqual(log.new_date, target_30)

        target_200 = today + timedelta(days=200)
        res2 = self.client.post(f"/api/v1/users/{cashier.id}/subscription/set-date/", {"end_date": target_200.isoformat()}, format='json')
        self.assertEqual(res2.status_code, 200)
        self.assertEqual(res2.json()['daysLeft'], 200)

    def test_shorten_logic_and_validation(self):
        today = timezone.localdate()
        initial_end = today + relativedelta(months=3)
        cashier = User.objects.create_user(
            phone_number="998900000011", password="Pass123!", role="cashier", company=self.company,
            plan=UserPlan.STANDARD, subscription_status=SubscriptionStatus.ACTIVE,
            subscription_expires_at=initial_end
        )
        self.client.force_authenticate(user=self.admin)

        log_count_before = SubscriptionAuditLog.objects.count()
        for m in [-5, 0, 12, "abc"]:
            res = self.client.post(f"/api/v1/users/{cashier.id}/subscription/shorten/", {"months": m}, format='json')
            self.assertEqual(res.status_code, 400)
        self.assertEqual(SubscriptionAuditLog.objects.count(), log_count_before)

        res = self.client.post(f"/api/v1/users/{cashier.id}/subscription/shorten/", {"months": 1}, format='json')
        self.assertEqual(res.status_code, 200)
        cashier.refresh_from_db()
        expected_date = initial_end - relativedelta(months=1)
        self.assertEqual(cashier.subscription_expires_at, expected_date)

        cashier.subscription_expires_at = today + timedelta(days=15)
        cashier.save()
        res = self.client.post(f"/api/v1/users/{cashier.id}/subscription/shorten/", {"months": 3}, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json().get('clamped'))
        self.assertEqual(res.json()['daysLeft'], 0)

        cashier.subscription_expires_at = today - timedelta(days=5)
        cashier.save()
        log_count_before_exp = SubscriptionAuditLog.objects.count()
        res = self.client.post(f"/api/v1/users/{cashier.id}/subscription/shorten/", {"months": 1}, format='json')
        self.assertEqual(res.status_code, 400)
        self.assertEqual(SubscriptionAuditLog.objects.count(), log_count_before_exp)

        cashier.subscription_expires_at = None
        cashier.save()
        res = self.client.post(f"/api/v1/users/{cashier.id}/subscription/shorten/", {"months": 1}, format='json')
        self.assertEqual(res.status_code, 400)

    def test_set_date_inactive_remains_inactive(self):
        today = timezone.localdate()
        cashier = User.objects.create_user(
            phone_number="998900000012", password="Pass123!", role="cashier", company=self.company,
            plan=UserPlan.STANDARD, subscription_status=SubscriptionStatus.INACTIVE,
            subscription_expires_at=today + timedelta(days=30)
        )
        self.client.force_authenticate(user=self.admin)
        target = today + timedelta(days=60)
        res = self.client.post(f"/api/v1/users/{cashier.id}/subscription/set-date/", {"end_date": target.isoformat()}, format='json')
        self.assertEqual(res.status_code, 200)
        cashier.refresh_from_db()
        self.assertEqual(cashier.subscription_status, SubscriptionStatus.INACTIVE)

    def test_cross_tenant_access_404(self):
        cashier_b = User.objects.create_user(
            phone_number="998900000013", password="Pass123!", role="cashier", company=self.company_b,
            plan=UserPlan.STANDARD, subscription_status=SubscriptionStatus.ACTIVE,
            subscription_expires_at=timezone.localdate() + timedelta(days=30)
        )
        self.client.force_authenticate(user=self.admin)
        res1 = self.client.post(f"/api/v1/users/{cashier_b.id}/subscription/renew-subscription/", {"months": 1}, format='json')
        self.assertEqual(res1.status_code, 404)

        res2 = self.client.post(f"/api/v1/users/{cashier_b.id}/subscription/set-date/", {"end_date": (timezone.localdate() + timedelta(days=30)).isoformat()}, format='json')
        self.assertEqual(res2.status_code, 404)

        res3 = self.client.post(f"/api/v1/users/{cashier_b.id}/subscription/shorten/", {"months": 1}, format='json')
        self.assertEqual(res3.status_code, 404)

    def test_phone_uniqueness_and_update_validation(self):
        self.client.force_authenticate(user=self.admin)
        res1 = self.client.post(reverse('user-list'), {
            "phone_number": "998901234567",
            "first_name": "User1",
            "password": "Pass123!"
        }, format='json')
        self.assertEqual(res1.status_code, 201)
        user1_id = res1.json()['id']

        res2 = self.client.post(reverse('user-list'), {
            "phone_number": "+998 90 123 45 67",
            "first_name": "User2",
            "password": "Pass123!"
        }, format='json')
        self.assertEqual(res2.status_code, 400)
        self.assertIn("phoneNumber", res2.json())
        self.assertEqual(res2.json()["phoneNumber"], ["Bu telefon raqami allaqachon mavjud."])

        res3 = self.client.post(reverse('user-list'), {
            "phone_number": "998907654321",
            "first_name": "User2",
            "password": "Pass123!"
        }, format='json')
        self.assertEqual(res3.status_code, 201)
        user2_id = res3.json()['id']

        res_patch1 = self.client.patch(f"/api/v1/users/{user2_id}/", {
            "first_name": "User2Updated"
        }, format='json')
        self.assertEqual(res_patch1.status_code, 200)

        res_patch2 = self.client.patch(f"/api/v1/users/{user2_id}/", {
            "phone_number": "998901234567"
        }, format='json')
        self.assertEqual(res_patch2.status_code, 400)
        self.assertIn("phoneNumber", res_patch2.json())
        self.assertEqual(res_patch2.json()["phoneNumber"], ["Bu telefon raqami allaqachon mavjud."])

    def test_inactive_and_expired_cashier_product_list_and_sales_403(self):
        today = timezone.localdate()
        category = Category.objects.create(company=self.company, key="test_cat", label="Test Cat")
        product = Product.objects.create(company=self.company, category=category, sku="SKU-1", name="Item 1", price=100, qty=10, date_received="2026-09-20")

        # 1. Inactive cashier
        inactive_cashier = User.objects.create_user(
            phone_number="998905555551", password="CashierPass123!", role="cashier", company=self.company,
            plan=UserPlan.STANDARD, subscription_status=SubscriptionStatus.INACTIVE,
            subscription_expires_at=today + timedelta(days=30)
        )
        login_resp = self.client.post('/api/token/', {
            "phone_number": "998905555551",
            "password": "CashierPass123!"
        }, format='json')
        self.assertEqual(login_resp.status_code, 403)

        self.client.force_authenticate(user=inactive_cashier)
        prod_resp = self.client.get(reverse('product-list'))
        self.assertEqual(prod_resp.status_code, 403)

        sale_resp = self.client.post(reverse('sale-list'), {
            "items": [{"product_id": str(product.id), "qty": 1}]
        }, format='json')
        self.assertEqual(sale_resp.status_code, 403)

        # 2. Expired free trial cashier
        expired_free = User.objects.create_user(
            phone_number="998905555552", password="CashierPass123!", role="cashier", company=self.company,
            plan=UserPlan.FREE, subscription_status=SubscriptionStatus.ACTIVE,
            subscription_expires_at=today - timedelta(days=1)
        )
        login_resp2 = self.client.post('/api/token/', {
            "phone_number": "998905555552",
            "password": "CashierPass123!"
        }, format='json')
        self.assertEqual(login_resp2.status_code, 403)

        self.client.force_authenticate(user=expired_free)
        prod_resp2 = self.client.get(reverse('product-list'))
        self.assertEqual(prod_resp2.status_code, 403)

        sale_resp2 = self.client.post(reverse('sale-list'), {
            "items": [{"product_id": str(product.id), "qty": 1}]
        }, format='json')
        self.assertEqual(sale_resp2.status_code, 403)

    def test_markaz_viewset_rules(self):
        comp_less_admin = User.objects.create_superuser(
            phone_number="998909998877", password="Pass123!", company=None
        )
        self.client.force_authenticate(user=comp_less_admin)
        
        res_create = self.client.post(reverse('markaz-list'), {"name": "Bad Markaz"}, format='json')
        self.assertEqual(res_create.status_code, 400)
        res_list = self.client.get(reverse('markaz-list'))
        self.assertEqual(res_list.status_code, 200)
        data = res_list.json()
        items = data.get('results', data)
        self.assertEqual(len(items), 0)

        self.client.force_authenticate(user=self.admin)
        res_create_ok = self.client.post(reverse('markaz-list'), {"name": "Good Markaz"}, format='json')
        self.assertEqual(res_create_ok.status_code, 201)
        markaz_id = res_create_ok.json()['id']

        res_list_ok = self.client.get(reverse('markaz-list'))
        self.assertEqual(res_list_ok.status_code, 200)
        data_ok = res_list_ok.json()
        items_ok = data_ok.get('results', data_ok)
        self.assertEqual(len(items_ok), 1)

        self.client.force_authenticate(user=self.admin_b)
        res_detail_b = self.client.get(f"/api/v1/markazlar/{markaz_id}/")
        self.assertEqual(res_detail_b.status_code, 404)

    def test_attach_orphans_command(self):
        from django.core.management import call_command
        from io import StringIO

        comp_target = Company.objects.create(name="Target Comp")
        comp_other = Company.objects.create(name="Other Comp")

        orphan_cashier = User.objects.create_user(phone_number="998901234433", role="cashier", company=None, password="Pass")
        assigned_cashier = User.objects.create_user(phone_number="998901234434", role="cashier", company=comp_other, password="Pass")
        orphan_super = User.objects.create_superuser(phone_number="998901234435", company=None)
        orphan_markaz = Markaz.objects.create(name="Orphan Markaz", company=None)
        other_markaz = Markaz.objects.create(name="Other Markaz", company=comp_other)

        out = StringIO()
        call_command('attach_orphans', '--company-id', str(comp_target.id), '--all-orphan-cashiers', '--include-superadmin', '998901234435', stdout=out)
        orphan_cashier.refresh_from_db()
        assigned_cashier.refresh_from_db()
        orphan_super.refresh_from_db()
        orphan_markaz.refresh_from_db()
        other_markaz.refresh_from_db()

        self.assertIsNone(orphan_cashier.company)
        self.assertEqual(assigned_cashier.company, comp_other)
        self.assertIsNone(orphan_super.company)
        self.assertIsNone(orphan_markaz.company)
        self.assertEqual(other_markaz.company, comp_other)

        call_command('attach_orphans', '--company-id', str(comp_target.id), '--all-orphan-cashiers', '--include-superadmin', '998901234435', '--apply', stdout=out)
        orphan_cashier.refresh_from_db()
        assigned_cashier.refresh_from_db()
        orphan_super.refresh_from_db()
        orphan_markaz.refresh_from_db()
        other_markaz.refresh_from_db()

        self.assertEqual(orphan_cashier.company, comp_target)
        self.assertEqual(assigned_cashier.company, comp_other)
        self.assertEqual(orphan_super.company, comp_target)
        self.assertEqual(orphan_markaz.company, comp_target)
        self.assertEqual(other_markaz.company, comp_other)

    def test_inactive_company_blocks_superadmin_login(self):
        comp_inactive = Company.objects.create(name="Inactive Company", subscription_status=SubscriptionStatus.INACTIVE)
        superadmin_inactive = User.objects.create_superuser(
            phone_number="998906666661", password="Pass123!", company=comp_inactive
        )
        # 1. Inactive company -> login 403
        res = self.client.post('/api/token/', {
            "phone_number": "998906666661",
            "password": "Pass123!"
        }, format='json')
        self.assertEqual(res.status_code, 403)

        # 2. Active company -> login 200
        comp_inactive.subscription_status = SubscriptionStatus.ACTIVE
        comp_inactive.save()
        res2 = self.client.post('/api/token/', {
            "phone_number": "998906666661",
            "password": "Pass123!"
        }, format='json')
        self.assertEqual(res2.status_code, 200)
        self.assertIn('access', res2.json())

    def test_same_sku_different_companies(self):
        cat_a = Category.objects.create(company=self.company, key="cat-a", label="Cat A")
        cat_b = Category.objects.create(company=self.company_b, key="cat-b", label="Cat B")

        self.client.force_authenticate(user=self.admin)
        res_a = self.client.post(reverse('product-list'), {
            "sku": "SHARED-SKU-999",
            "name": "Product A",
            "category": cat_a.key,
            "unit": "dona",
            "price": 1000,
            "qty": 10,
            "date_received": "2026-09-20"
        }, format='json')
        self.assertEqual(res_a.status_code, 201)

        self.client.force_authenticate(user=self.admin_b)
        res_b = self.client.post(reverse('product-list'), {
            "sku": "SHARED-SKU-999",
            "name": "Product B",
            "category": cat_b.key,
            "unit": "dona",
            "price": 1200,
            "qty": 15,
            "date_received": "2026-09-20"
        }, format='json')
        self.assertEqual(res_b.status_code, 201)

    def test_cashier_can_read_settings_cannot_modify(self):
        today = timezone.localdate()
        cashier = User.objects.create_user(
            phone_number="998904444444", password="CashierPass123!", role="cashier", company=self.company,
            plan=UserPlan.STANDARD, subscription_status=SubscriptionStatus.ACTIVE,
            subscription_expires_at=today + timedelta(days=30)
        )
        self.client.force_authenticate(user=cashier)

        # 1. Read settings -> 200
        res_get = self.client.get('/api/v1/settings/')
        self.assertEqual(res_get.status_code, 200)

        # 2. Modify settings (PUT) -> 403
        res_put = self.client.put('/api/v1/settings/', {
            "store_name": "New Store Name"
        }, format='json')
        self.assertEqual(res_put.status_code, 403)

