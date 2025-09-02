from django.contrib import admin
from .models import Product, ProductCategory, Service, ServiceCategory, Order, Customer
# Register your models here.
admin.site.register(Customer)
admin.site.register(Product)
admin.site.register(ProductCategory)
admin.site.register(Service)
admin.site.register(ServiceCategory)
admin.site.register(Order)