from django.db import models
from django.conf import settings

class Category(models.Model):
    name = models.CharField(max_length=80, unique=True)
    def __str__(self): return self.name

class Listing(models.Model):
    title = models.CharField(max_length=120)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    exchange = models.BooleanField(default=False)   # “exchange” badge
    tags = models.CharField(max_length=250, blank=True)  # simple CSV
    image = models.ImageField(upload_to='listings/', blank=True, null=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='listings')
    vendor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='listings')
    created_at = models.DateTimeField(auto_now_add=True)
