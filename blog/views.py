from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import *
from .serializers import *
from django.db.models import F

class BlogDetailView(APIView):
    def get(self, request, blog_url_name):
        try:
            blog = BlogPost.objects.get(blog_url_name=blog_url_name)
            
            BlogPost.objects.filter(pk=blog.pk).update(views=F('views') + 1)
        
            serializer = BlogPostSerializer(blog)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except BlogPost.DoesNotExist:
            return Response(
                {"error": f"Blog with slug '{blog_url_name}' not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": "Internal server error", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class BlogListView(APIView):
    def get(self, request):
        try:
            category = request.query_params.get('category', None)

            if category:
                # Sanitize and lowercase the input
                category_cleaned = category.strip().lower()

                blogs = BlogPost.objects.filter(category__category_name__iexact=category_cleaned)

                if not blogs.exists():
                    return Response({"message": "No blogs found in this category."}, status=status.HTTP_200_OK)

                serializer = BlogPostSerializer(blogs, many=True)
                return Response(serializer.data, status=status.HTTP_200_OK)

            else:
                blogs = BlogPost.objects.all()
                if not blogs.exists():
                    return Response({"message": "No blogs available."}, status=status.HTTP_200_OK)

                serializer = BlogPostSerializer(blogs, many=True)
                return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": "Something went wrong", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
