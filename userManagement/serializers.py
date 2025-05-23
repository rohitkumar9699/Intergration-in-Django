from rest_framework import serializers

from django.contrib.sites.shortcuts import get_current_site
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from datetime import datetime
from .models import *
from .utils import OTPManager

import re
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
# serializers.py
from django.contrib.auth import get_user_model
from .models import email_otp



User = get_user_model()


class SignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6,required=False)
    full_name = serializers.CharField(required=True)
    #country_code = serializers.CharField(required=False, default='+91')  # Only needed for mobile
    
    class Meta:
        model = CustomUser
        fields = ['username', 'password', 'full_name']
    
    def validate_username(self, value):
        """Validate username as either email or mobile"""
        value = value.lower().strip()
        print(value)
        
        # Check if email
        try:
            validate_email(value)
            return value
        except ValidationError:
            pass
        
        # Check if mobile (10 digits)
        if re.match(r'^[0-9]{10}$', value):
            return value
        
        raise serializers.ValidationError(
            "Username must be a valid email or 10-digit mobile number"
        )
    
    def validate(self, data):
        username = data['username']
        password = data['password']
        # Check if user exists
        if CustomUser.objects.filter(username=username).exists():
            raise serializers.ValidationError({
                'username': 'User with this username already exists'
            })
        

            # Check if it's an email
        is_email = '@' in username

        # If it's an email, password is mandatory
        if is_email and not password: # type: ignore
            raise serializers.ValidationError({
                'password': 'Password is required for email sign-up'
            })

        
        return data
    
    def create(self, validated_data,password=None):
        existing_user = True
        request = self.context.get('request')
        username = validated_data['username']
        password = validated_data.get('password')  # use .get() to avoid KeyError

        try: 
            existing_username=CustomUser.objects.filter(communication_email=username).exists() 
            if existing_username:
                return CustomUser.objects.get(communication_email=username)
        
            existing_username_mobile=CustomUser.objects.filter(communication_mobile=username).exists()
            if existing_username_mobile:
                return CustomUser.objects.get(communication_mobile=username)
        except Exception as e:
            return ('User Not Exists with this Account!!')

        # if not existing_username or not existing_username_mobile:
        #     user = CustomUser.objects.create_user(
        #         username=username,
        #         password = password
        #     )
        # user.full_name = validated_data['full_name']
        # Handle verification
        # Email verification
        if '@' in username and password :
            self.send_verification_email(username, request)

           
        if '@' in username and not password:  # Email verification
            self.send_verification_email(username, request)

        else:  # Mobile verification
            print('lldldldlslssssss---------')
            OTPManager.send_otp(
                country_code=validated_data.get('country_code', '+91'),
                phone_number=username
            )
        
        return username
    

   
    
    def send_verification_email(self, username, request):
        """Send email verification link and OTP."""
        try:
           
            domain = get_current_site(request).domain
            print(domain)
           

            # link = reverse('verify-email')
            # print('link',link)
            # verify_url = f"http://{domain}{link}"
            # print(verify_url)

            
            
            # Generate OTP
            otp = OTPManager.generate_otp()
            email_otps = email_otp()
            email_otps.otp = otp
            email_otps.email = username
            email_otps.otp_status = True
            email_otps.created_date = datetime.now()
            email_otps.save()

            # Email content
            subject = "Verify Your Email"
            message = f"""
            Welcome to Prune! Please verify your email address.
            
            Your OTP: {otp}
            
            This OTP is valid for 24 hours.
            """
            OTPManager.send_email(
                subject,
                message,
                [username],
            )
            
            return {"success": "Verification email sent"}
        except Exception as e:
            return {"error": str(e)}
        


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True)

    def validate_username(self, value):
        value = value.lower().strip()
        
        # Check if email
        try:
            validate_email(value)
            return {'type': 'email', 'value': value}
        except ValidationError:
            pass
        
        # Check if mobile (10 digits)
        if re.match(r'^[0-9]{10}$', value):
            return {'type': 'mobile', 'value': value}
        
        raise serializers.ValidationError(
            "Username must be a valid email or 10-digit mobile number"
        )
        

class PasswordResetRequestSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)

    def validate_username(self, value):
        value = value.lower().strip()

        # Try email validation
        try:
            validate_email(value)
            return value
        except ValidationError:
            pass  # Not an email, check mobile next

        # Try mobile validation
        mobile_regex = r'^\+?1?\d{9,15}$'  # You can customize this regex
        if re.match(mobile_regex, value):
            return value

        # If neither match
        raise serializers.ValidationError("Please enter a valid email address or mobile number")

class PasswordResetConfirmSerializer(serializers.Serializer):
    # token = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=8)
    confirm_password = serializers.CharField(required=True, min_length=8)

    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError("Passwords don't match")
        return data
    


class PasswordResetConfirmView(APIView):
    def post(self, request, uidb64, token):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            uid = uidb64
            user = CustomUser.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
            return Response(
                {"error": "Invalid user"},
                status=status.HTTP_400_BAD_REQUEST
            )

        token_generator = PasswordResetTokenGenerator()
        if not token_generator.check_token(user, token):
            return Response(
                {"error": "Invalid or expired token"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Set new password
        user.set_password(serializer.validated_data['new_password'])
        user.save()

        return Response(
            {"message": "Password reset successfully"},
            status=status.HTTP_200_OK
        )
    


class UserSerializer(serializers.ModelSerializer):
    avatar = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = [
            'id',
            'username',
            'full_name',
            'communication_email',
            'communication_mobile',
            'avatar',
            'country',
            'referral_code',
            'created_at',
        ]
        read_only_fields = ['id', 'username','created_at']

    def get_avatar(self, obj):
        if obj.avatar:
            return self.context['request'].build_absolute_uri(obj.avatar.url)
        return None
    

class UserAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserAddress
        fields = [
            'id', 'user', 'phone_no', 'house_no', 'locality', 'request_for',
            'lat', 'lng', 'landmark', 'district', 'state', 'country',
            'pincode', 'full_address', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'is_active', 'created_at', 'updated_at', 'user']

    # Add required field validation
    def validate(self, data):
        required_fields = [
            'phone_no', 'house_no', 'locality', 'landmark',
            'district', 'state', 'country', 'pincode', 'full_address'
        ]
        missing = [field for field in required_fields if not data.get(field)]
        if missing:
            raise serializers.ValidationError(f"Missing fields: {', '.join(missing)}")
        return data

class UserAddressRetrunSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserAddress
        fields = '__all__'


class WalletHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = WalletHistory
        fields = [
            'id',
            'user',
            'amount',
            'transaction_type',
            'description',
            'additional_details',
            'created_at',
        ]
        read_only_fields = ['id', 'user', 'created_at']

