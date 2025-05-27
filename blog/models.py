from django.db import models
from ckeditor.fields import RichTextField



# Predefined categories based on Prune's blog
CATEGORY_CHOICES = [
    ("Travel", "Travel"),
    ("Latest Gadgets", "Latest Gadgets"),
    ("Mobile Phones & Cool Tricks", "Mobile Phones & Cool Tricks"),
    ("Latest Tech News", "Latest Tech News"),
    ("Trending", "Trending"),
    ("Latest Games", "Latest Games"),
    ("Reviews", "Reviews"),
    ("Tech News", "Tech News"),
    ("Forex", "Forex"),
    ("News", "News"),
]

class BlogPost(models.Model):
    title = models.CharField(max_length=255)
    blog_url_name = models.SlugField(max_length=255, unique=True)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    author = models.CharField(max_length=100, blank=True, null=True)
    published_date = models.DateField( auto_now_add=True)
    updated_date = models.DateField( auto_now=True)
    # content = models.TextField()
    content = RichTextField()
    featured_image = models.ImageField(upload_to='blog_images/', blank=True, null=True)
    views = models.PositiveIntegerField(default=0)
    likes = models.PositiveIntegerField(default=0)
    dislikes = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.title
