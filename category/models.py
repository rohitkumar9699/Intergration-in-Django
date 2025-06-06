from django.db import models

class Category(models.Model):
    category_name = models.CharField(max_length=100, unique=True)
    category_url_name = models.SlugField(max_length=100, unique=True)

    def __str__(self):
        return self.category_name
