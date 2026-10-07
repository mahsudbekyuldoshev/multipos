from django.db import models
from apps.models.users import User


class SubscriptionAuditLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="subscription_logs")
    admin = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="performed_subscription_logs")
    old_date = models.DateField(null=True, blank=True)
    new_date = models.DateField(null=True, blank=True)
    action = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Cashier: {self.user} | Action: {self.action} | {self.old_date} -> {self.new_date}"


class FreeTrialUsage(models.Model):
    phone_number = models.CharField(max_length=20, unique=True)
    used_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.phone_number} - {self.used_at}"


class SubscriptionPayment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="subscription_payments")
    admin = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="processed_payments")
    months = models.PositiveIntegerField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    plan = models.CharField(max_length=20, default='standard')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} - {self.months} months ({self.amount})"
