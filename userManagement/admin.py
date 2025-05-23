from django.contrib import admin
from .models import *
# from .models import CustomUser,UserAddress,Prune_Old_User,Wallet
# admin.site.register(CustomUser)
admin.site.register(UserAddress)
# admin.site.register(Prune_Old_User)

admin.site.register(Cart)
@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'full_name', 'communication_email', 'country', 'is_active', 'created_at')
    search_fields = ('username', 'communication_email', 'full_name')
    list_filter = ('gender', 'country', 'is_active', 'created_at')
    ordering = ('-created_at',)


@admin.register(Prune_Old_User)
class PruneOldUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'created_at')
    list_filter = ('created_at',)

@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'is_active', 'created_at')
    search_fields = ('user__username',)
    list_filter = ('is_active', 'created_at')


@admin.register(mobile_otp)
class MobileOtpAdmin(admin.ModelAdmin):
    list_display = [field.name for field in mobile_otp._meta.fields]

@admin.register(email_otp)
class EmailOtpAdmin(admin.ModelAdmin):
    list_display = [field.name for field in email_otp._meta.fields]