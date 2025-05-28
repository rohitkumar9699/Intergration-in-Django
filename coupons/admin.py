from django.contrib import admin
from .models import Coupon, CouponUsage, PruneOrderDetails

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'coupon_code', 'promotion_name', 'short_description',
        'promotion_type', 'discount_type', 'discount_value',
        'currency', 'payment_option', 'bank_or_card_name',
        'valid_from', 'valid_until', 'max_total_usage',
        'token_used_count', 'max_usage_per_user',
        'min_order_value', 'max_discount_value',
        'is_active', 'registered_by', 'created_at', 'updated_at'
    )
    list_filter = (
        'promotion_type', 'discount_type', 'currency',
        'payment_option', 'is_active', 'valid_from', 'valid_until', 'created_at'
    )
    search_fields = ('coupon_code', 'promotion_name', 'bank_or_card_name', 'registered_by')
    ordering = ('-created_at',)


@admin.register(CouponUsage)
class CouponUsageAdmin(admin.ModelAdmin):
    list_display = ('id', 'coupon_code', 'user', 'usage_count', 'last_used_at')
    list_filter = ('last_used_at', 'coupon_code')
    search_fields = ('coupon_code__coupon_code', 'user__email', 'user__username')


@admin.register(PruneOrderDetails)
class PruneOrderDetailsAdmin(admin.ModelAdmin):
    list_display = [
        field.name for field in PruneOrderDetails._meta.get_fields()
        if not field.many_to_many and not field.one_to_many
    ]
    list_filter = (
        'status', 'payment_method', 'payment_status', 'order_date',
    )
    search_fields = (
        'order_by__email', 'order_by__username', 'product_name', 'product_id'
    )
    ordering = ('-order_date',)
