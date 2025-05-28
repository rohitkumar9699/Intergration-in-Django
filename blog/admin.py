from django.contrib import admin
from .models import BlogPost

@admin.register(BlogPost)
class BlogAdmin(admin.ModelAdmin):
    list_display = [field.name for field in BlogPost._meta.fields if field.name != 'id']
    list_display_links = ('blog_title',)
    list_filter = ('category', 'author')
    search_fields = ('blog_title', 'content', 'author')
