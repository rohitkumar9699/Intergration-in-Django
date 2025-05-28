from django.db import models
from django.utils import timezone

CATEGORY_CHOICES = [
    ('india_sim', 'India SIM'),
    ('e_sim', 'E-SIM'),
    ('bills', 'Bills'),
]

from coupons.models import *  # Assuming these models are defined in the same app

class Ticket(models.Model):
    
    order_id = models.ForeignKey(PruneOrderDetails, on_delete=models.CASCADE)
    # order_id = models.CharField(unique=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    resolution_message = models.TextField(null=True, blank=True) # remove
    issue_description = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.EmailField(null=True, blank=True)

    def __str__(self):
        return f"Ticket #{self.id}"
