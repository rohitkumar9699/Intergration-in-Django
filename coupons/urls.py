from django.urls import path
from .views import *

urlpatterns = [
    path('register-coupon/', RegisterCouponView.as_view(), name='register-coupon'),
    path('apply-coupon/', ApplyCouponView.as_view(), name='apply-coupon'),
   
    path('place-order/', PlaceOrderView.as_view(), name='place_order'),
    path('add-money-to-wallet/',AddMoneyToWalletView.as_view(), name = 'add-money-to-wallet'),
]
