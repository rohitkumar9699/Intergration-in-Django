from django.db.models.signals import post_save
from django.dispatch import receiver
from decimal import Decimal
from userManagement.models import Wallet
from .models import PruneOrderDetails
from django.db import transaction
import json
import requests
from .serializers import PruneOrderDetailsSerializer
from userManagement.serializers import UserSerializer
import requests


@receiver(post_save, sender=PruneOrderDetails)
def give_cashback_on_order_delivery(sender, instance, created, **kwargs):
    if created:
        return
    
    token = instance.get_access_token()
    # print(token)
    headers = {'Authorization': token}

    if ( 
        instance.status.lower() == "delivered"
    ):
        
        serializer = PruneOrderDetailsSerializer(instance)
        order_data = serializer.data  # dict, JSON serializable
        user = instance.order_by
        serializer1 = UserSerializer(user)
        user_data = serializer1.data

        merged_data = {**order_data, **user_data}
        try:
            response = requests.post("http://localhost:8001/create-card/", json= merged_data, headers=headers)
            print({
                "status": "success",
                "reward_api_status": response.status_code,
                "response_data": response.json()
            })

            #security
            # print("before")
            # print(instance.get_access_token())
            instance.set_access_token(None)
            # print("after")
            # print(instance.get_access_token())
            

        except requests.exceptions.RequestException as e:
            print({
                "status": "error",
                "message": "Reward service unreachable",
                "error": str(e)
            })

        coupon = instance.coupon_code

        if coupon.promotion_type == "Cash back":
            try:
                wallet = Wallet.objects.get(user=instance.order_by)

                # Convert both to Decimal safely
                cashback = Decimal(str(instance.discount)).quantize(Decimal("0.01"))
                wallet.amount = Decimal(str(wallet.amount)).quantize(Decimal("0.01"))

                old_balance = wallet.amount
                wallet.amount += cashback
                wallet.save(update_fields=["amount"])

                def mark_payment_done():
                    PruneOrderDetails.objects.filter(pk=instance.pk).update(payment_status=True)

                transaction.on_commit(mark_payment_done)

                print(f"✅ Cashback of ₹{cashback} added to user {instance.order_by}.")
                print(f"Wallet: ₹{old_balance} → ₹{wallet.amount}")

            except Wallet.DoesNotExist:
                print(f"⚠️ Wallet not found for user {instance.order_by}.")
