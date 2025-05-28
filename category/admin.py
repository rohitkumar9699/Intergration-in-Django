from django.contrib import admin
from .models import Category

class CategoryAdmin(admin.ModelAdmin):
    # Show these fields in the list view
    list_display = ('category_name', 'category_url_name')
    list_display_links = ('category_name',)
    search_fields = ('category_name', 'category_url_name')
    ordering = ('category_name',)
admin.site.register(Category, CategoryAdmin)
