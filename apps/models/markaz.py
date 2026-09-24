from django.db import models
from apps.models.company import Company


class Markaz(models.Model):
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=255, blank=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="markazlar")

    def __str__(self):
        return self.name
