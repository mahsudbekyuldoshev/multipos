from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

from apps.models.markaz import Markaz
from apps.models.company import Company, SubscriptionStatus


class UserRole(models.TextChoices):
    SUPERADMIN = "superadmin", "Super Admin"
    CASHIER = "cashier", "Kassir"


class UserPlan(models.TextChoices):
    FREE = "free", "Free"
    STANDARD = "standard", "Standard"


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
    first_name = models.CharField(max_length=150, blank=True, null=True)
    last_name = models.CharField(max_length=150, blank=True, null=True)
    role = models.CharField(max_length=20, choices=UserRole.choices, default=UserRole.CASHIER)
    plan = models.CharField(max_length=20, choices=UserPlan.choices, default=UserPlan.FREE)
    markaz = models.ForeignKey(
        Markaz, on_delete=models.SET_NULL, null=True, blank=True, related_name="users"
    )
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, null=True, blank=True, related_name="users"
    )
    subscription_status = models.CharField(
        max_length=20, choices=SubscriptionStatus.choices, default=SubscriptionStatus.ACTIVE
    )
    subscription_expires_at = models.DateField(null=True, blank=True)

    USERNAME_FIELD = "phone_number"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        ordering = ["-id"]

    @property
    def is_subscription_valid(self):
        if self.role == UserRole.SUPERADMIN:
            return True
        if self.subscription_status != SubscriptionStatus.ACTIVE:
            return False
        if not self.subscription_expires_at:
            return False
        if self.subscription_expires_at < timezone.localdate():
            return False
        return True

    @property
    def computed_status(self):
        if self.role == UserRole.SUPERADMIN:
            return "active"
        today = timezone.localdate()
        if self.subscription_status != SubscriptionStatus.ACTIVE:
            return "inactive"
        if not self.subscription_expires_at:
            return "expired"
        if self.subscription_expires_at < today:
            return "expired"
        return "active"

    @property
    def days_left(self):
        if not self.subscription_expires_at:
            return 0
        return (self.subscription_expires_at - timezone.localdate()).days

    def __str__(self):
        return f"{self.first_name or ''} {self.last_name or ''} ({self.phone_number})"
