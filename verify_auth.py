import requests, time
import django, os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "root.settings")
django.setup()
from apps.models import Company, User, SubscriptionStatus

Company.objects.all().delete()
company_a = Company.objects.create(name="Do'kon A", subscription_status=SubscriptionStatus.ACTIVE)
company_b = Company.objects.create(name="Do'kon B", subscription_status=SubscriptionStatus.INACTIVE)
User.objects.create_user(phone_number="998911111111", password="PassA123!", first_name="A", last_name="A", role="superadmin", company=company_a)
User.objects.create_user(phone_number="998922222222", password="PassB123!", first_name="B", last_name="B", role="superadmin", company=company_b)

r1 = requests.post("http://127.0.0.1:8000/api/token/", json={"phone_number": "998911111111", "password": "PassA123!"})
print("A LOGIN (200 kutiladi):", r1.status_code)

r2 = requests.post("http://127.0.0.1:8000/api/token/", json={"phone_number": "998922222222", "password": "PassB123!"})
print("B LOGIN (403 kutiladi, obuna Company darajasida ishlashi kerak):", r2.status_code, r2.json())
