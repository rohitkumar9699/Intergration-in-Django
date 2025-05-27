from django.urls import path
from .views import TicketView, TicketCreateAPIView, TicketResolveAPIView

urlpatterns = [
    path('tickets/', TicketView.as_view(), name='ticket-list'),                      # GET: all tickets
    path('tickets/<int:id>/', TicketView.as_view(), name='ticket-detail'),           # GET: specific ticket
    path('tickets/create/', TicketCreateAPIView.as_view(), name='ticket-create'),    # POST: create new ticket
    path('tickets/resolve/<int:id>/', TicketResolveAPIView.as_view(), name='ticket-resolve'),  # PUT: resolve
]
