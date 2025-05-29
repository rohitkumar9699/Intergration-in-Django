from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAdminUser
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.utils import timezone
from .models import *
from .serializers import *
from coupons.models import *
import requests
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import AccessToken
from django.contrib.auth import get_user_model


def get_country(ip):
    if ip == "127.0.0.1":
        return "Localhost" 
    

    try:
        response = requests.get(f"http://ip-api.com/json/{ip}", timeout=3)
        response.raise_for_status()
        data = response.json()
        if data.get("status") == "success":
            return data.get("country", "Unknown")
    except requests.RequestException:
        pass
    
    # Removed IP because it is giving India as IN 

    # try:
    #     response = requests.get(f"https://ipinfo.io/{ip}/json", timeout=3)
    #     response.raise_for_status()
    #     data = response.json()
    #     country = data.get("country")
    #     if country:
    #         return country
    # except requests.RequestException:
    #     pass
    
    
    return "Unknown"


# ✅ 1. Create Ticket
class TicketCreateAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]


    def post(self, request):
        try:
            user = request.user
            order_id = request.data.get('order_id')

            # Check if user_id exists in PruneOrderDetails
            if not PruneOrderDetails.objects.filter(order_by=user, id = order_id).exists():
                return Response({"error": "Wrong user authentication or order ID to raise the ticket "}, status=403)

            
            if Ticket.objects.filter(order_id=order_id, is_active=True).exists():
                return Response({"error": "Only one ticket can be raised at a time"}, status=403)

            ip = request.META.get('REMOTE_ADDR', '127.0.0.1')
            data = request.data.copy()
            data['country'] = get_country(ip)
            print(get_country('103.152.158.66'))
            try:
                order = PruneOrderDetails.objects.get(id=data['order_id'])
            except PruneOrderDetails.DoesNotExist:
                return Response({"error": "Invalid order ID"}, status=status.HTTP_400_BAD_REQUEST)

            data['category'] = order.category  # Automatically copying category
            data['name'] = user.full_name
            serializer = TicketSerializer(data=data)
            if serializer.is_valid():
                serializer.save()
                
                return Response({
                    "data": serializer.data,
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

                    return Response(data)
                except Ticket.DoesNotExist:
                    return Response({"detail": "Ticket not found"}, status=status.HTTP_404_NOT_FOUND)

            tickets = Ticket.objects.all().order_by('-created_at')
            paginator = PageNumberPagination()
            paginator.page_size = 10
            result_page = paginator.paginate_queryset(tickets, request)
            serializer = TicketSerializer(result_page, many=True)

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
                return Response({
                    "message": "Update on Ticket.",
                    "ticket": serializer.data
                }, status=status.HTTP_200_OK)

            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
