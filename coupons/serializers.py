from rest_framework import serializers
from .models import Coupon

class CouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = '__all__'

    def validate_coupon_code(self, value):
        if Coupon.objects.filter(coupon_code=value).exists():
            raise serializers.ValidationError("Coupon code already exists.")
        return value

from rest_framework import serializers
from .models import PruneOrderDetails

class PruneOrderDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = PruneOrderDetails
        fields = '__all__'


class PruneOrderDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = PruneOrderDetails
        fields = '__all__'
        read_only_fields = ['order_by', 'total_amount', 'final_amount', 'order_date', 'payment_status']
    