import datetime
from django.db import models
from apps.models import Product
from apps.models.company import Company


class Sale(models.Model):
    id = models.CharField(max_length=50, primary_key=True)
    date = models.DateTimeField(auto_now_add=True)
    total = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    cashier = models.CharField(max_length=100, blank=True, null=True)
    store_name = models.CharField(max_length=255, default="MUSTAHKAM SAVDO MARKAZI")
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="sales")

    class Meta:
        ordering = ['-date']

    def save(self, *args, **kwargs):
        if not self.id:
            today = datetime.date.today()
            prefix = f"s_{today.strftime('%Y%m%d')}"
            # Ensure unique ID even with concurrency/existing items
            count = Sale.objects.filter(id__startswith=prefix).count()
            candidate = f"{prefix}_{count+1:04d}"
            while Sale.objects.filter(id=candidate).exists():
                count += 1
                candidate = f"{prefix}_{count+1:04d}"
            self.id = candidate
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Sale {self.id} - Total: {self.total}"


class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='items')
    # Use SET_NULL for product to preserve sale history even if a product is deleted
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True, related_name='sale_items')
    product_id_str = models.CharField(max_length=50) # Stores product ID as a backup snapshot to avoid clashing with 'product'

    # Snapshot fields of product at the time of checkout
    name = models.CharField(max_length=255)
    sku = models.CharField(max_length=50)
    category = models.CharField(max_length=50)
    date_received = models.DateField()
    unit = models.CharField(max_length=20)
    price = models.DecimalField(max_digits=15, decimal_places=2)

    # Sale details
    qty = models.DecimalField(max_digits=12, decimal_places=3)
    subtotal = models.DecimalField(max_digits=15, decimal_places=2)

    def __str__(self):
        return f"{self.qty} x {self.name} for Sale {self.sale.id}"
