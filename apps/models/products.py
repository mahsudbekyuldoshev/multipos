from django.db import models


class ProductCategory(models.TextChoices):
    QURILISH = 'qurilish', 'Qurilish'
    ELEKTRIKA = 'elektrika', 'Elektrika'
    SANTEXNIKA = 'santexnika', 'Santexnika'
    AVTO = 'avto', 'Avto'


class ProductUnit(models.TextChoices):
    DONA = 'dona', 'dona'
    KG = 'kg', 'kg'
    METR = 'metr', 'metr'
    QUTI = 'quti', 'quti'
    RULON = 'rulon', 'rulon'
    QOP = 'qop', 'qop'
    LITR = 'litr', 'litr'


class Product(models.Model):
    sku = models.CharField(max_length=50, unique=True, db_index=True)
    name = models.CharField(max_length=255)
    category = models.CharField(
        max_length=20,
        choices=ProductCategory.choices,
        default=ProductCategory.QURILISH
    )
    unit = models.CharField(
        max_length=20,
        choices=ProductUnit.choices,
        default=ProductUnit.DONA
    )
    price = models.DecimalField(max_digits=15, decimal_places=2)
    qty = models.DecimalField(max_digits=12, decimal_places=3, default=0.0)
    min = models.DecimalField(max_digits=12, decimal_places=3, default=0.0)
    date_received = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    @property
    def low_stock(self):
        return self.qty <= self.min

    def __str__(self):
        return f"{self.name} ({self.sku})"


class Settings(models.Model):
    store_name = models.CharField(max_length=255, default="MUSTAHKAM SAVDO MARKAZI")

    class Meta:
        verbose_name_plural = "Settings"

    def __str__(self):
        return self.store_name
