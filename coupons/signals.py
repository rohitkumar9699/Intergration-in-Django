from django.db.models.signals import post_save
from django.dispatch import receiver
from decimal import Decimal
from userManagement.models import Wallet
from .models import PruneOrderDetails
from django.db import transaction


@receiver(post_save, sender=PruneOrderDetails)
def give_cashback_on_order_delivery(sender, instance, created, **kwargs):
    if created:
        return

    if (
        instance.status.lower() == "delivered"
        and instance.coupon_code
        and instance.discount > 0
        and not instance.payment_status
    ):
        coupon = instance.coupon_code

        if coupon.promotion_type == "Cash back":
            try:
                wallet = Wallet.objects.get(user=instance.order_id)

                # Convert both to Decimal safely
                cashback = Decimal(str(instance.discount)).quantize(Decimal("0.01"))
                wallet.amount = Decimal(str(wallet.amount)).quantize(Decimal("0.01"))

                old_balance = wallet.amount
                wallet.amount += cashback
                wallet.save(update_fields=["amount"])

                def mark_payment_done():
                    PruneOrderDetails.objects.filter(pk=instance.pk).update(payment_status=True)

                transaction.on_commit(mark_payment_done)

                print(f"✅ Cashback of ₹{cashback} added to user {instance.order_id}.")
                print(f"Wallet: ₹{old_balance} → ₹{wallet.amount}")

            except Wallet.DoesNotExist:
                print(f"⚠️ Wallet not found for user {instance.order_id}.")
