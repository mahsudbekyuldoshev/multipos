from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models

from apps.models.markaz import Markaz


class UserRole(models.TextChoices):
    SUPERADMIN = "superadmin", "Super Admin"
    CASHIER = "cashier", "Kassir"


class UserManager(BaseUserManager):
    def create_user(self, phone_number, password=None, **extra_fields):
        if not phone_number:
            raise ValueError("Telefon raqami kiritilishi shart")
        user = self.model(phone_number=phone_number, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, password=None, **extra_fields):
        extra_fields.setdefault("role", UserRole.SUPERADMIN)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("first_name", "Super")
        extra_fields.setdefault("last_name", "Admin")
        return self.create_user(phone_number, password, **extra_fields)


class User(AbstractUser):
    username = None
    phone_number = models.CharField(max_length=20, unique=True)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    role = models.CharField(max_length=20, choices=UserRole.choices, default=UserRole.CASHIER)
    markaz = models.ForeignKey(
        Markaz, on_delete=models.SET_NULL, null=True, blank=True, related_name="users"
    )

    USERNAME_FIELD = "phone_number"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.phone_number})"
