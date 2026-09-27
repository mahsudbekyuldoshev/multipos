import requests, time
import django, os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "root.settings")
django.setup()
from apps.models import Company, User, SubscriptionStatus

# Clean up previous test entries if any
Company.objects.all().delete()

# --- Platforma egasi 2 ta kompaniya yaratadi ---
company_a = Company.objects.create(name="Do'kon A", subscription_status=SubscriptionStatus.ACTIVE)
company_b = Company.objects.create(name="Do'kon B", subscription_status=SubscriptionStatus.INACTIVE)

# --- Superadminlar yaratish ---
admin_a = User.objects.create_user(phone_number="998911111111", password="PassA123!", first_name="Admin", last_name="A", role="superadmin", company=company_a)
admin_b = User.objects.create_user(phone_number="998922222222", password="PassB123!", first_name="Admin", last_name="B", role="superadmin", company=company_b)

BASE = "http://127.0.0.1:8000"

# --- A kompaniyasi superadmini login qiladi ---
r = requests.post(f"{BASE}/api/token/", json={"phone_number": "998911111111", "password": "PassA123!"})
print("A LOGIN:", r.status_code)
token_a = r.json()["access"]
headers_a = {"Authorization": f"Bearer {token_a}"}

# --- /settings/ testlari ---
r1 = requests.get(f"{BASE}/api/v1/settings/", headers=headers_a)
print("A SETTINGS GET:", r1.status_code, r1.json())

r2 = requests.put(f"{BASE}/api/v1/settings/", json={"store_name": "A Do'koni"}, headers=headers_a)
print("A SETTINGS PUT:", r2.status_code, r2.json())

# --- B kompaniyasi login qilishga urinadi (obuna inactive) ---
r3 = requests.post(f"{BASE}/api/token/", json={"phone_number": "998922222222", "password": "PassB123!"})
print("B LOGIN (403 kutiladi, obuna inactive):", r3.status_code, r3.json())

# --- B kompaniyasining obunasini faollashtiramiz ---
company_b.subscription_status = SubscriptionStatus.ACTIVE
company_b.save()

r4 = requests.post(f"{BASE}/api/token/", json={"phone_number": "998922222222", "password": "PassB123!"})
print("B LOGIN (endi 200 kutiladi):", r4.status_code)
token_b = r4.json()["access"]
headers_b = {"Authorization": f"Bearer {token_b}"}

r3_settings = requests.get(f"{BASE}/api/v1/settings/", headers=headers_b)
print("B SETTINGS GET (o'zining, boshqacha bo'lishi kerak):", r3_settings.status_code, r3_settings.json())

# --- Bir xil SKU ikki kompaniyada ham ishlashi kerak ---
r_prod_a = requests.post(f"{BASE}/api/v1/products/", json={
    "sku": "SAME-SKU", "name": "A mahsuloti", "category": "qurilish",
    "unit": "dona", "price": 1000, "qty": 10, "min": 2, "date_received": "2026-09-24"
}, headers=headers_a)
print("A PRODUCT CREATE:", r_prod_a.status_code, r_prod_a.json())
product_a_id = r_prod_a.json().get("id")

r4_prod = requests.post(f"{BASE}/api/v1/products/", json={
    "sku": "SAME-SKU", "name": "B mahsuloti", "category": "qurilish",
    "unit": "dona", "price": 500, "qty": 5, "min": 1, "date_received": "2026-09-24"
}, headers=headers_b)
print("B CREATES SAME SKU AS A (201 kutiladi, xato emas):", r4_prod.status_code, r4_prod.json())

# --- Checkout — A kompaniyasi o'z mahsulotini sotadi ---
r5 = requests.post(f"{BASE}/api/v1/sales/", json={"items": [{"product_id": product_a_id, "qty": 2}]}, headers=headers_a)
print("A CHECKOUT:", r5.status_code, r5.json())

# --- Checkout — B A'ning mahsulotini sotishga urinsa, topilmasligi kerak ---
r6 = requests.post(f"{BASE}/api/v1/sales/", json={"items": [{"product_id": product_a_id, "qty": 1}]}, headers=headers_b)
print("B TRIES TO SELL A's PRODUCT (400/404 kutiladi):", r6.status_code, r6.json())

# --- A kompaniyasi haqiqiy mahsulotining boshlang'ich qoldig'ini eslab qol ---
product_check = requests.get(f"{BASE}/api/v1/products/{product_a_id}/", headers=headers_a)
qty_before = float(product_check.json()["qty"])
print("QTY OLDIN:", qty_before)

# --- Savatda: A'ning haqiqiy mahsuloti + mavjud bo'lmagan ID ---
r7 = requests.post(f"{BASE}/api/v1/sales/", json={
    "items": [
        {"product_id": product_a_id, "qty": 1},
        {"product_id": 999999, "qty": 1}
    ]
}, headers=headers_a)
print("ARALASH SAVAT (404 kutiladi):", r7.status_code, r7.json())

# --- ENG MUHIM TEKSHIRUV: qoldiq O'ZGARMAGAN bo'lishi kerak (birinchi mahsulot ham commit qilinmagan) ---
product_check2 = requests.get(f"{BASE}/api/v1/products/{product_a_id}/", headers=headers_a)
qty_after = float(product_check2.json()["qty"])
print("QTY KEYIN (OLDINGI BILAN BIR XIL bo'lishi kerak):", qty_after)
assert qty_before == qty_after, "XATO: qisman commit bo'lgan! Tranzaksiya buzilgan."
print("TASDIQLANDI: qisman commit yo'q, tranzaksiya to'g'ri ishlaydi.")
