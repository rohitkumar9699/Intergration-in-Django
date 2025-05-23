# utils.py
from decimal import Decimal
from django.utils import timezone
from .models import *
from userManagement.models import *

def apply_coupon_discount(user, coupon_code, amount, payment_option=None, bank_or_card_name=None):
    """
    Apply coupon discount logic.
    Returns a dict with keys:
    - 'error': error message if any
    - 'discount_applied': Decimal
    - 'final_amount': Decimal
    - 'coupon': Coupon object if valid else None
    """
    try:
        amount = Decimal(amount)
        if amount <= 0:
            return {"error": "Invalid or zero amount format"}
    except:
        return {"error": "Invalid amount"}

    try:
        coupon = Coupon.objects.get(coupon_code=coupon_code, is_active=True)
    except Coupon.DoesNotExist:
        return {"error": "Invalid or inactive coupon"}

    today = timezone.now().date()
    if coupon.valid_until and coupon.valid_until < today:
        coupon.is_active = False
        coupon.save()
        return {"error": "Coupon has expired"}

    if coupon.valid_from and today < coupon.valid_from:
        return {"error": "Coupon is not yet valid"}

    if amount < coupon.min_order_value:
        return {"error": f"Minimum order value should be ₹{coupon.min_order_value}"}

    # Check usage limits
    if coupon.max_total_usage != 0 and coupon.token_used_count >= coupon.max_total_usage:
        return {"error": "Coupon usage limit reached"}

    user_usage = CouponUsage.objects.filter(coupon_code=coupon, user=user).first()
    if user_usage and coupon.max_usage_per_user != 0 and user_usage.usage_count >= coupon.max_usage_per_user:
        return {"error": "You have already used this coupon the maximum number of times."}

    if "welcome" in coupon.promotion_name.lower():
        if CouponUsage.objects.filter(user=user).exists():
            return {"error": "Welcome coupon can only be used by new users"}

    if coupon.payment_option and payment_option and coupon.payment_option != payment_option:
        return {"error": f"This coupon is valid only for {coupon.payment_option}"}

    if coupon.bank_or_card_name and bank_or_card_name and coupon.bank_or_card_name != bank_or_card_name:
        return {"error": f"This coupon is valid only for {coupon.bank_or_card_name}"}

    # Calculate discount
    if coupon.discount_type == "Flat":
        discount = min(coupon.discount_value, coupon.max_discount_value, amount)
    else:  # Percentage
        percentage_discount = (amount * coupon.discount_value / Decimal('100')).quantize(Decimal('0.01'))
        discount = min(percentage_discount, coupon.max_discount_value, amount)

    final_amount = (amount - discount).quantize(Decimal('0.01'))

    # You can handle wallet deduction or coupon usage updates here or in the view after confirming order

    return {
        "discount_applied": discount,
        "final_amount": final_amount,
        "coupon": coupon
    }
