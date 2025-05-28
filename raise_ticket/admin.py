from django.contrib import admin
from .models import Ticket


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'get_order_id', 'resolved_by', 'category', 'created_at',
        'resolved_at', 'is_active', 'ip_address'
    ]
    search_fields = ['order_id__user_email', 'order_id__user_mobile']
    list_filter = ['category', 'is_active']

    def get_order_id(self, obj):
        return obj.order_id.id
    get_order_id.short_description = 'Order ID'  