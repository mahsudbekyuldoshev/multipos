from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.models.company import Company
from apps.models.category import Category

DEFAULT_CATEGORIES = [
    {"key": "qurilish", "label": "Qurilish", "icon": "🧱", "accent": "#4E97C4"},
    {"key": "elektrika", "label": "Elektrika", "icon": "🔌", "accent": "#E8B23B"},
    {"key": "santexnika", "label": "Santexnika", "icon": "🚰", "accent": "#3FB6AE"},
    {"key": "avto", "label": "Avto", "icon": "🚗", "accent": "#C9564B"},
]

@receiver(post_save, sender=Company)
def create_default_categories(sender, instance, created, **kwargs):
    if created:
        for cat in DEFAULT_CATEGORIES:
            Category.objects.get_or_create(company=instance, key=cat["key"], defaults=cat)
