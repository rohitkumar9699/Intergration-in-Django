from django.db import models
from ckeditor.fields import RichTextField
from category.models import *



class BlogPost(models.Model):
    blog_title = models.CharField(max_length=255)
    blog_url_name = models.SlugField(max_length=255, unique=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    author = models.CharField(max_length=100, blank=True, null=True)
    content = RichTextField()
    blog_image = models.ImageField(upload_to='blog_images/', blank=True, null=True)
    views = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.blog_title
