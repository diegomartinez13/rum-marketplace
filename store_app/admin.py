from django.contrib import admin
from .models import Product, ProductCategory, Service, ServiceCategory, Order, Customer
# Register your models here.
@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'is_active', 'created_at']
    readonly_fields = ['created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'slug']

@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'is_active', 'created_at']
    readonly_fields = ['created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'slug']

admin.site.register(Customer)
admin.site.register(Product)
admin.site.register(Service)
admin.site.register(Order)