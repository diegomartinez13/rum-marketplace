from django.contrib import admin
from .models import Category, Listing

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    search_fields = ("name",)

@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = ("title","price","category","vendor","created_at","exchange")
    list_filter = ("category","exchange","created_at")
    search_fields = ("title","description","tags")
