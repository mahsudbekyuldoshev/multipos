from django.db import models
from apps.models.company import Company


class Category(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="categories")
    key = models.SlugField(max_length=50)
    label = models.CharField(max_length=100)
    icon = models.CharField(max_length=10, blank=True)
    accent = models.CharField(max_length=20, blank=True)

    class Meta:
        unique_together = ("company", "key")

    def __str__(self):
        return f"{self.label} ({self.company.name})"
