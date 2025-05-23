from django.urls import path
from .views import RegisterCouponView , ApplyCouponView, PlaceOrderView

urlpatterns = [
    path('register-coupon/', RegisterCouponView.as_view(), name='register-coupon'),
    path('apply-coupon/', ApplyCouponView.as_view(), name='apply-coupon'),
    # path('orders/', PruneOrderDetailView.as_view(), name='order-detail'),
    path('place-order/', PlaceOrderView.as_view(), name='place_order'),
]
