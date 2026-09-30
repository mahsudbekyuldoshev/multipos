"""
MultiPOS backend — smoke-test skripti.

Bu skript frontend qiladigan barcha asosiy so'rovlarni simulyatsiya qiladi va
har birining natijasini (status kod, maydon nomlari, shakl) tekshiradi.
Faqat chop etib qo'ymaydi — har bir tekshiruv PASS/FAIL bilan aniq ko'rsatiladi,
oxirida umumiy hisobot chiqadi.

Ishlatish:
    uv run python smoke_test.py

Talablar:
    - Backend lokal serverda ishlab turishi kerak: uv run python manage.py runserver 127.0.0.1:8000
    - Skript Django ORM orqali (to'g'ridan-to'g'ri bazaga) bir martalik test
      kompaniya/foydalanuvchi yaratadi — shuning uchun backend loyihasi papkasida
      ishga tushirilishi kerak (manage.py bilan bir joyda emas, lekin shu venv/uv
      muhitida).
"""

import os
import sys
import django
import requests
from decimal import Decimal

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "root.settings")
django.setup()

from apps.models import Company, User, SubscriptionStatus, Category, Product  # noqa: E402

BASE = "http://127.0.0.1:8000"

passed = []
failed = []


def check(name, condition, detail=""):
    if condition:
        passed.append(name)
        print(f"  \u2705 {name}")
    else:
        failed.append((name, detail))
        print(f"  \u274c {name}" + (f"  \u2192 {detail}" if detail else ""))


def section(title):
    print(f"\n--- {title} ---")


def try_check(name, fn):
    """fn chaqiradi, xato chiqsa ham skript davom etadi."""
    try:
        fn()
    except Exception as e:  # noqa: BLE001
        failed.append((name, f"kutilmagan xato: {e}"))
        print(f"  \u274c {name}  \u2192 kutilmagan xato: {e}")


# =========================================================================
# 0. Test ma'lumotlarini tayyorlash (Django ORM orqali — API orqali emas,
#    chunki kompaniya yaratish API'da yo'q, faqat Django Admin/ORM orqali)
# =========================================================================
section("0. Test muhitini tayyorlash")

Company.objects.filter(name__startswith="SMOKE-TEST").delete()

company_a = Company.objects.create(name="SMOKE-TEST A", subscription_status=SubscriptionStatus.ACTIVE)
company_b = Company.objects.create(name="SMOKE-TEST B", subscription_status=SubscriptionStatus.INACTIVE)

superadmin_a = User.objects.create_user(
    phone_number="998900000001", password="SmokeAdmin123!",
    first_name="Smoke", last_name="AdminA", role="superadmin", company=company_a,
)
User.objects.create_user(
    phone_number="998900000002", password="SmokeAdmin123!",
    first_name="Smoke", last_name="AdminB", role="superadmin", company=company_b,
)

check("Test kompaniyalari va superadminlar yaratildi", True)

# =========================================================================
# 1. Autentifikatsiya
# =========================================================================
section("1. Autentifikatsiya")

token_a = None
refresh_a = None


def t1_login_ok():
    global token_a, refresh_a
    r = requests.post(f"{BASE}/api/token/", json={
        "phone_number": "998900000001", "password": "SmokeAdmin123!"
    })
    check("Login (to'g'ri parol) -> 200", r.status_code == 200, f"status={r.status_code}, body={r.text[:200]}")
    if r.status_code == 200:
        data = r.json()
        check("Javobda 'access' bor", "access" in data)
        check("Javobda 'refresh' bor", "refresh" in data)
        token_a = data.get("access")
        refresh_a = data.get("refresh")


def t2_login_bad_password():
    r = requests.post(f"{BASE}/api/token/", json={
        "phone_number": "998900000001", "password": "notogri"
    })
    check("Login (noto'g'ri parol) -> 401", r.status_code == 401, f"status={r.status_code}")


def t3_login_inactive_company_blocks_superadmin():
    r = requests.post(f"{BASE}/api/token/", json={
        "phone_number": "998900000002", "password": "SmokeAdmin123!"
    })
    check(
        "Nofaol obunali kompaniya superadmini -> 403 (Company darajasidagi tekshiruv)",
        r.status_code == 403, f"status={r.status_code}, body={r.text[:200]}"
    )
    if r.status_code == 403:
        check("403 javobida 'detail' maydoni bor", "detail" in r.json())


def t4_token_refresh():
    if not refresh_a:
        check("Token refresh", False, "oldingi login muvaffaqiyatsiz, refresh token yo'q")
        return
    r = requests.post(f"{BASE}/api/token/refresh/", json={"refresh": refresh_a})
    check("Token refresh -> 200 va yangi 'access' beradi", r.status_code == 200 and "access" in r.json())


try_check("1.1 Login (to'g'ri)", t1_login_ok)
try_check("1.2 Login (noto'g'ri parol)", t2_login_bad_password)
try_check("1.3 Nofaol obuna bloklaydi", t3_login_inactive_company_blocks_superadmin)
try_check("1.4 Token refresh", t4_token_refresh)

headers_a = {"Authorization": f"Bearer {token_a}"} if token_a else {}

# =========================================================================
# 2. Profil
# =========================================================================
section("2. Profil")


def t5_profile_get():
    r = requests.get(f"{BASE}/api/v1/profile/", headers=headers_a)
    check("GET /profile/ -> 200", r.status_code == 200, f"status={r.status_code}")
    if r.status_code == 200:
        data = r.json()
        for field in ("id", "phoneNumber", "firstName", "lastName", "role", "markaz"):
            check(f"Profilda '{field}' maydoni bor (camelCase)", field in data, f"kelgan maydonlar: {list(data.keys())}")
        check("role == 'superadmin'", data.get("role") == "superadmin", f"kelgan: {data.get('role')}")


try_check("2.1 Profil ko'rish", t5_profile_get)

# =========================================================================
# 3. Kategoriyalar — dinamik, pagination'siz, kassir ham yoza oladi
# =========================================================================
section("3. Kategoriyalar")

cashier_headers = {}


def t6_categories_list_flat():
    r = requests.get(f"{BASE}/api/v1/categories/", headers=headers_a)
    check("GET /categories/ -> 200", r.status_code == 200)
    if r.status_code == 200:
        data = r.json()
        check("Javob yalang'och massiv (pagination'siz)", isinstance(data, list), f"kelgan tur: {type(data)}")
        if isinstance(data, list):
            check("Kamida 4 ta boshlang'ich kategoriya bor", len(data) >= 4, f"soni: {len(data)}")
            keys = [c.get("key") for c in data]
            for expected in ("qurilish", "elektrika", "santexnika", "avto"):
                check(f"'{expected}' kategoriyasi bor", expected in keys)


def t7_create_cashier_and_test_category_crud():
    global cashier_headers
    r = requests.post(f"{BASE}/api/v1/users/", json={
        "phone_number": "998900000003", "first_name": "Smoke", "last_name": "Cashier",
        "password": "SmokeCashier123!"
    }, headers=headers_a)
    check("Kassir yaratish -> 201", r.status_code == 201, f"status={r.status_code}, body={r.text[:200]}")

    r2 = requests.post(f"{BASE}/api/token/", json={
        "phone_number": "998900000003", "password": "SmokeCashier123!"
    })
    check("Kassir login -> 200", r2.status_code == 200)
    if r2.status_code == 200:
        cashier_headers = {"Authorization": f"Bearer {r2.json()['access']}"}

    r3 = requests.post(f"{BASE}/api/v1/categories/", json={
        "key": "smoke-cat", "label": "Smoke kategoriya", "icon": "\U0001F9EA", "accent": "#123456"
    }, headers=cashier_headers)
    check("Kassir kategoriya QO'SHADI -> 201", r3.status_code == 201, f"status={r3.status_code}, body={r3.text[:200]}")

    r4 = requests.patch(f"{BASE}/api/v1/categories/smoke-cat/", json={"label": "Yangilangan nom"}, headers=cashier_headers)
    check("Kassir kategoriyani O'ZGARTIRADI -> 200", r4.status_code == 200, f"status={r4.status_code}")

    r5 = requests.delete(f"{BASE}/api/v1/categories/smoke-cat/", headers=cashier_headers)
    check("Kassir bo'sh kategoriyani O'CHIRADI -> 204", r5.status_code == 204, f"status={r5.status_code}")


try_check("3.1 Kategoriyalar ro'yxati", t6_categories_list_flat)
try_check("3.2 Kassir + kategoriya CRUD", t7_create_cashier_and_test_category_crud)

# =========================================================================
# 4. Mahsulotlar — faqat superadmin yozadi, pagination bilan
# =========================================================================
section("4. Mahsulotlar")

product_id = None


def t8_products_list_paginated():
    r = requests.get(f"{BASE}/api/v1/products/", headers=headers_a)
    check("GET /products/ -> 200", r.status_code == 200)
    if r.status_code == 200:
        data = r.json()
        for field in ("count", "next", "previous", "results"):
            check(f"Pagination'da '{field}' maydoni bor", field in data, f"kelgan: {list(data.keys())}")


def t9_superadmin_creates_product():
    global product_id
    r = requests.post(f"{BASE}/api/v1/products/", json={
        "sku": "SMOKE-001", "name": "Smoke mahsulot", "category": "qurilish",
        "unit": "dona", "price": 15000, "qty": 20, "min": 5, "date_received": "2026-09-29"
    }, headers=headers_a)
    check("Superadmin mahsulot QO'SHADI -> 201", r.status_code == 201, f"status={r.status_code}, body={r.text[:300]}")
    if r.status_code == 201:
        data = r.json()
        product_id = data.get("id")
        for field in ("dateReceived", "lowStock", "createdAt", "updatedAt"):
            check(f"Javobda '{field}' (camelCase) bor", field in data, f"kelgan: {list(data.keys())}")
        check("id butun son", isinstance(product_id, int), f"tur: {type(product_id)}")


def t10_cashier_cannot_create_product():
    r = requests.post(f"{BASE}/api/v1/products/", json={
        "sku": "HACK-SMOKE", "name": "Ruxsatsiz", "category": "qurilish",
        "unit": "dona", "price": 100, "qty": 1, "min": 1, "date_received": "2026-09-29"
    }, headers=cashier_headers)
    check("Kassir mahsulot qo'shishga urinadi -> 403", r.status_code == 403, f"status={r.status_code}")


def t11_cashier_can_view_products():
    r = requests.get(f"{BASE}/api/v1/products/", headers=cashier_headers)
    check("Kassir mahsulotlarni ko'radi -> 200", r.status_code == 200, f"status={r.status_code}")


try_check("4.1 Mahsulotlar ro'yxati (pagination)", t8_products_list_paginated)
try_check("4.2 Superadmin mahsulot qo'shadi", t9_superadmin_creates_product)
try_check("4.3 Kassir mahsulot qo'sha olmaydi", t10_cashier_cannot_create_product)
try_check("4.4 Kassir mahsulotlarni ko'radi", t11_cashier_can_view_products)

# =========================================================================
# 5. Checkout (sotish)
# =========================================================================
section("5. Checkout")


def t12_checkout_success():
    if not product_id:
        check("Checkout (muvaffaqiyatli)", False, "product_id yo'q, oldingi qadam muvaffaqiyatsiz")
        return
    r = requests.post(f"{BASE}/api/v1/sales/", json={
        "items": [{"product_id": product_id, "qty": 2.5}]
    }, headers=headers_a)
    check("Checkout (yetarli stok) -> 201", r.status_code == 201, f"status={r.status_code}, body={r.text[:300]}")
    if r.status_code == 201:
        data = r.json()
        check("Javobda 'items' bor", "items" in data)
        if data.get("items"):
            item = data["items"][0]
            for field in ("productId", "name", "sku", "category", "dateReceived", "unit", "price", "qty", "subtotal"):
                check(f"Chek qatorida '{field}' bor", field in item, f"kelgan: {list(item.keys())}")


def t13_checkout_insufficient_stock():
    if not product_id:
        check("Checkout (stok yetmasa)", False, "product_id yo'q")
        return
    r = requests.post(f"{BASE}/api/v1/sales/", json={
        "items": [{"product_id": product_id, "qty": 99999}]
    }, headers=headers_a)
    check("Stok yetmasa -> 409", r.status_code == 409, f"status={r.status_code}")
    if r.status_code == 409:
        data = r.json()
        for field in ("error", "message", "details"):
            check(f"409 javobida '{field}' bor", field in data, f"kelgan: {list(data.keys())}")


def t14_checkout_product_not_found():
    r = requests.post(f"{BASE}/api/v1/sales/", json={
        "items": [{"product_id": 999999999, "qty": 1}]
    }, headers=headers_a)
    check("Mavjud bo'lmagan mahsulot -> 404", r.status_code == 404, f"status={r.status_code}")


def t15_checkout_empty_cart():
    r = requests.post(f"{BASE}/api/v1/sales/", json={"items": []}, headers=headers_a)
    check("Bo'sh savat -> 400", r.status_code == 400, f"status={r.status_code}")


def t16_sales_stats_today():
    r = requests.get(f"{BASE}/api/v1/sales/stats/today/", headers=headers_a)
    check("GET /sales/stats/today/ -> 200", r.status_code == 200, f"status={r.status_code}")
    if r.status_code == 200:
        data = r.json()
        check("Javobda 'count' va 'total' bor", "count" in data and "total" in data, f"kelgan: {list(data.keys())}")


try_check("5.1 Checkout muvaffaqiyatli", t12_checkout_success)
try_check("5.2 Checkout — stok yetmasa", t13_checkout_insufficient_stock)
try_check("5.3 Checkout — mahsulot topilmasa", t14_checkout_product_not_found)
try_check("5.4 Checkout — bo'sh savat", t15_checkout_empty_cart)
try_check("5.5 Bugungi statistika", t16_sales_stats_today)

# =========================================================================
# 6. Sozlamalar — kassir o'qiydi, faqat superadmin yozadi
# =========================================================================
section("6. Sozlamalar")


def t17_settings_get_both_roles():
    r1 = requests.get(f"{BASE}/api/v1/settings/", headers=headers_a)
    check("Superadmin sozlamani ko'radi -> 200", r1.status_code == 200, f"status={r1.status_code}")
    r2 = requests.get(f"{BASE}/api/v1/settings/", headers=cashier_headers)
    check("Kassir sozlamani ko'radi -> 200", r2.status_code == 200, f"status={r2.status_code}")


def t18_settings_put_permission():
    r1 = requests.put(f"{BASE}/api/v1/settings/", json={"store_name": "Smoke Do'kon"}, headers=headers_a)
    check("Superadmin sozlamani o'zgartiradi -> 200", r1.status_code == 200, f"status={r1.status_code}")
    r2 = requests.put(f"{BASE}/api/v1/settings/", json={"store_name": "Buzilgan"}, headers=cashier_headers)
    check("Kassir sozlamani o'zgartirishga urinadi -> 403", r2.status_code == 403, f"status={r2.status_code}")


try_check("6.1 Sozlamalarni ko'rish (ikkisi ham)", t17_settings_get_both_roles)
try_check("6.2 Sozlamalarni o'zgartirish (faqat superadmin)", t18_settings_put_permission)

# =========================================================================
# 7. Aloqa formasi — tokensiz
# =========================================================================
section("7. Aloqa formasi")


def t19_contact_no_auth():
    r = requests.post(f"{BASE}/api/v1/contact/", json={
        "name": "Smoke Test", "phone": "998900000099", "message": "Bu — smoke-test xabari."
    })
    check("Aloqa formasi (tokensiz) -> 201", r.status_code == 201, f"status={r.status_code}, body={r.text[:200]}")
    if r.status_code == 201:
        data = r.json()
        for field in ("id", "name", "phone", "message", "createdAt"):
            check(f"Javobda '{field}' bor", field in data, f"kelgan: {list(data.keys())}")


try_check("7.1 Aloqa formasi", t19_contact_no_auth)

# =========================================================================
# 8. Ko'p-mijozli izolyatsiya (qisqacha)
# =========================================================================
section("8. Ko'p-mijozli izolyatsiya")


def t20_company_isolation():
    company_b.subscription_status = SubscriptionStatus.ACTIVE
    company_b.save()
    r1 = requests.post(f"{BASE}/api/token/", json={
        "phone_number": "998900000002", "password": "SmokeAdmin123!"
    })
    check("B kompaniyasi endi login qila oladi (obuna faollashtirilgach)", r1.status_code == 200)
    if r1.status_code == 200:
        headers_b = {"Authorization": f"Bearer {r1.json()['access']}"}
        r2 = requests.get(f"{BASE}/api/v1/products/", headers=headers_b)
        if r2.status_code == 200:
            results = r2.json().get("results", [])
            check("B kompaniyasi A'ning mahsulotlarini KO'RMAYDI", len(results) == 0, f"ko'rilgan soni: {len(results)}")
        if product_id:
            r3 = requests.get(f"{BASE}/api/v1/products/{product_id}/", headers=headers_b)
            check("B kompaniyasi A'ning mahsulotini ID orqali topa olmaydi -> 404", r3.status_code == 404, f"status={r3.status_code}")


try_check("8.1 Kompaniyalar izolyatsiyasi", t20_company_isolation)

# =========================================================================
# Yakuniy hisobot
# =========================================================================
print("\n" + "=" * 60)
print(f"NATIJA: {len(passed)} PASS, {len(failed)} FAIL")
print("=" * 60)

if failed:
    print("\nMUVAFFAQIYATSIZ TEKSHIRUVLAR:")
    for name, detail in failed:
        print(f"  - {name}: {detail}")
    sys.exit(1)
else:
    print("\nBarcha tekshiruvlar muvaffaqiyatli o'tdi.")
    sys.exit(0)