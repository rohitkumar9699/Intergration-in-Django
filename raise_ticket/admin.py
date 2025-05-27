from django.contrib import admin
from .models import Ticket

@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'order_id', 'resolved_by', 'category', 'created_at',
        'resolved_at', 'is_active', 'ip_address'
    ]
    search_fields = ['order_id__name', 'order_id__mobile']
    list_filter = ['category', 'is_active']
