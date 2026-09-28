import requests, django, os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "root.settings")
django.setup()
from apps.models import Company, User, SubscriptionStatus, Product

Product.objects.all().delete()
Company.objects.all().delete()
company_a = Company.objects.create(name="Do'kon A", subscription_status=SubscriptionStatus.ACTIVE)
User.objects.create_user(phone_number="998911111111", password="PassA123!", first_name="A", last_name="A", role="superadmin", company=company_a)

r1 = requests.post("http://127.0.0.1:8000/api/token/", json={"phone_number": "998911111111", "password": "PassA123!"})
token_a = r1.json()["access"]
headers_a = {"Authorization": f"Bearer {token_a}"}

r2 = requests.post("http://127.0.0.1:8000/api/v1/products/", json={
    "sku": "TEST-001", "name": "Test mahsulot", "category": "qurilish",
    "unit": "dona", "price": 1000, "qty": 10, "min": 2, "date_received": "2026-09-27"
}, headers=headers_a)
print("MAHSULOT QO'SHISH (201 kutiladi):", r2.status_code, r2.json())

r3 = requests.post("http://127.0.0.1:8000/api/v1/users/", json={
    "phone_number": "998933334444", "first_name": "Kassir", "last_name": "T", "password": "CashierPass123!", "role": "cashier"
}, headers=headers_a)
print("KASSIR YARATISH:", r3.status_code, r3.json())

cashier_token = requests.post("http://127.0.0.1:8000/api/token/", json={"phone_number": "998933334444", "password": "CashierPass123!"}).json()["access"]
cashier_headers = {"Authorization": f"Bearer {cashier_token}"}

r4 = requests.post("http://127.0.0.1:8000/api/v1/categories/", json={
    "key": "mebel", "label": "Mebel", "icon": "🪑", "accent": "#8B5E3C"
}, headers=cashier_headers)
print("KASSIR KATEGORIYA QO'SHADI (201 kutiladi):", r4.status_code, r4.json())
