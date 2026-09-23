from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from apps.models import User, Product, Settings, Sale, SaleItem, Markaz

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    ordering = ('phone_number',)
    fieldsets = UserAdmin.fieldsets + (
        ("Qo'shimcha", {"fields": ("phone_number", "role", "markaz")}),
    )
    list_display = ('phone_number', 'first_name', 'last_name', 'role')

@admin.register(Markaz)
class MarkazAdmin(admin.ModelAdmin):
    list_display = ('name', 'address')

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'sku', 'price', 'qty')

@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('id', 'date', 'total', 'cashier')

@admin.register(SaleItem)
class SaleItemAdmin(admin.ModelAdmin):
    list_display = ('sale', 'name', 'qty', 'subtotal')

@admin.register(Settings)
class SettingsAdmin(admin.ModelAdmin):
    list_display = ('store_name',)
