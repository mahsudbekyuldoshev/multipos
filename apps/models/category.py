from django.db import models
from django.utils.text import slugify


class Category(models.Model):
    key = models.CharField(max_length=50, primary_key=True, unique=True, db_index=True)
    label = models.CharField(max_length=100)
    icon = models.CharField(max_length=10)  # Emoji
    accent = models.CharField(max_length=7)  # Hex color code

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = slugify(self.label)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.label
