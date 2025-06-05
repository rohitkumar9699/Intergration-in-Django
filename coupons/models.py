from django.db import models
from django.conf import settings

class Coupon(models.Model):
    PROMOTION_TYPE_CHOICES = [
        ('Cash back', 'Cash back'),
        ('Discount', 'Discount'),
    ]


    DISCOUNT_TYPE_CHOICES = [
        ('Flat', 'Flat'),
        ('Percentage', 'Percentage'),
    ]

    CURRENCY_CHOICES = [
        ('INR', 'INR'),
        ('USD', 'USD'),
        ('EUR', 'EUR'),
    ]

    PAYMENT_OPTION_CHOICES = [
        ('Unified Payments', 'Unified Payments'),
        ('Credit Card', 'Credit Card'),
        ('Debit Card', 'Debit Card'),
        ('Net Banking', 'Net Banking'),
        ('UPI', 'UPI'),
    ]
    coupon_code = models.CharField(max_length=20, unique=True, db_index=True)
    promotion_name = models.CharField(max_length=255)
    short_description = models.TextField(blank=True, null=True)
    terms_and_conditions = models.TextField(blank=True, null=True)

    promotion_type = models.CharField(max_length=20, choices=PROMOTION_TYPE_CHOICES)
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPE_CHOICES)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    currency = models.CharField(max_length=10, choices=CURRENCY_CHOICES, default='INR')

    payment_option = models.CharField(max_length=50, choices=PAYMENT_OPTION_CHOICES, blank=True, null=True)
    bank_or_card_name = models.CharField(max_length=100, blank=True, null=True)

    valid_from = models.DateField(blank=True, null=True)
    valid_until = models.DateField(blank=True, null=True)

    max_total_usage = models.PositiveIntegerField(default=0, help_text="0 for infinite usage")
    max_usage_per_user = models.PositiveIntegerField(default=0, help_text="0 for infinite usage per user")

    min_order_value = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    max_discount_value = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    registered_by = models.EmailField(null=True, blank=True)
    token_used_count = models.PositiveIntegerField(default=0, help_text="Number of times the coupon has been used")
    # can_be_only_used_by_ids = models.multiplefield

    
    def __str__(self):
        return self.promotion_name
    
    

class CouponUsage(models.Model):
    coupon_code = models.ForeignKey(Coupon, on_delete=models.CASCADE, db_index=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, db_index=True)
    last_used_at = models.DateTimeField(auto_now=True)
    usage_count = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.user} - {self.coupon_code.coupon_code} - {self.usage_count}"




class PruneOrderDetails(models.Model):
    ORDER_STATUS_CHOICES = [
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('pending', 'Pending'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('Unified Payments', 'Unified Payments'),
        ('Credit Card', 'Credit Card'),
        ('Debit Card', 'Debit Card'),
        ('Net Banking', 'Net Banking'),
        ('UPI', 'UPI'),
        ('Any', 'Any')
    ]

    order_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders')
    product_name = models.CharField(max_length=255, default='Indian Sim')
    product_id = models.CharField(max_length=100, default='PROD000')
    quantity = models.PositiveIntegerField(default=1)
    price_per_item = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    coupon_code = models.ForeignKey(Coupon, on_delete=models.CASCADE, blank=True, null=True)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    procesing_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    final_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    order_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default='pending')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='cod')
    payment_status = models.BooleanField(default=False)
    category = models.CharField(null= True)

    access_token = None

    def set_access_token(self, token):
        self.access_token = token

    def get_access_token(self):
        return self.access_token

