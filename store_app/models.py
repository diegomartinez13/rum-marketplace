from django.db import models
from decimal import Decimal
from django.utils import timezone
from django.contrib.auth.hashers import make_password
from django.core.validators import RegexValidator
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserProfile(models.Model):
    # Link to Django's built-in User (for authentication)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")

    # Your custom e-commerce fields
    phone_number = models.CharField(max_length=20, blank=True)
    is_seller = models.BooleanField(default=False)
    provides_service = models.BooleanField(default=False)
    profile_picture = models.ImageField(upload_to="uploads/profile_pictures/", blank=True, null=True)
    description = models.TextField(max_length=200, blank=True, null=True)

    # Email verification (for your app, separate from Django auth)
    pending_email_verification = models.BooleanField(default=True)
    email_token = models.CharField(max_length=64, blank=True, null=True, db_index=True)
    email_token_expires_at = models.DateTimeField(blank=True, null=True)
    verified_at = models.DateTimeField(blank=True, null=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.email} Profile"

    def mark_verified(self):
        self.pending_email_verification = False
        self.verified_at = timezone.now()
        self.email_token = None
        self.email_token_expires_at = None
        self.save()


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
    image = models.ImageField(upload_to="uploads/products/", blank=True, null=True)  # Keep for backward compatibility
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

    @property
    def final_price(self):
        return self.price - self.discount
    
    @property
    def primary_image(self):
        """Get the primary image (first ProductImage or fallback to image field)"""
        first_image = self.images.first()
        if first_image:
            return first_image.image
        return self.image

    def __str__(self):
        return self.name


class ProductImage(models.Model):
    """Model to store multiple images for a product (up to 5)"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="uploads/products/")
    order = models.IntegerField(default=0, help_text="Order of image display (0 = primary)")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['order', 'created_at']
        verbose_name = "Product Image"
        verbose_name_plural = "Product Images"
    
    def __str__(self):
        return f"Image {self.order} for {self.product.name}"


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

    @property
    def final_price(self):
        return self.price - self.discount

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
    discounts_applied = models.DecimalField(
        default=Decimal("0.00"), decimal_places=2, max_digits=10
    )
    total_amount = models.DecimalField(
        default=Decimal("0.00"), decimal_places=2, max_digits=10
    )

    def __str__(self):
        return f"Purchase {self} by {self.user} on {self.purchase_date}"

    class Meta:
        verbose_name_plural = "Purchase Histories"


class Conversation(models.Model):
    """Represents a conversation between two users"""
    participants = models.ManyToManyField(User, related_name='conversations')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Optional: Link to a product or service if the conversation started from a listing
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True, related_name='conversations')
    service = models.ForeignKey(Service, on_delete=models.SET_NULL, null=True, blank=True, related_name='conversations')
    
    class Meta:
        ordering = ['-updated_at']
    
    def __str__(self):
        participant_names = [p.get_full_name() or p.username for p in self.participants.all()]
        return f"Conversation between {', '.join(participant_names)}"
    
    def get_other_participant(self, user):
        """Get the other participant in the conversation"""
        return self.participants.exclude(id=user.id).first()
    
    def get_latest_message(self):
        """Get the latest message in this conversation"""
        return self.messages.last()
    
    @classmethod
    def get_or_create_conversation(cls, user1, user2):
        """Get existing conversation between two users or create a new one"""
        # Check if conversation already exists
        existing = cls.objects.filter(participants=user1).filter(participants=user2).first()
        if existing:
            return existing, False
        
        # Create new conversation
        conversation = cls.objects.create()
        conversation.participants.add(user1, user2)
        return conversation, True


class Message(models.Model):
    """Represents a message within a conversation"""
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"Message from {self.sender.get_full_name() or self.sender.username} in {self.conversation}"
    
    def mark_as_read(self):
        """Mark the message as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save()


# Signal to automatically create profile when User is created
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, "profile"):
        instance.profile.save()
