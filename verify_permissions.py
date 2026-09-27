import requests, time
import django, os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "root.settings")
django.setup()
from apps.models import Company, User, SubscriptionStatus, Product

# Clean up
Company.objects.all().delete()

# Create company and superadmin
company_a = Company.objects.create(name="Do'kon A", subscription_status=SubscriptionStatus.ACTIVE)
admin_a = User.objects.create_user(phone_number="998911111111", password="PassA123!", first_name="Admin", last_name="A", role="superadmin", company=company_a)
product_a = Product.objects.create(company=company_a, sku="A-PROD", name="Prod A", price=1000, qty=10, date_received="2026-09-24")
product_a_id = product_a.id

BASE = "http://127.0.0.1:8000"

# Get Superadmin token
r_login = requests.post(f"{BASE}/api/token/", json={"phone_number": "998911111111", "password": "PassA123!"})
token_a = r_login.json()["access"]
headers_a = {"Authorization": f"Bearer {token_a}"}

# 1. Create Cashier via API
r1 = requests.post(f"{BASE}/api/v1/users/", json={
    "phone_number": "998933334444", "first_name": "Kassir", "last_name": "Test", "password": "CashierPass123!"
}, headers=headers_a)
print("KASSIR YARATILDI:", r1.status_code)

# 2. Get Cashier token
r2 = requests.post(f"{BASE}/api/token/", json={"phone_number": "998933334444", "password": "CashierPass123!"})
cashier_token = r2.json()["access"]
cashier_headers = {"Authorization": f"Bearer {cashier_token}"}

# 3. Cashier tries to add product (expect 403)
r3 = requests.post(f"{BASE}/api/v1/products/", json={
    "sku": "HACK-001", "name": "Ruxsatsiz mahsulot", "category": "qurilish",
    "unit": "dona", "price": 100, "qty": 1, "min": 1, "date_received": "2026-09-24"
}, headers=cashier_headers)
print("KASSIR MAHSULOT QO'SHISHga URINADI (403 kutiladi):", r3.status_code)

# 4. Cashier views products (expect 200)
r4 = requests.get(f"{BASE}/api/v1/products/", headers=cashier_headers)
print("KASSIR MAHSULOTLARNI KO'RADI (200 kutiladi):", r4.status_code)

# 5. Cashier tries to modify settings (expect 403)
r5 = requests.put(f"{BASE}/api/v1/settings/", json={"store_name": "Buzilgan nom"}, headers=cashier_headers)
print("KASSIR SOZLAMANI O'ZGARTIRISHGA URINADI (403 kutiladi):", r5.status_code)

# 6. Cashier views settings (expect 200)
r6 = requests.get(f"{BASE}/api/v1/settings/", headers=cashier_headers)
print("KASSIR SOZLAMANI KO'RADI (200 kutiladi):", r6.status_code)

# 7. Cashier sells product (expect 201)
r7 = requests.post(f"{BASE}/api/v1/sales/", json={"items": [{"product_id": product_a_id, "qty": 1}]}, headers=cashier_headers)
print("KASSIR SOTADI (201 kutiladi, hali ishlashi kerak):", r7.status_code)
