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
from coupons.models import PruneOrderDetails
import requests


def get_country(ip):
    if ip == "127.0.0.1":
        return "Localhost"
    try:
        response = requests.get(f"https://ipapi.co/{ip}/country_name/", timeout=3)
        return response.text.strip()

    except requests.RequestException:
        return "Unknown"


# ✅ 1. Create Ticket
class TicketCreateAPIView(APIView):
    def post(self, request):
        try:
            ip = request.META.get('REMOTE_ADDR', '127.0.0.1')
            data = request.data.copy()
            data['ip_address'] = ip
            data['country'] = get_country(ip)

            try:
                order = PruneOrderDetails.objects.get(id=data['order_id'])
            except PruneOrderDetails.DoesNotExist:
                return Response({"error": "Invalid order ID"}, status=status.HTTP_400_BAD_REQUEST)

            data['category'] = order.category  # Automatically copying category

            serializer = TicketSerializer(data=data)
            if serializer.is_valid():
                serializer.save()
                response_data = serializer.data.copy()
                response_data.pop('ip_address', None)
                return Response({
                    "data": response_data,
                    "message": "Ticket raised successfully"
                }, status=status.HTTP_201_CREATED)

            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ✅ 2. View Tickets (All or by ID)
class TicketView(APIView):
    def get(self, request, id=None):
        try:
            if id:
                try:
                    ticket = Ticket.objects.get(id=id)
                    serializer = TicketSerializer(ticket)
                    data = serializer.data
                    data.pop('ip_address', None)
                    return Response(data)
                except Ticket.DoesNotExist:
                    return Response({"detail": "Ticket not found"}, status=status.HTTP_404_NOT_FOUND)

            tickets = Ticket.objects.all().order_by('-created_at')
            paginator = PageNumberPagination()
            paginator.page_size = 5
            result_page = paginator.paginate_queryset(tickets, request)
            serializer = TicketSerializer(result_page, many=True)

            for ticket in serializer.data:
                ticket.pop('ip_address', None)

            return paginator.get_paginated_response(serializer.data)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ✅ 3. Resolve Ticket (Admin Only)
class TicketResolveAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdminUser]

    def post(self, request, id):
        try:
            try:
                ticket = Ticket.objects.get(id=id)
            except Ticket.DoesNotExist:
                return Response({"detail": "Ticket not found"}, status=status.HTTP_404_NOT_FOUND)

            if not ticket.is_active:
                return Response({"detail": "Ticket is already resolved."}, status=status.HTTP_400_BAD_REQUEST)

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
                'resolved_by': request.user.communication_email
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

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
