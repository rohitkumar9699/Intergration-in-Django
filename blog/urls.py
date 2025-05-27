from django.urls import path
from .views import *

urlpatterns = [
    path('api/blogs/', BlogListView.as_view(), name='blog-list'),   # note trailing slash
    path('api/blog/<slug:blog_url_name>/', BlogDetailView.as_view(), name='blog-detail'),
    # path('api/blog/<int:id>/', BlogDetailView.as_view(), name='blog-detail'),  # trailing slash
]
