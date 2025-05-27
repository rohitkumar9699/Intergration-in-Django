from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.core.paginator import Paginator
from django.utils import timezone
from django.db.models import Q

from .models import Ticket
from .serializers import TicketSerializer


class TicketCreateAPIView(APIView):
    def post(self, request):
        ip = request.META.get('REMOTE_ADDR')
        data = request.data.copy()
        data['ip_address'] = ip
        serializer = TicketSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(
            {
                "data": serializer.data,
                "message": "Ticket raised successfully"
            }, 
    status=status.HTTP_201_CREATED
)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

class TicketView(APIView):
    def get(self, request, id=None):
        search_query = request.GET.get('search', '')
        page_number = request.GET.get('page', 1)

        if id:
            try:
                ticket = Ticket.objects.get(id=id)
                serializer = TicketSerializer(ticket)
                return Response(serializer.data)
            except Ticket.DoesNotExist:
                return Response({"detail": "Ticket not found"}, status=status.HTTP_404_NOT_FOUND)

        tickets = Ticket.objects.all().order_by('-created_at')
        if search_query:
            tickets = tickets.filter(Q(order_id__icontains=search_query))

        paginator = Paginator(tickets, 10)
        page_obj = paginator.get_page(page_number)
        serializer = TicketSerializer(page_obj, many=True)

        return Response({
            'count': paginator.count,
            'num_pages': paginator.num_pages,
            'current_page': page_obj.number,
            'results': serializer.data
        })


from rest_framework.permissions import IsAdminUser
from rest_framework_simplejwt.authentication import JWTAuthentication


class TicketResolveAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdminUser]

    def post(self, request, id):
        try:
            ticket = Ticket.objects.get(id=id)
        except Ticket.DoesNotExist:
            return Response({"detail": "Ticket not found"}, status=status.HTTP_404_NOT_FOUND)

        # Check if ticket is already resolved (inactive)
        if not ticket.is_active:
            return Response({
                "detail": "Ticket is already resolved."
            }, status=status.HTTP_400_BAD_REQUEST)

        expiry_date = ticket.created_at + timezone.timedelta(days=7)
        now = timezone.now()

        if now > expiry_date:
            if ticket.is_active:
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
            'resolved_by_email': request.user.communication_email  # added field
        }

        serializer = TicketSerializer(ticket, data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)