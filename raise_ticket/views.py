from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAdminUser
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.utils import timezone
from django.db.models import Q
from .models import Ticket
from .serializers import TicketSerializer
from coupons.models import *

import requests


def get_country(ip):
    if ip == "127.0.0.1":
        return "Localhost"
    response = requests.get(f"https://ipinfo.io/{ip}/json")
    return response.json().get("country", "Unknown")

print(get_country("103.27.9.190"))



class TicketCreateAPIView(APIView):
    def post(self, request):
        ip = request.META.get('REMOTE_ADDR')
        data = request.data.copy()
        data['ip_address'] = ip

        country = get_country(ip)
        
        data['country'] = country

        # Validate and get order instance
        try:
            order = PruneOrderDetails.objects.get(id=data['order_id'])
        except PruneOrderDetails.DoesNotExist:
            return Response({"error": "Invalid order ID"}, status=status.HTTP_400_BAD_REQUEST)

        # Set category from order
        data['category'] = order.category  # Ensure this is a string value like "india_sim"

        serializer = TicketSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "data": serializer.data,
                "message": "Ticket raised successfully"
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ✅ 2. View Ticket(s) with Pagination
class TicketView(APIView):
    def get(self, request, id=None):
        if id:
            try:
                ticket = Ticket.objects.get(id=id)
                serializer = TicketSerializer(ticket)
                return Response(serializer.data)
            except Ticket.DoesNotExist:
                return Response({"detail": "Ticket not found"}, status=status.HTTP_404_NOT_FOUND)

        tickets = Ticket.objects.all().order_by('-created_at')

        paginator = PageNumberPagination()
        paginator.page_size = 5
        result_page = paginator.paginate_queryset(tickets, request)
        serializer = TicketSerializer(result_page, many=True)
        return paginator.get_paginated_response(serializer.data)


# ✅ 3. Resolve a Ticket (Admin Only)
class TicketResolveAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdminUser]

    def post(self, request, id):
        user = request.user

        try:
            ticket = Ticket.objects.get(id=id)
        except Ticket.DoesNotExist:
            return Response({"detail": "Ticket not found"}, status=status.HTTP_404_NOT_FOUND)

        # If already resolved
        if not ticket.is_active:
            return Response({"detail": "Ticket is already resolved."}, status=status.HTTP_400_BAD_REQUEST)

        # Check expiry
        expiry_date = ticket.created_at + timezone.timedelta(days=7)
        now = timezone.now()

        if now > expiry_date:
            ticket.is_active = False
            ticket.save(update_fields=['is_active'])
            return Response({
                "detail": "Ticket expired and cannot be resolved. It is now inactive."
            }, status=status.HTTP_400_BAD_REQUEST)

        resolution_message = request.data.get('resolution_message', '').strip()
        if not resolution_message:
            return Response({
                "resolution_message": ["This field is required to resolve the ticket."]
            }, status=status.HTTP_400_BAD_REQUEST)

        data = {
            'resolution_message': resolution_message,
            'resolved_at': now,
            'is_active': False,
            'resolved_by': user.communication_email  # ✅ This should match your model field
        }
        serializer = TicketSerializer(ticket, data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            response_data = serializer.data.copy()
            response_data.pop('ip_address', None)
            return Response({
                "message": "Update on Ticket.",
                "ticket": response_data
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
