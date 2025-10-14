from django.db import models
from decimal import Decimal
from django.utils import timezone
from django.contrib.auth.hashers import make_password
from django.core.validators import RegexValidator


# NOTE: For production, prefer a proper auth User. This is your current custom table.
class User(models.Model):
    # existing fields ...
    first_name     = models.CharField(max_length=50)
    last_name      = models.CharField(max_length=100)
    email          = models.EmailField(max_length=100, unique=True)
    username       = models.CharField(max_length=150, unique=True)
    password       = models.CharField(max_length=128)  # hashed only
    phone_number   = models.CharField(max_length=20, blank=True)
    is_seller      = models.BooleanField(default=False)
    provides_service = models.BooleanField(default=False)
    is_admin       = models.BooleanField(default=False)

    # NEW: email verification state
    pendingemail   = models.BooleanField(default=True)      # gate access
    email_token    = models.CharField(max_length=64, blank=True, null=True, db_index=True)
    email_token_expires_at = models.DateTimeField(blank=True, null=True)
    verified_at    = models.DateTimeField(blank=True, null=True)

    def mark_verified(self):
        self.pendingemail = False
        self.verified_at = timezone.now()
        self.email_token = None
        self.email_token_expires_at = None
        self.save(update_fields=["pendingemail","verified_at","email_token","email_token_expires_at"])

    def set_password_raw(self, raw):
        self.password = make_password(raw)

class ProductCategory(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True)
    description = models.TextField(max_length=250, default="", blank=True, null=True)
    image = models.ImageField(
        upload_to="uploads/categories_images/", blank=True, null=True
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        related_name="children",
        null=True,
        blank=True,
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Product Categories"


class Product(models.Model):
    name = models.CharField(max_length=50)
    price = models.DecimalField(default=Decimal("0.00"), decimal_places=2, max_digits=6)
    category = models.ForeignKey(
        ProductCategory, on_delete=models.CASCADE, related_name="products"
    )
    description = models.TextField(max_length=250, default="", blank=True, null=True)
    image = models.ImageField(upload_to="uploads/products/")
    discount = models.DecimalField(
        default=Decimal("0.00"), decimal_places=2, max_digits=6
    )
    business_vendor = models.ForeignKey(
        "Business",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="products",
    )
    user_vendor = models.ForeignKey(
        User, on_delete=models.CASCADE, null=True, blank=True, related_name="products"
    )

    def __str__(self):
        return self.name


class ServiceCategory(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True)
    description = models.TextField(max_length=250, default="", blank=True, null=True)
    image = models.ImageField(
        upload_to="uploads/categories_images/", blank=True, null=True
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        related_name="children",
        null=True,
        blank=True,
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Service Categories"


class Service(models.Model):
    name = models.CharField(max_length=50)
    price = models.DecimalField(default=Decimal("0.00"), decimal_places=2, max_digits=6)
    category = models.ForeignKey(
        ServiceCategory, on_delete=models.CASCADE, related_name="services"
    )
    description = models.TextField(max_length=250, default="", blank=True, null=True)
    image = models.ImageField(upload_to="uploads/services/")
    discount = models.DecimalField(
        default=Decimal("0.00"), decimal_places=2, max_digits=6
    )
    business_provider = models.ForeignKey(
        "Business",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="services",
    )
    user_provider = models.ForeignKey(
        User, on_delete=models.CASCADE, null=True, blank=True, related_name="services"
    )

    def __str__(self):
        return self.name


class ProductOrder(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    address = models.CharField(max_length=100, default="", blank=True, null=True)
    phone = models.CharField(max_length=20, default="", blank=True, null=True)
    date = models.DateField(auto_now_add=True)
    status = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.product.name} ordered by {self.user}"


class ServiceRequest(models.Model):
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date_of_request = models.DateField(auto_now_add=True)
    time_of_request = models.TimeField(auto_now_add=True)
    date_for_service = models.DateField(null=True, blank=True)
    time_for_service = models.TimeField(null=True, blank=True)
    status = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.service} requested by {self.user}"

    class Meta:
        verbose_name_plural = "Service Requests"


class Business(models.Model):
    business_category = models.CharField(max_length=50)
    business_name = models.CharField(max_length=100)
    business_email = models.EmailField(max_length=100)
    business_phone = models.CharField(max_length=20)
    business_owner = models.ForeignKey(User, on_delete=models.CASCADE)
    business_location = models.CharField(max_length=100)
    business_description = models.TextField(
        max_length=250, default="", blank=True, null=True
    )
    business_logo = models.ImageField(upload_to="uploads/businesses/logos/")

    def __str__(self):
        return self.business_name

    class Meta:
        verbose_name_plural = "Businesses"


class BusinessCategory(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Business Categories"


class Inventory(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE)

    def __str__(self):
        return f"Inventory of {self.business.business_name}"

    class Meta:
        verbose_name_plural = "Inventories"


class StockedProduct(models.Model):
    inventory = models.ForeignKey(Inventory, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=0)
    restock_date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.quantity} of {self.product.name} in {self.inventory.business.business_name}"

    class Meta:
        verbose_name_plural = "Stocked Products"


class StockedService(models.Model):
    inventory = models.ForeignKey(Inventory, on_delete=models.CASCADE)
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    availability = models.BooleanField(default=True)
    last_updated = models.DateField(auto_now=True)

    def __str__(self):
        return f"{self.service.name} in {self.inventory.business.business_name}"

    class Meta:
        verbose_name_plural = "Stocked Services"


class Review(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, null=True, blank=True
    )
    service = models.ForeignKey(
        Service, on_delete=models.CASCADE, null=True, blank=True
    )
    rating = models.IntegerField(default=5)
    comment = models.TextField(max_length=250, default="", blank=True, null=True)
    date = models.DateField(auto_now_add=True)

    def __str__(self):
        target = (
            self.product.name
            if self.product
            else self.service.name if self.service else "Unknown"
        )
        return f"Review for {target}"


class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateField(auto_now_add=True)
    last_updated = models.DateField(auto_now=True)
    products_orders = models.ManyToManyField(ProductOrder, blank=True)
    services_requests = models.ManyToManyField(ServiceRequest, blank=True)
    subtotal = models.DecimalField(
        default=Decimal("0.00"), decimal_places=2, max_digits=10
    )

    def __str__(self):
        return f"Cart of {self.user} as of {self.last_updated}"


class PurchaseHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE)
    purchase_date = models.DateField(auto_now_add=True)
    discounts_applied = models.DecimalField(default=Decimal('0.00'), decimal_places=2, max_digits=10)
    total_amount = models.DecimalField(default=Decimal('0.00'), decimal_places=2, max_digits=10)
    def __str__(self): return f"Purchase {self.id} by {self.user.id} on {self.purchase_date}"
    class Meta: verbose_name_plural = "Purchase Histories"
