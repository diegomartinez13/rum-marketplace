from django.db import models
from decimal import Decimal
import datetime

# Customer
class Customer(models.Model):
  first_name = models.CharField(max_length=50)
  last_name = models.CharField(max_length=100)
  email = models.EmailField(max_length=100)
  password = models.CharField(max_length=100)
  phone_number = models.CharField(max_length=20)
  is_vendor = models.BooleanField(default=False)
  is_provider = models.BooleanField(default=False)
  
  def __str__(self) -> str:
    return f"{self.first_name} {self.last_name}"

# Product Category
class ProductCategory(models.Model):
  name = models.CharField(max_length=50)
  slug = models.SlugField(max_length=50, unique=True)
  description = models.TextField(max_length=250, default='', blank= True, null=True)
  image = models.ImageField(upload_to="uploads/categories_images/", blank=True, null=True)
  parent = models.ForeignKey('self', on_delete=models.SET_NULL, related_name='children', null=True, blank=True)
  is_active = models.BooleanField(default=True)
  created_at = models.DateTimeField(auto_now_add=True)

  def __str__(self) -> str:
    return self.name
  
  class Meta:
        verbose_name_plural = "Product Categories"

# Product
class Product(models.Model):
  name = models.CharField(max_length=50)
  price = models.DecimalField(default=Decimal('0.00'), decimal_places=2, max_digits= 6)
  category = models.ForeignKey(ProductCategory, on_delete=models.CASCADE)
  description = models.TextField(max_length=250, default='', blank= True, null=True)
  image = models.ImageField(upload_to="uploads/products/")
  sale_price = models.DecimalField(default=Decimal('0.00'), decimal_places=2, max_digits= 6)
  is_sale = models.BooleanField(default=False)

  def __str__(self) -> str:
    return self.name

# Service Category
class ServiceCategory(models.Model):
  name = models.CharField(max_length=50, unique=True)
  slug = models.SlugField(max_length=50, unique=True)
  description = models.TextField(max_length=250, default='', blank= True, null=True)
  image = models.ImageField(upload_to="uploads/categories_images/", blank=True, null=True)
  parent = models.ForeignKey('self', on_delete=models.SET_NULL, related_name='children', null=True, blank=True)
  is_active = models.BooleanField(default=True)
  created_at = models.DateTimeField(auto_now_add=True)

  def __str__(self) -> str:
    return self.name
  
  class Meta:
        verbose_name_plural = "Service Categories"

# Service 
class Service(models.Model):
  name = models.CharField(max_length=50)
  price = models.DecimalField(default=Decimal('0.00'), decimal_places=2, max_digits= 6)
  category = models.ForeignKey(ServiceCategory, on_delete=models.CASCADE)
  description = models.TextField(max_length=250, default='', blank= True, null=True)
  image = models.ImageField(upload_to="uploads/services/")
  
  def __str__(self) -> str:
    return self.name

# Order
class Order(models.Model):
  product = models.ForeignKey(Product, on_delete=models.CASCADE)
  customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
  quantity = models.IntegerField(default = 1)
  address = models.CharField(max_length=100, default='', blank=True, null=True)
  phone = models.CharField(max_length=20, default='', blank=True, null=True)
  date = models.DateField(default=datetime.date.today)
  status = models.BooleanField(default=False)
  
  def __str__(self) -> str:
    return f"{self.product}"