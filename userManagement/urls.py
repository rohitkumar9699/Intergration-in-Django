from django.urls import path
from .views import *

urlpatterns = [
    path('signup/', SignupView.as_view(), name='signup'),
    path('verify-email/', VerifyEmailView.as_view(), name='verify-email'),
    path('verify-otp/', VerifyOTPView.as_view(), name='verify-otp'),
    path('resend-verification/', ResendVerificationView.as_view(), name='resend-verification'),
    path('verification-status/', VerificationStatusView.as_view(), name='verification-status'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('password-reset/',PasswordResetRequestView.as_view(), name='password-reset'),
    path('password-otp-verify/',PasswordVerifyOtpView.as_view(),name="verify-password-otp"),
    path('password-reset-confirm/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
    path('token-refresh/', RefreshTokenView.as_view(), name='token_refresh'), 
    path('update-user/', UserProfileUpdateView.as_view(), name='user-list'),
    path('get-user/', UserDetailView.as_view(), name='user-list'),
    path('delete-address/', DeleteUserAddressAPIView.as_view(), name='delete-user-address'),
    path('resend-otp/',ReSendOtpView.as_view(), name='resend-otp'),
    path('save-address/', UserAddressSave.as_view()),
    path('wallet/', WalletBalanceAPIView.as_view(), name='wallet-balance'),
    path('wallet-history/', WalletHistoryAPIView.as_view(), name='wallet-history'),

]
