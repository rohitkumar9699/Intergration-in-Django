from django.contrib import admin
from .models import Coupon, CouponUsage, PruneOrderDetails

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'coupon_code',
        'promotion_name',
        'short_description',
        'terms_and_conditions',
        'promotion_type',
        # 'promotion_available',
        'discount_type',
        'discount_value',
        'currency',
        'payment_option',
        'bank_or_card_name',
        'valid_from',
        'valid_until',
        'max_total_usage',
        'token_used_count',
        'max_usage_per_user',
        'min_order_value',
        'max_discount_value',
        'is_active',
        'registered_by',
        'created_at',
        'updated_at',
        

    )
  
@admin.register(CouponUsage)
class CouponUsageAdmin(admin.ModelAdmin):
    list_display = ('id', 'coupon_code', 'user', 'usage_count', 'last_used_at')


from django.contrib import admin
from .models import PruneOrderDetails

@admin.register(PruneOrderDetails)
class PruneOrderDetailsAdmin(admin.ModelAdmin):
    list_display = [field.name for field in PruneOrderDetails._meta.get_fields() if not field.many_to_many and not field.one_to_many]
