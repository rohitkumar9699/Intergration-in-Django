from django.contrib import admin
from .models import BlogPost

@admin.register(BlogPost)
class BlogAdmin(admin.ModelAdmin):
    list_display = [field.name for field in BlogPost._meta.fields]
    
    # Filters
    list_filter = (
        'category', 'author', 'published_date', 'updated_date',      
    )
    
    search_fields = ('title', 'content', 'author')

    ordering = ('-published_date',)
