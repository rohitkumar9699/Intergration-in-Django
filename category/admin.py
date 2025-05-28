from django.contrib import admin
from .models import Category

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['category_name', 'category_url_name']
    list_filter = ['category_name']  # ✅ Dropdown filter for all categories
    search_fields = ['category_name']  # ✅ Typing search
