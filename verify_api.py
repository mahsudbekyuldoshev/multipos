import requests, time
time.sleep(2)
# Login
r = requests.post("http://127.0.0.1:8000/api/token/", json={"phone_number": "998901234567", "password": "StrongPass123!"})
print("LOGIN:", r.status_code, r.json())
token = r.json()["access"]
headers = {"Authorization": f"Bearer {token}"}

# Markaz yaratish
r2 = requests.post("http://127.0.0.1:8000/api/v1/markazlar/", json={"name": "Bosh filial", "address": "Toshkent"}, headers=headers)
print("MARKAZ:", r2.status_code, r2.json())
markaz_id = r2.json().get("id")

# Kassir yaratish (markaz bilan)
r3 = requests.post("http://127.0.0.1:8000/api/v1/users/", json={
    "phone_number": "998911111111", "first_name": "Aziz", "last_name": "Aliyev",
    "markaz": markaz_id, "password": "CashierPass123!"
}, headers=headers)
print("CASHIER CREATE:", r3.status_code, r3.json())

# Kassir markazsiz yaratish
r4 = requests.post("http://127.0.0.1:8000/api/v1/users/", json={
    "phone_number": "998922222222", "first_name": "Nodira", "last_name": "Karimova",
    "password": "CashierPass456!"
}, headers=headers)
print("CASHIER (no markaz):", r4.status_code, r4.json())

# Kassir sifatida login
r5 = requests.post("http://127.0.0.1:8000/api/token/", json={"phone_number": "998911111111", "password": "CashierPass123!"})
print("CASHIER LOGIN:", r5.status_code)
cashier_token = r5.json()["access"]
cashier_headers = {"Authorization": f"Bearer {cashier_token}"}

# Kassir o'z profilini ko'radi
r6 = requests.get("http://127.0.0.1:8000/api/v1/profile/", headers=cashier_headers)
print("PROFILE:", r6.status_code, r6.json())

# Kassir parolni o'zgartira oladi
r7 = requests.patch("http://127.0.0.1:8000/api/v1/profile/", json={
    "old_password": "CashierPass123!", "new_password": "NewPass789!"
}, headers=cashier_headers)
print("PROFILE UPDATE:", r7.status_code, r7.json())

# Kassir foydalanuvchi yaratishga urinsa — 403 bo'lishi kerak
r8 = requests.post("http://127.0.0.1:8000/api/v1/users/", json={
    "phone_number": "998933333333", "first_name": "Test", "last_name": "Test", "password": "x"
}, headers=cashier_headers)
print("CASHIER TRYING TO CREATE USER (expect 403):", r8.status_code)
