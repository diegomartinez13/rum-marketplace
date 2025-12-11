from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from decimal import Decimal
from io import BytesIO
from PIL import Image
from .models import Product, ProductCategory, ProductImage, UserProfile, Conversation, Message


def create_test_image(name="test.png", size=(100, 100), color="red"):
    """Helper function to create a test image file"""
    file = BytesIO()
    image = Image.new("RGB", size, color)
    image.save(file, "PNG")
    file.seek(0)
    return SimpleUploadedFile(name, file.read(), content_type="image/png")


class CreateProductListingTests(TestCase):
    """Tests for the add_product view (product listing creation)"""

    def setUp(self):
        """Set up test data before each test method"""
        self.client = Client()
        
        # Create a test user
        self.user = User.objects.create_user(
            username="seller",
            email="seller@upr.edu",
            password="testpass123",
            first_name="Test",
            last_name="Seller",
        )
        
        # The UserProfile is auto-created via signal, update it
        self.user.profile.is_seller = True
        self.user.profile.pending_email_verification = False
        self.user.profile.save()
        
        # Create a test category
        self.category = ProductCategory.objects.create(
            name="Electronics",
            slug="electronics",
            description="Electronic items",
        )
        
        # URL for adding products
        self.add_product_url = reverse("store_app:add-product")

    def test_add_product_requires_login(self):
        """Test that unauthenticated users are redirected to login"""
        response = self.client.get(self.add_product_url)
        # Should redirect to login page
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url.lower())

    def test_add_product_page_loads_for_authenticated_user(self):
        """Test that the add product page loads for logged-in users"""
        self.client.login(username="seller", password="testpass123")
        response = self.client.get(self.add_product_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "add_product.html")
        # Check that categories are passed to context
        self.assertIn("categories", response.context)

    def test_create_product_success(self):
        """Test successful product creation with valid data"""
        self.client.login(username="seller", password="testpass123")
        
        data = {
            "name": "Notebook",
            "description": "A great notebook for class notes",
            "price": "29.99",
            "category": self.category.id,
            "discount": "",  # No discount
        }
        
        response = self.client.post(self.add_product_url, data, follow=True)
        
        # Should redirect to home on success
        self.assertEqual(response.status_code, 200)
        
        # Product should be created
        self.assertEqual(Product.objects.count(), 1)
        
        product = Product.objects.first()
        self.assertEqual(product.name, "Notebook")
        self.assertEqual(product.description, "A great notebook for class notes")
        self.assertEqual(product.price, Decimal("29.99"))
        self.assertEqual(product.category, self.category)
        self.assertEqual(product.user_vendor, self.user)
        self.assertEqual(product.discount, Decimal("0.00"))

    def test_create_product_with_discount(self):
        """Test product creation with a percentage discount"""
        self.client.login(username="seller", password="testpass123")
        
        data = {
            "name": "Laptop Stand",
            "description": "Ergonomic laptop stand",
            "price": "100.00",
            "category": self.category.id,
            "discount": "20",  # 20% discount
        }
        
        response = self.client.post(self.add_product_url, data, follow=True)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Product.objects.count(), 1)
        
        product = Product.objects.first()
        # Discount is 20% of $100 = $20
        self.assertEqual(product.discount, Decimal("20.00"))
        # Final price should be $80
        self.assertEqual(product.final_price, Decimal("80.00"))

    def test_create_product_with_single_image(self):
        """Test product creation with a single image"""
        self.client.login(username="seller", password="testpass123")
        
        image = create_test_image("product.png")
        
        data = {
            "name": "Headphones",
            "description": "Wireless headphones",
            "price": "49.99",
            "category": self.category.id,
            "discount": "",
        }
        
        response = self.client.post(
            self.add_product_url,
            {**data, "images": image},
            follow=True,
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Product.objects.count(), 1)
        
        product = Product.objects.first()
        # Should have one ProductImage created
        self.assertEqual(product.images.count(), 1)
        # Primary image should also be set (for backward compatibility)
        self.assertIsNotNone(product.image)

    def test_create_product_with_multiple_images(self):
        """Test product creation with multiple images (up to 5)"""
        self.client.login(username="seller", password="testpass123")
        
        images = [create_test_image(f"product{i}.png") for i in range(3)]
        
        data = {
            "name": "Camera",
            "description": "Digital camera",
            "price": "299.99",
            "category": self.category.id,
            "discount": "",
        }
        
        # Use format_suffix to send multiple files with same key
        response = self.client.post(
            self.add_product_url,
            {**data, "images": images},
            follow=True,
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Product.objects.count(), 1)
        
        product = Product.objects.first()
        self.assertEqual(product.images.count(), 3)

    def test_create_product_rejects_more_than_five_images(self):
        """Test that uploading more than 5 images shows an error"""
        self.client.login(username="seller", password="testpass123")
        
        images = [create_test_image(f"product{i}.png") for i in range(6)]
        
        data = {
            "name": "Phone",
            "description": "Smartphone",
            "price": "599.99",
            "category": self.category.id,
            "discount": "",
        }
        
        response = self.client.post(
            self.add_product_url,
            {**data, "images": images},
            follow=True,
        )
        
        # Product should NOT be created
        self.assertEqual(Product.objects.count(), 0)
        # Should show error message
        messages_list = list(response.context.get("messages", []))
        self.assertTrue(
            any("maximum of 5 images" in str(m).lower() for m in messages_list)
        )

    def test_create_product_without_image(self):
        """Test that products can be created without images"""
        self.client.login(username="seller", password="testpass123")
        
        data = {
            "name": "Study Guide",
            "description": "Digital study guide - no images needed",
            "price": "9.99",
            "category": self.category.id,
            "discount": "",
        }
        
        response = self.client.post(self.add_product_url, data, follow=True)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Product.objects.count(), 1)
        
        product = Product.objects.first()
        self.assertIsNone(product.image.name if product.image else None)
        self.assertEqual(product.images.count(), 0)

    def test_create_product_price_exceeds_maximum(self):
        """Test that prices exceeding $99,999.99 are rejected"""
        self.client.login(username="seller", password="testpass123")
        
        data = {
            "name": "Expensive Item",
            "description": "Very expensive",
            "price": "100000.00",  # Exceeds max of $99,999.99
            "category": self.category.id,
            "discount": "",
        }
        
        response = self.client.post(self.add_product_url, data, follow=True)
        
        # Product should NOT be created
        self.assertEqual(Product.objects.count(), 0)
        # Should show error message
        messages_list = list(response.context.get("messages", []))
        self.assertTrue(
            any("cannot exceed" in str(m).lower() for m in messages_list)
        )

    def test_create_product_negative_price(self):
        """Test that negative prices are rejected"""
        self.client.login(username="seller", password="testpass123")
        
        data = {
            "name": "Free Item",
            "description": "Trying to use negative price",
            "price": "-10.00",
            "category": self.category.id,
            "discount": "",
        }
        
        response = self.client.post(self.add_product_url, data, follow=True)
        
        # Product should NOT be created
        self.assertEqual(Product.objects.count(), 0)
        # Should show error message
        messages_list = list(response.context.get("messages", []))
        self.assertTrue(
            any("cannot be negative" in str(m).lower() for m in messages_list)
        )

    def test_create_product_zero_price(self):
        """Test that zero price is allowed (free items)"""
        self.client.login(username="seller", password="testpass123")
        
        data = {
            "name": "Free Item",
            "description": "This item is free",
            "price": "0.00",
            "category": self.category.id,
            "discount": "",
        }
        
        response = self.client.post(self.add_product_url, data, follow=True)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Product.objects.count(), 1)
        
        product = Product.objects.first()
        self.assertEqual(product.price, Decimal("0.00"))

    def test_create_product_maximum_allowed_price(self):
        """Test that the maximum allowed price ($99,999.99) works"""
        self.client.login(username="seller", password="testpass123")
        
        data = {
            "name": "Max Price Item",
            "description": "At maximum price",
            "price": "99999.99",
            "category": self.category.id,
            "discount": "",
        }
        
        response = self.client.post(self.add_product_url, data, follow=True)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Product.objects.count(), 1)
        
        product = Product.objects.first()
        self.assertEqual(product.price, Decimal("99999.99"))

    def test_create_product_invalid_category(self):
        """Test that an invalid category ID returns 404"""
        self.client.login(username="seller", password="testpass123")
        
        data = {
            "name": "Test Product",
            "description": "Test",
            "price": "10.00",
            "category": 99999,  # Non-existent category
            "discount": "",
        }
        
        response = self.client.post(self.add_product_url, data)
        
        # Should return 404 for invalid category
        self.assertEqual(response.status_code, 404)
        self.assertEqual(Product.objects.count(), 0)

    def test_create_product_assigns_current_user_as_vendor(self):
        """Test that the logged-in user is automatically set as the vendor"""
        self.client.login(username="seller", password="testpass123")
        
        # Create another user to ensure correct user is assigned
        other_user = User.objects.create_user(
            username="other", email="other@upr.edu", password="pass123"
        )
        
        data = {
            "name": "My Product",
            "description": "My product description",
            "price": "25.00",
            "category": self.category.id,
            "discount": "",
        }
        
        response = self.client.post(self.add_product_url, data, follow=True)
        
        self.assertEqual(response.status_code, 200)
        product = Product.objects.first()
        
        # Vendor should be the logged-in user, not the other user
        self.assertEqual(product.user_vendor, self.user)
        self.assertNotEqual(product.user_vendor, other_user)

    def test_create_product_sold_out_default_false(self):
        """Test that new products are not sold out by default"""
        self.client.login(username="seller", password="testpass123")
        
        data = {
            "name": "Available Product",
            "description": "This product is available",
            "price": "15.00",
            "category": self.category.id,
            "discount": "",
        }
        
        response = self.client.post(self.add_product_url, data, follow=True)
        
        self.assertEqual(response.status_code, 200)
        product = Product.objects.first()
        self.assertFalse(product.sold_out)

    def test_create_product_redirects_to_home_on_success(self):
        """Test that successful creation redirects to home page"""
        self.client.login(username="seller", password="testpass123")
        
        data = {
            "name": "Test Product",
            "description": "Test",
            "price": "10.00",
            "category": self.category.id,
            "discount": "",
        }
        
        response = self.client.post(self.add_product_url, data)
        
        # Should redirect to home
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(
            response,
            reverse("store_app:home"),
            fetch_redirect_response=False,
        )

    def test_create_product_success_message_displayed(self):
        """Test that a success message is shown after creation"""
        self.client.login(username="seller", password="testpass123")
        
        data = {
            "name": "Test Product",
            "description": "Test",
            "price": "10.00",
            "category": self.category.id,
            "discount": "",
        }
        
        response = self.client.post(self.add_product_url, data, follow=True)
        
        messages_list = list(response.context.get("messages", []))
        self.assertTrue(
            any("success" in str(m).lower() for m in messages_list)
        )


class ProductImageOrderTests(TestCase):
    """Tests for ProductImage ordering"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="seller",
            email="seller@upr.edu",
            password="testpass123",
        )
        self.user.profile.pending_email_verification = False
        self.user.profile.save()
        
        self.category = ProductCategory.objects.create(
            name="Test", slug="test"
        )
        self.add_product_url = reverse("store_app:add-product")

    def test_images_are_ordered_correctly(self):
        """Test that multiple images maintain their upload order"""
        self.client.login(username="seller", password="testpass123")
        
        images = [create_test_image(f"img{i}.png") for i in range(5)]
        
        data = {
            "name": "Multi Image Product",
            "description": "Product with 5 images",
            "price": "50.00",
            "category": self.category.id,
            "discount": "",
        }
        
        response = self.client.post(
            self.add_product_url,
            {**data, "images": images},
            follow=True,
        )
        
        product = Product.objects.first()
        product_images = list(product.images.all())
        
        # Check that images are ordered by their 'order' field
        for i, img in enumerate(product_images):
            self.assertEqual(img.order, i)


class ProductModelTests(TestCase):
    """Tests for the Product model itself"""

    def setUp(self):
        self.user = User.objects.create_user(
            username="seller",
            email="seller@upr.edu",
            password="testpass123",
        )
        self.category = ProductCategory.objects.create(
            name="Books", slug="books"
        )

    def test_product_str_representation(self):
        """Test the string representation of Product"""
        product = Product.objects.create(
            name="Python Textbook",
            price=Decimal("45.00"),
            category=self.category,
            user_vendor=self.user,
        )
        self.assertEqual(str(product), "Python Textbook")

    def test_product_final_price_calculation(self):
        """Test the final_price property"""
        product = Product.objects.create(
            name="Discounted Item",
            price=Decimal("100.00"),
            discount=Decimal("25.00"),
            category=self.category,
            user_vendor=self.user,
        )
        self.assertEqual(product.final_price, Decimal("75.00"))

    def test_product_final_price_no_discount(self):
        """Test final_price when there's no discount"""
        product = Product.objects.create(
            name="Full Price Item",
            price=Decimal("50.00"),
            discount=Decimal("0.00"),
            category=self.category,
            user_vendor=self.user,
        )
        self.assertEqual(product.final_price, Decimal("50.00"))

    def test_product_primary_image_returns_first_product_image(self):
        """Test that primary_image returns the first ProductImage"""
        product = Product.objects.create(
            name="Product with images",
            price=Decimal("30.00"),
            category=self.category,
            user_vendor=self.user,
        )
        
        # Create product images
        img1 = create_test_image("first.png")
        img2 = create_test_image("second.png")
        
        ProductImage.objects.create(product=product, image=img1, order=0)
        ProductImage.objects.create(product=product, image=img2, order=1)
        
        # primary_image should return the first one
        self.assertEqual(product.primary_image, product.images.first().image)

    def test_product_primary_image_fallback_to_image_field(self):
        """Test that primary_image falls back to image field when no ProductImages"""
        img = create_test_image("main.png")
        product = Product.objects.create(
            name="Product with single image",
            price=Decimal("30.00"),
            category=self.category,
            user_vendor=self.user,
            image=img,
        )
        
        # No ProductImage objects, should fall back to image field
        self.assertEqual(product.images.count(), 0)
        self.assertEqual(product.primary_image, product.image)


class ProductCategoryTests(TestCase):
    """Tests for ProductCategory model"""

    def test_category_str_representation(self):
        """Test string representation of category"""
        category = ProductCategory.objects.create(
            name="Clothing", slug="clothing"
        )
        self.assertEqual(str(category), "Clothing")

    def test_category_with_parent(self):
        """Test creating a subcategory with a parent"""
        parent = ProductCategory.objects.create(
            name="Electronics", slug="electronics"
        )
        child = ProductCategory.objects.create(
            name="Phones", slug="phones", parent=parent
        )
        
        self.assertEqual(child.parent, parent)
        self.assertIn(child, parent.children.all())


class DeleteProductListingTests(TestCase):
    """Tests for deleting product listings"""

    def setUp(self):
        self.client = Client()
        
        # Create owner user
        self.owner = User.objects.create_user(
            username="owner",
            email="owner@upr.edu",
            password="testpass123",
        )
        self.owner.profile.pending_email_verification = False
        self.owner.profile.save()
        
        # Create another user (non-owner)
        self.other_user = User.objects.create_user(
            username="other",
            email="other@upr.edu",
            password="testpass123",
        )
        self.other_user.profile.pending_email_verification = False
        self.other_user.profile.save()
        
        # Create category and product
        self.category = ProductCategory.objects.create(
            name="Test", slug="test"
        )
        self.product = Product.objects.create(
            name="Test Product",
            price=Decimal("25.00"),
            category=self.category,
            user_vendor=self.owner,
        )

    def test_delete_product_requires_login(self):
        """Test that unauthenticated users cannot delete products"""
        url = reverse("store_app:delete_product", args=[self.product.id])
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url.lower())
        # Product should still exist
        self.assertEqual(Product.objects.count(), 1)

    def test_delete_product_success_by_owner(self):
        """Test that owner can delete their own product"""
        self.client.login(username="owner", password="testpass123")
        url = reverse("store_app:delete_product", args=[self.product.id])
        
        response = self.client.post(url, follow=True)
        
        self.assertEqual(response.status_code, 200)
        # Product should be deleted
        self.assertEqual(Product.objects.count(), 0)

    def test_delete_product_denied_for_non_owner(self):
        """Test that non-owner cannot delete someone else's product"""
        self.client.login(username="other", password="testpass123")
        url = reverse("store_app:delete_product", args=[self.product.id])
        
        response = self.client.post(url, follow=True)
        
        # Product should still exist
        self.assertEqual(Product.objects.count(), 1)
        # Should show error message
        messages_list = list(response.context.get("messages", []))
        self.assertTrue(
            any("not authorized" in str(m).lower() for m in messages_list)
        )

    def test_delete_nonexistent_product_returns_404(self):
        """Test that deleting a non-existent product returns 404"""
        self.client.login(username="owner", password="testpass123")
        url = reverse("store_app:delete_product", args=[99999])
        
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, 404)


class MessagingSystemTests(TestCase):
    """Tests for the messaging/conversation system"""

    def setUp(self):
        self.client = Client()
        
        # Create two users for messaging
        self.user1 = User.objects.create_user(
            username="user1",
            email="user1@upr.edu",
            password="testpass123",
            first_name="User",
            last_name="One",
        )
        self.user1.profile.pending_email_verification = False
        self.user1.profile.save()
        
        self.user2 = User.objects.create_user(
            username="user2",
            email="user2@upr.edu",
            password="testpass123",
            first_name="User",
            last_name="Two",
        )
        self.user2.profile.pending_email_verification = False
        self.user2.profile.save()
        
        # Create a third user for testing unauthorized access
        self.user3 = User.objects.create_user(
            username="user3",
            email="user3@upr.edu",
            password="testpass123",
        )
        self.user3.profile.pending_email_verification = False
        self.user3.profile.save()

    def test_messages_page_requires_login(self):
        """Test that messages page requires authentication"""
        response = self.client.get(reverse("store_app:messages"))
        
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url.lower())

    def test_messages_page_loads_for_authenticated_user(self):
        """Test that messages page loads for logged-in users"""
        self.client.login(username="user1", password="testpass123")
        response = self.client.get(reverse("store_app:messages"))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "messages.html")

    def test_start_conversation_creates_new_conversation(self):
        """Test starting a new conversation between two users"""
        self.client.login(username="user1", password="testpass123")
        url = reverse("store_app:start_conversation", args=[self.user2.id])
        
        response = self.client.get(url)
        
        # Should redirect to conversation page
        self.assertEqual(response.status_code, 302)
        # Conversation should be created
        self.assertEqual(Conversation.objects.count(), 1)
        
        conversation = Conversation.objects.first()
        self.assertIn(self.user1, conversation.participants.all())
        self.assertIn(self.user2, conversation.participants.all())

    def test_start_conversation_reuses_existing_conversation(self):
        """Test that starting a conversation with same user reuses existing one"""
        self.client.login(username="user1", password="testpass123")
        url = reverse("store_app:start_conversation", args=[self.user2.id])
        
        # Start conversation twice
        self.client.get(url)
        self.client.get(url)
        
        # Should still only have one conversation
        self.assertEqual(Conversation.objects.count(), 1)

    def test_cannot_start_conversation_with_self(self):
        """Test that users cannot message themselves"""
        self.client.login(username="user1", password="testpass123")
        url = reverse("store_app:start_conversation", args=[self.user1.id])
        
        response = self.client.get(url, follow=True)
        
        # Should not create conversation
        self.assertEqual(Conversation.objects.count(), 0)
        # Should show error message
        messages_list = list(response.context.get("messages", []))
        self.assertTrue(
            any("yourself" in str(m).lower() for m in messages_list)
        )

    def test_send_message_in_conversation(self):
        """Test sending a message in a conversation"""
        # Create conversation first
        conversation, _ = Conversation.get_or_create_conversation(self.user1, self.user2)
        
        self.client.login(username="user1", password="testpass123")
        url = reverse("store_app:conversation", args=[conversation.id])
        
        response = self.client.post(url, {"content": "Hello, this is a test message!"}, follow=True)
        
        self.assertEqual(response.status_code, 200)
        # Message should be created
        self.assertEqual(Message.objects.count(), 1)
        
        message = Message.objects.first()
        self.assertEqual(message.content, "Hello, this is a test message!")
        self.assertEqual(message.sender, self.user1)
        self.assertEqual(message.conversation, conversation)

    def test_cannot_send_empty_message(self):
        """Test that empty messages are rejected"""
        conversation, _ = Conversation.get_or_create_conversation(self.user1, self.user2)
        
        self.client.login(username="user1", password="testpass123")
        url = reverse("store_app:conversation", args=[conversation.id])
        
        response = self.client.post(url, {"content": ""}, follow=True)
        
        # No message should be created
        self.assertEqual(Message.objects.count(), 0)

    def test_non_participant_cannot_view_conversation(self):
        """Test that non-participants cannot view a conversation"""
        # Create conversation between user1 and user2
        conversation, _ = Conversation.get_or_create_conversation(self.user1, self.user2)
        
        # Login as user3 (not a participant)
        self.client.login(username="user3", password="testpass123")
        url = reverse("store_app:conversation", args=[conversation.id])
        
        response = self.client.get(url)
        
        # Should redirect away (to messages page)
        self.assertEqual(response.status_code, 302)

    def test_conversation_view_marks_messages_as_read(self):
        """Test that viewing a conversation marks messages as read"""
        conversation, _ = Conversation.get_or_create_conversation(self.user1, self.user2)
        
        # User2 sends a message to user1
        message = Message.objects.create(
            conversation=conversation,
            sender=self.user2,
            content="Hello user1!",
            is_read=False,
        )
        
        # User1 views the conversation
        self.client.login(username="user1", password="testpass123")
        url = reverse("store_app:conversation", args=[conversation.id])
        self.client.get(url)
        
        # Message should now be marked as read
        message.refresh_from_db()
        self.assertTrue(message.is_read)

    def test_unread_messages_count(self):
        """Test the unread messages count API"""
        conversation, _ = Conversation.get_or_create_conversation(self.user1, self.user2)
        
        # User2 sends 3 messages to user1
        for i in range(3):
            Message.objects.create(
                conversation=conversation,
                sender=self.user2,
                content=f"Message {i}",
                is_read=False,
            )
        
        self.client.login(username="user1", password="testpass123")
        response = self.client.get(reverse("store_app:get_unread_messages_count"))
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["unread_count"], 3)


class ConversationModelTests(TestCase):
    """Tests for the Conversation model"""

    def setUp(self):
        self.user1 = User.objects.create_user(
            username="user1", email="user1@upr.edu", password="pass123"
        )
        self.user2 = User.objects.create_user(
            username="user2", email="user2@upr.edu", password="pass123"
        )

    def test_get_or_create_conversation_creates_new(self):
        """Test creating a new conversation via class method"""
        conversation, created = Conversation.get_or_create_conversation(self.user1, self.user2)
        
        self.assertTrue(created)
        self.assertIn(self.user1, conversation.participants.all())
        self.assertIn(self.user2, conversation.participants.all())

    def test_get_or_create_conversation_returns_existing(self):
        """Test that existing conversation is returned"""
        conv1, created1 = Conversation.get_or_create_conversation(self.user1, self.user2)
        conv2, created2 = Conversation.get_or_create_conversation(self.user1, self.user2)
        
        self.assertTrue(created1)
        self.assertFalse(created2)
        self.assertEqual(conv1.id, conv2.id)

    def test_get_other_participant(self):
        """Test getting the other participant in a conversation"""
        conversation, _ = Conversation.get_or_create_conversation(self.user1, self.user2)
        
        other = conversation.get_other_participant(self.user1)
        self.assertEqual(other, self.user2)
        
        other = conversation.get_other_participant(self.user2)
        self.assertEqual(other, self.user1)

    def test_get_latest_message(self):
        """Test getting the latest message in a conversation"""
        conversation, _ = Conversation.get_or_create_conversation(self.user1, self.user2)
        
        # Initially no messages
        self.assertIsNone(conversation.get_latest_message())
        
        # Add messages
        Message.objects.create(conversation=conversation, sender=self.user1, content="First")
        msg2 = Message.objects.create(conversation=conversation, sender=self.user2, content="Second")
        
        # Latest should be the second message
        self.assertEqual(conversation.get_latest_message(), msg2)


class MessageModelTests(TestCase):
    """Tests for the Message model"""

    def setUp(self):
        self.user1 = User.objects.create_user(
            username="user1", email="user1@upr.edu", password="pass123"
        )
        self.user2 = User.objects.create_user(
            username="user2", email="user2@upr.edu", password="pass123"
        )
        self.conversation, _ = Conversation.get_or_create_conversation(self.user1, self.user2)

    def test_message_defaults_to_unread(self):
        """Test that new messages are unread by default"""
        message = Message.objects.create(
            conversation=self.conversation,
            sender=self.user1,
            content="Test message",
        )
        
        self.assertFalse(message.is_read)
        self.assertIsNone(message.read_at)

    def test_mark_as_read(self):
        """Test marking a message as read"""
        message = Message.objects.create(
            conversation=self.conversation,
            sender=self.user1,
            content="Test message",
        )
        
        message.mark_as_read()
        
        self.assertTrue(message.is_read)
        self.assertIsNotNone(message.read_at)

    def test_mark_as_read_only_once(self):
        """Test that marking as read twice doesn't change read_at"""
        message = Message.objects.create(
            conversation=self.conversation,
            sender=self.user1,
            content="Test message",
        )
        
        message.mark_as_read()
        first_read_at = message.read_at
        
        message.mark_as_read()
        
        # read_at should not change
        self.assertEqual(message.read_at, first_read_at)


class AccountCreationTests(TestCase):
    """Tests for user signup/account creation"""

    def setUp(self):
        self.client = Client()
        self.signup_url = reverse("store_app:signup")

    def test_signup_page_loads(self):
        """Test that signup page loads correctly"""
        response = self.client.get(self.signup_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "signup.html")

    def test_signup_success_with_valid_data(self):
        """Test successful account creation"""
        data = {
            "username": "newuser",
            "first_name": "New",
            "last_name": "User",
            "email": "newuser@upr.edu",
            "phone_number": "787-555-1234",
            "password": "SecurePass123!",
            "confirm_password": "SecurePass123!",
            "is_seller": True,
        }
        
        response = self.client.post(self.signup_url, data)
        
        # Should redirect to email verification page
        self.assertEqual(response.status_code, 302)
        
        # User should be created
        self.assertTrue(User.objects.filter(username="newuser").exists())
        
        user = User.objects.get(username="newuser")
        self.assertEqual(user.email, "newuser@upr.edu")
        self.assertTrue(user.profile.is_seller)
        self.assertTrue(user.profile.pending_email_verification)

    def test_signup_requires_upr_email(self):
        """Test that only @upr.edu emails are allowed"""
        data = {
            "username": "testuser",
            "first_name": "Test",
            "last_name": "User",
            "email": "testuser@gmail.com",  # Not a UPR email
            "password": "SecurePass123!",
            "confirm_password": "SecurePass123!",
        }
        
        response = self.client.post(self.signup_url, data)
        
        # Should return form with errors (400 status)
        self.assertEqual(response.status_code, 400)
        # User should NOT be created
        self.assertFalse(User.objects.filter(username="testuser").exists())

    def test_signup_passwords_must_match(self):
        """Test that password confirmation must match"""
        data = {
            "username": "testuser",
            "first_name": "Test",
            "last_name": "User",
            "email": "testuser@upr.edu",
            "password": "SecurePass123!",
            "confirm_password": "DifferentPass456!",
        }
        
        response = self.client.post(self.signup_url, data)
        
        self.assertEqual(response.status_code, 400)
        self.assertFalse(User.objects.filter(username="testuser").exists())

    def test_signup_duplicate_username_rejected(self):
        """Test that duplicate usernames are rejected"""
        # Create existing user
        User.objects.create_user(
            username="existinguser",
            email="existing@upr.edu",
            password="pass123",
        )
        
        data = {
            "username": "existinguser",  # Already taken
            "first_name": "New",
            "last_name": "User",
            "email": "newuser@upr.edu",
            "password": "SecurePass123!",
            "confirm_password": "SecurePass123!",
        }
        
        response = self.client.post(self.signup_url, data)
        
        self.assertEqual(response.status_code, 400)
        # Should still only have one user with this username
        self.assertEqual(User.objects.filter(username="existinguser").count(), 1)
