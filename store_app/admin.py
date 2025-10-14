from django.contrib import admin
from .models import (
    User, ProductCategory, Product,
    ServiceCategory, Service,
    ProductOrder, ServiceRequest,
    Business, BusinessCategory,
    Inventory, StockedProduct, StockedService,
    Review, Cart, PurchaseHistory
)

# Register your models here.
@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'is_active', 'created_at']
    search_fields = ['name', 'slug']
    list_filter = ['is_active', 'created_at']
    readonly_fields = ['created_at']

@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'is_active', 'created_at']
    search_fields = ['name', 'slug']
    list_filter = ['is_active', 'created_at']
    readonly_fields = ['created_at']

admin.site.register(User)
admin.site.register(Product)
admin.site.register(Service)
admin.site.register(ProductOrder)
admin.site.register(ServiceRequest)
admin.site.register(Business)
admin.site.register(BusinessCategory)
admin.site.register(Inventory)
admin.site.register(StockedProduct)
admin.site.register(StockedService)
admin.site.register(Review)
admin.site.register(Cart)
admin.site.register(PurchaseHistory)

admin.site.site_header = "Rum Marketplace Admin"
admin.site.site_title = "Rum Marketplace Admin Portal"
admin.site.index_title = "Welcome to Rum Marketplace Admin Portal"