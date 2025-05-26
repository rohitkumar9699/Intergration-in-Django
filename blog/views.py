from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import *
from .serializers import *


class BlogDetailView(APIView):
    def get(self, request, id):
        try:
            blog = BlogPost.objects.get(id=id)
            serializer = BlogPostSerializer(blog)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except BlogPost.DoesNotExist:
            return Response({"error": "Blog not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(
                {"error": "Something went wrong", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class BlogListView(APIView):
    def get(self, request):
        try:
            category = request.query_params.get('category', None)

            if category:
                # Sanitize and lowercase the input
                category_cleaned = category.strip().lower()

                # Case-insensitive category matching using iexact
                blogs = BlogPost.objects.filter(category__iexact=category_cleaned)

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
