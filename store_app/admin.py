from django.contrib import admin
from .models import (
    UserProfile,
    ProductCategory,
    Product,
    ProductImage,
    ServiceCategory,
    Service,
    ProductOrder,
    ServiceRequest,
    Business,
    BusinessCategory,
    Inventory,
    StockedProduct,
    StockedService,
    Review,
    Cart,
    PurchaseHistory,
    Conversation,
    Message,
    SellerRating,
)


# Register your models here.
@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "is_active", "created_at"]
    search_fields = ["name", "slug"]
    list_filter = ["is_active", "created_at"]
    readonly_fields = ["created_at"]


@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "is_active", "created_at"]
    search_fields = ["name", "slug"]
    list_filter = ["is_active", "created_at"]
    readonly_fields = ["created_at"]


admin.site.register(UserProfile)
admin.site.register(Product)
admin.site.register(ProductImage)
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
admin.site.register(SellerRating)


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ['id', 'get_participants', 'product', 'service', 'created_at', 'updated_at', 'message_count']
    list_filter = ['created_at', 'updated_at', 'product', 'service']
    search_fields = ['participants__username', 'participants__email', 'product__name', 'service__name']
    readonly_fields = ['created_at', 'updated_at']
    filter_horizontal = ['participants']
    
    def get_participants(self, obj):
        return ', '.join([p.get_full_name() or p.username for p in obj.participants.all()])
    get_participants.short_description = 'Participants'
    
    def message_count(self, obj):
        return obj.messages.count()
    message_count.short_description = 'Messages'


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'conversation', 'sender', 'content_preview', 'product', 'service', 'is_read', 'created_at']
    list_filter = ['is_read', 'created_at', 'read_at', 'product', 'service']
    search_fields = ['content', 'sender__username', 'sender__email', 'conversation__participants__username']
    readonly_fields = ['created_at', 'read_at']
    date_hierarchy = 'created_at'
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content'


admin.site.site_header = "Rum Marketplace Admin"
admin.site.site_title = "Rum Marketplace Admin Portal"
admin.site.index_title = "Welcome to Rum Marketplace Admin Portal"
