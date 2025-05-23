# utils.py
from decimal import Decimal
from django.utils import timezone
from .models import *
from userManagement.models import *
from rest_framework.response import Response
from rest_framework import status
from django.http import HttpResponse


def apply_coupon_discount(request, user, code, amount, payment_option=None, bank_or_card_name=None):
    payment_option = payment_option
    bank_or_card_name = bank_or_card_name
    user = request.user

    if not code or not amount:
            return Response({"error": "coupon_code and amount are required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        amount = Decimal(amount)
        if amount <= 0:
            raise ValueError
    except:
        return Response({"error": "Invalid or zero amount format"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        coupon = Coupon.objects.get(coupon_code=code, is_active=True)
    except Coupon.DoesNotExist:
        return Response({"error": "Invalid or inactive coupon"}, status=status.HTTP_400_BAD_REQUEST)

    today = timezone.now().date()
    if coupon.valid_until < today:
        coupon.is_active = False
        coupon.save()

    if coupon.valid_from and today < coupon.valid_from:
        return Response({"error": "Coupon is not yet valid"}, status=status.HTTP_400_BAD_REQUEST)
    if coupon.valid_until and today > coupon.valid_until:
        return Response({"error": "Coupon has expired"}, status=status.HTTP_400_BAD_REQUEST)


    if amount < coupon.min_order_value:
        return Response({
            "error": f"Minimum order value should be ₹{coupon.min_order_value}"
        }, status=status.HTTP_400_BAD_REQUEST)


    coupon_usage = Coupon.objects.get(coupon_code=code) 

    if coupon.max_total_usage != 0 and coupon_usage.token_used_count >= coupon.max_total_usage:
        return Response({"error": "Coupon usage limit reached"}, status=status.HTTP_400_BAD_REQUEST)

    user_usage = CouponUsage.objects.filter(coupon_code=coupon, user=user).first()
    if user_usage and coupon.max_usage_per_user != 0 and user_usage.usage_count >= coupon.max_usage_per_user:
        return Response({"error": "You have already used this coupon the maximum number of times."},
                        status=status.HTTP_400_BAD_REQUEST)


    if "welcome" in coupon.promotion_name.lower():
        user_coupon_history = CouponUsage.objects.filter(user=user).count()
        if user_coupon_history > 0:
            return Response({"error": "Welcome coupon can only be used by new users"}, status=status.HTTP_400_BAD_REQUEST)

    if coupon.payment_option and payment_option and coupon.payment_option != payment_option:
        return Response({"error": f"This coupon is valid only for {coupon.payment_option}"}, status=status.HTTP_400_BAD_REQUEST)

    if coupon.bank_or_card_name and bank_or_card_name and coupon.bank_or_card_name != bank_or_card_name:
        return Response({"error": f"This coupon is valid only for {coupon.bank_or_card_name}"}, status=status.HTTP_400_BAD_REQUEST)

    # ✅ Discount Calculation (Flat or Percentage)
    if coupon.discount_type == "Flat":
        discount = min(coupon.discount_value, coupon.max_discount_value, amount)
    else:  # Percentage
        percentage_discount = (amount * coupon.discount_value / Decimal('100')).quantize(Decimal('0.01'))
        discount = min(percentage_discount, coupon.max_discount_value, amount)

    final_amount = (amount - discount).quantize(Decimal('0.01'))


    if coupon.promotion_type == "Cash back":

        # ✅ Wallet balance validation
        # get_wallet = Wallet.objects.get(user=request.user)
        # print("this is my wallet ---->", get_wallet)
        # print("this is my wallet amount ---->", get_wallet.amount)
        get_wallet = Wallet.objects.get(user=request.user)

        # wallet_before = getattr(user, 'wallet_balance', Decimal('0.00'))
        wallet_before = Decimal(get_wallet.amount)

        if wallet_before < amount:
            return Response({"error": "Insufficient wallet balance"}, status=status.HTTP_400_BAD_REQUEST)
        # ✅ Deduct from wallet and save

        wallet_after = wallet_before - amount
        user.wallet_balance = wallet_after
        user.save()

        OrderDetails = PruneOrderDetails.objects.get(user=request.user)
        OrderDetails.number_of_orders = OrderDetails.number_of_orders + 1
        OrderDetails.save()
        
        # ✅ Save coupon usage
        user_usage = CouponUsage.objects.filter(coupon_code=coupon, user=user)
        if user_usage.exists():
            user_usage = user_usage.first()
            user_usage.usage_count += 1
            user_usage.last_used_at = timezone.now()
            user_usage.save()
        else:
            user_usage = CouponUsage.objects.create(coupon_code=coupon, user=user)
            user_usage.usage_count = 1
            user_usage.last_used_at = timezone.now()
            user_usage.save()

        if  coupon_usage.token_used_count+1>= coupon_usage.max_total_usage:
            coupon_usage.is_active = False
            coupon_usage.save()
        # ✅ Update coupon usage count
        coupon_usage.token_used_count += 1
        coupon_usage.save()

        # ✅ Return response
        return Response({
        "coupon_applied": coupon.coupon_code,
        "promotion_name": coupon.promotion_name,
        "promotion_type": coupon.promotion_type,
        "discount_type": coupon.discount_type,
        "currency": coupon.currency,
        "original_amount": str(amount),
        "discount_applied": str(discount),
        "final_amount": str(final_amount),
        "wallet_balance_before": str(wallet_before),
        "wallet_balance_after": str(wallet_after),
        "message": "This coupon is applied And Refund Will be Backed to Wallet within 3 Days",
        }, status=status.HTTP_200_OK)

    # ✅ Wallet balance validation
    # get_wallet = Wallet.objects.get(user=request.user)
    # print("this is my wallet ---->", get_wallet)
    # print("this is my wallet amount ---->", get_wallet.amount)
    get_wallet = Wallet.objects.get(user=request.user)

    # wallet_before = getattr(user, 'wallet_balance', Decimal('0.00'))
    wallet_before = Decimal(get_wallet.amount)


    
    print(wallet_before)
    if wallet_before < final_amount:
        return Response({"error": "Insufficient wallet balance"}, status=status.HTTP_400_BAD_REQUEST)

    # ✅ Deduct from wallet and save
    wallet_after = wallet_before - final_amount
    user.wallet_balance = wallet_after
    # user.number_of_orders = user.number_of_orders + 1
    user.save()

    OrderDetails = PruneOrderDetails.objects.get(user=request.user)
    OrderDetails.number_of_orders = OrderDetails.number_of_orders + 1
    OrderDetails.save()

    # ✅ Save coupon usage
    user_usage = CouponUsage.objects.filter(coupon_code=coupon, user=user)
    if user_usage.exists():
        user_usage = user_usage.first()
        user_usage.usage_count += 1
        user_usage.last_used_at = timezone.now()
        user_usage.save()
    else:
        user_usage = CouponUsage.objects.create(coupon_code=coupon, user=user)
        user_usage.usage_count = 1
        user_usage.last_used_at = timezone.now()
        user_usage.save()
    
    if  coupon_usage.token_used_count+1>= coupon_usage.max_total_usage:
        coupon_usage.is_active = False
        coupon_usage.save()
    # ✅ Update coupon usage count
    coupon_usage.token_used_count += 1
    coupon_usage.save()


    return Response({
        "coupon_applied": coupon.coupon_code,
        "promotion_name": coupon.promotion_name,
        "promotion_type": coupon.promotion_type,
        "discount_type": coupon.discount_type,
        "currency": coupon.currency,
        "original_amount": str(amount),
        "discount_applied": str(discount),
        "final_amount": str(final_amount),
        "wallet_balance_before": str(wallet_before),
        "wallet_balance_after": str(wallet_after),
        "message": "Coupon successfully applied and amount deducted."
    }, status=status.HTTP_200_OK)