from django.db import models
from django.utils import timezone


class SubscriptionStatus(models.TextChoices):
    ACTIVE = "active", "Faol"
    INACTIVE = "inactive", "Faol emas"


class Company(models.Model):
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20, blank=True)
    subscription_status = models.CharField(
        max_length=20, choices=SubscriptionStatus.choices, default=SubscriptionStatus.ACTIVE
    )
    subscription_expires_at = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    @property
    def is_subscription_valid(self):
        if self.subscription_status != SubscriptionStatus.ACTIVE:
            return False
        if self.subscription_expires_at and self.subscription_expires_at < timezone.now().date():
            return False
        return True
