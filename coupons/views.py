from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.utils import timezone
from decimal import Decimal
from .models import *
from .serializers import *
from .utils import apply_coupon_discount
from userManagement.models import CustomUser, Wallet


class RegisterCouponView(APIView):
    # permission_classes = [permissions.IsAuthenticated]  # Require authentication

    def post(self, request):
        user = request.user
        print(user.communication_email)

        # Only superusers can register coupons
        if not user.is_superuser:
            return Response({"error": "Only superusers can register coupons."}, status=status.HTTP_403_FORBIDDEN)

        data = request.data
        coupon_code = data.get('coupon_code')

        # Check required field coupon_code
        if not coupon_code:
            return Response({"error": "coupon_code is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Check if coupon_code already exists
        if Coupon.objects.filter(coupon_code=coupon_code).exists():
            return Response({"error": "This coupon code already exists."}, status=status.HTTP_400_BAD_REQUEST)

        # Add registered_by to data from authenticated user's email
        data['registered_by'] = user.communication_email

        serializer = CouponSerializer(data=data)
        if serializer.is_valid():
            serializer.save()  # registered_by will be saved from data
            return Response({
                "message": "Coupon registered successfully.",
                "data": serializer.data
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class ApplyCouponView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    

    
    def post(self, request):
        user = request.user
        code = request.data.get('coupon_code')
        amount = request.data.get('amount')
        payment_option = request.data.get('payment_option')
        bank_or_card_name = request.data.get('bank_or_card_name')

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


class PlaceOrderView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        # auth_header = request.headers.get('Authorization')
        # print(auth_header)
        try:
            # Extract order details
            product_name = request.data.get('product_name', 'Indian Sim')
            product_id = request.data.get('product_id', 'PROD000')
            quantity = int(request.data.get('quantity', 1))
            category = request.data.get('category', None)
            price_per_item = Decimal(request.data.get('price_per_item', '0.00'))
            payment_method = request.data.get('payment_method', 'Unified Payments')
            total_amount = price_per_item * quantity

            # print("*****************", category)

            # Defaults
            coupon_code_str = request.data.get('coupon_code', None)
            discount = Decimal('0.00')
            final_amount = total_amount
            coupon_instance = None
            coupon_result = None
            # Apply coupon if provided
            if coupon_code_str:
                coupon_result = apply_coupon_discount(
                request=request,
                user=user,
                code=coupon_code_str,
                category=category,
                amount=total_amount,
                payment_option=payment_method
            )

            # ❗ Handle failure
            if coupon_result.status_code != 200:
                return coupon_result  # Already a Response object with error

            # ❗ Safe dictionary access
            discount = Decimal(str(coupon_result.data.get("discount_applied", "0.00")))
            final_amount = Decimal(str(coupon_result.data.get("final_amount", total_amount)))
            coupon_instance = Coupon.objects.filter(coupon_code=coupon_code_str).first()


            # Create order
            order = PruneOrderDetails.objects.create(
                order_by=user,
                product_name=product_name,
                product_id=product_id,
                category = category,
                quantity=quantity,
                price_per_item=price_per_item,
                total_amount=total_amount,
                coupon_code=coupon_instance,
                # coupon_code=coupon_code_str,
                discount=discount,
                final_amount=final_amount,
                payment_method=payment_method,
                payment_status=False,
                status='pending'
            )

            serializer = PruneOrderDetailsSerializer(order)
            return Response({
                "message": coupon_result.data["message"],
                "order": serializer.data
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DeliverStatusView(APIView):

    authentication_classes = [JWTAuthentication]

    # def post(self, request):
    def patch(self, request):
        
        user = request.user
        if not user.is_superuser:
            return Response(
                {"error": "Only superusers can update delivery status."},
                status=status.HTTP_403_FORBIDDEN
            )
        order_id = request.data.get('id')
        new_status = request.data.get('status')

        if not order_id or not new_status:
            return Response({'error': 'Order ID and status are required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            order = PruneOrderDetails.objects.get(id=order_id)
            # ✅ Set token BEFORE saving, so signal can access it
            auth_header = request.headers.get('Authorization')
            order.set_access_token(auth_header)

            order.status = new_status
            order.save()
        except PruneOrderDetails.DoesNotExist:
            return Response({"error": "Order not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



        return Response({'message': 'Order status updated successfully.'}, status=status.HTTP_200_OK)
    

class AddMoneyToWalletView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    # def post(self, request):
    def patch(self, request):
    
        user  = request.user
        print(user)
        print(user.username)

        wallet_username = user.username
        reward_amount = request.data.get('wallet_balance')

        # access_token = request.headers.get('Authorization')
        # print(access_token)

        if not wallet_username:
            return Response({"error": "Missing wallet_username"}, status=status.HTTP_400_BAD_REQUEST)

        if not reward_amount:
            return Response({"error": "Missing wallet_balance"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            reward_amount = Decimal(reward_amount)
        except:
            return Response({"error": "Invalid wallet_balance"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = CustomUser.objects.get(username=wallet_username)
        except CustomUser.DoesNotExist:
            return Response({"error": "User does not exist"}, status=status.HTTP_404_NOT_FOUND)

        wallet = Wallet.objects.get(user=user)
        prevoius_balance = wallet.amount 
        wallet.amount = wallet.amount + float(reward_amount)
        wallet.save()

        return Response({
            "message": "Money added to wallet successfully",
            "prevoius_balance" : str(prevoius_balance),
            "reward_amount" : reward_amount,
            "new_balance": str(wallet.amount)
        }, status=status.HTTP_200_OK)


