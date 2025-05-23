import math
import random
import re
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import AccessToken,RefreshToken
from .models import email_otp
from django.core.mail import send_mail
from .models import *
# from deviceManagement.models import Device
from userManagement.utils import OTPManager
from datetime import timedelta
from django.utils import timezone

from django.contrib.auth.tokens import PasswordResetTokenGenerator
from .serializers import *
from django.contrib.auth import authenticate
from .utils import OTPManager
# from prune.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.exceptions import TokenError
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.contrib.auth.hashers import make_password
from django.db.models import Q
from rest_framework import generics, permissions
from django.db import transaction
from rest_framework.exceptions import NotFound
from django.http import Http404, JsonResponse



CustomUser = get_user_model()


class SignupView(APIView):
    """
    Handle user registration with email/mobile verification
    """
    def post(self, request):
        full_name = request.data.get('full_name')
        username = request.data.get('username')
        password = request.data.get('password')

        
        missing_fields = []
        if not full_name:
            missing_fields.append("full_name")
        if not username:
            missing_fields.append("username")
        if not password:
            missing_fields.append("password")

        if missing_fields:
            verb = "is" if len(missing_fields) == 1 else "are"
            return Response(
                {'status':False,"message": f"{', '.join(missing_fields)} {verb} required. "},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if CustomUser.objects.filter(username=username).exists():
            return Response({"status":False,"message":"User Already Exists!!!!"},status=status.HTTP_404_NOT_FOUND)
        

        if len(password) <= 5:
            return Response({'status':False,'message':'password length atleast six'})
        
        if len(full_name) < 3 :
            return Response({'status':False,'message':'full name length atleast three'})
        serializer = SignupSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            user = serializer.save()
            response_data = {
                'status': True,
                'message': 'OTP Sent Successfully.',
            }
            return Response(response_data, status=status.HTTP_200_OK)
        else:
            return Response(
                {'status': False, 'message': 'Validation failed', 'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )



class ReSendOtpView(APIView):
    """
    Handle user registration with email/mobile verification
    """
    def post(self, request):
        username = request.data.get('username')

        if CustomUser.objects.filter(username = username).exists():
            missing_fields = []
            
            if not username:
                missing_fields.append("username")
        

            if missing_fields:
                verb = "is" if len(missing_fields) == 1 else "are"
                return Response(
                    {'status':False,"message": f"{', '.join(missing_fields)} {verb} required. "},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if '@' in username :
                SignupSerializer.send_verification_email(self,username, request)

            else:  # Mobile verification
                OTPManager.send_otp(
                    country_code='+91',
                    phone_number=username
                )
            return Response({"message":"otp send successfully","status":True},status=status.HTTP_200_OK)
        else:
            return Response({"message":"User with this account doesnot exists!!!","status":False},status=status.HTTP_404_NOT_FOUND)

class ResendVerificationView(APIView):
    def post(self, request):
        username = request.data.get('username')
        
        if not username:
            return Response(
                {'message': 'Username is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = CustomUser.objects.get(username=username)
            
            if user.is_active:
                return Response(
                    {'message': 'User is already active','status':False},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            request = self.context.get('request')
            
            if user.communication_email:
                # Resend email verification
                result = SignupSerializer().send_verification_email(user, request)
                if "error" in result:
                    return Response(
                        {'error': result['error']},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
                return Response({'success': True,'message':"Verification email resent"})
            
            elif user.communication_mobile:
                # Resend SMS OTP
                country_code = user.country.country_code if user.country else '+91'
                sms_result = OTPManager.send_otp(
                    country_code=country_code,
                    phone_number=user.communication_mobile
                )
                if not sms_result['status']:
                    return Response(
                        {'message': sms_result['message'],'status':False},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
                return Response({'success': True,'message':'OTP resent to mobile'})
            
            return Response(
                {'message': 'No verification method found','status':False},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except CustomUser.DoesNotExist:
            return Response(
                {'message': 'User not found','status':False},
                status=status.HTTP_404_NOT_FOUND
            )
        


class VerifyEmailView(APIView):
    def get(self, request, uidb64, token):
        try:
            uid = uidb64
            user = CustomUser.objects.get(pk=uid)
            
            # Verify token
            access_token = AccessToken(token)
            if access_token['user_id'] != user.id:
                return Response({"error": "Invalid token"}, status=status.HTTP_400_BAD_REQUEST)
            
            # Mark user as active
            user.is_active = True
            user.save()
            
            return Response({"success": "Email verified successfully"})
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        

class VerifyMobileOTPView(APIView):
    def post(self, request):
        mobile = request.data.get('username')
        otp = request.data.get('otp')
        password = request.data.get('password')
        if not mobile or not otp:
            return Response(
                {"error": "Mobile and OTP are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        result = OTPManager.verify_otp(
            phone_number=mobile,
            otp=otp
        )
        try: 
            # Authenticate with username and password
            authenticated_user = authenticate(
                    username=mobile,
                    password=password
                )
                
            if not authenticated_user:
                return Response(
                    {"error": "Invalid credentials"},
                    status=status.HTTP_401_UNAUTHORIZED
                )

                # Mark user as active if not already
            if not authenticated_user.is_active:
                    authenticated_user.is_active = True
                    authenticated_user.save()

                # Generate tokens
            refresh = RefreshToken.for_user(authenticated_user)
            access_token = str(refresh.access_token)
                
            user_data = {
                    "id": authenticated_user.id,
                    "username": authenticated_user.username,
                    "full_name": authenticated_user.full_name,
                    "is_active": authenticated_user.is_active
                }
                
            return Response({
                    "success": "OTP verified and authenticated successfully",
                    "refresh_token": str(refresh),
                    "access_token": access_token,
                    "user": user_data
                }, status=status.HTTP_200_OK)
            
        except email_otp.DoesNotExist:
            return Response(
                {"error": "No OTP found for this user"},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class PasswordResetRequestView(APIView):
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        username = serializer.validated_data['username']
        
        # Check if username is email or mobile
        is_email = False
        is_mobile = False
        
        try:
            validate_email(username)
            is_email = True
        except ValidationError:
            # Check if it's a valid mobile number (adjust regex as needed)
            if re.match(r'^\+?1?\d{9,15}$', username):  # Basic international mobile format
                is_mobile = True
        
        if not is_email and not is_mobile:
            return Response(
                {"error": "Please provide a valid email address or mobile number"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Find user by email or mobile
            if is_email:
                user = CustomUser.objects.get(username=username)  
            else:
                user = CustomUser.objects.get(communication_mobile=username)  
            
        except CustomUser.DoesNotExist:
            return Response(
                {"error": "No account found with this username"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Generate a 6-digit OTP
        otp = str(random.randint(100000, 999999))
        
        if is_email:
            # Save OTP to email OTP table
            email_otp.objects.create(
                email=username,
                otp=otp,
                created_at=timezone.now()
            )

            # Send email with OTP
            subject = "Password Reset OTP"
            message = f"""
            You're receiving this email because you requested a password reset.
            Your OTP for password reset is: {otp}
            This OTP is valid for 5 hours.
            """
            
            send_mail(
                subject,
                message,
                'contact@prune.co.in',
                [user.username],
                fail_silently=False,
            )


              
        else:
            # For mobile, use your OTPManager
            result = OTPManager.send_otp(
            country_code='+91', # type: ignore

                phone_number=username,
                
            )
            
            if not result.get('status', False):
                return Response(
                    {"error": "Failed to send OTP to mobile number"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        return Response(
            {
                "status": True,
                "message": "Password reset OTP sent successfully",
                "destination": "email" if is_email else "mobile",
                "username": username  # returning where OTP was sent
            },
            status=status.HTTP_200_OK
        )

     
        

        
class VerificationStatusView(APIView):
    def get(self, request):
        username = request.query_params.get('username')
        
        if not username:
            return Response(
                {'error': 'Username is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = CustomUser.objects.get(username=username)
            return Response({
                'is_active': user.is_active,
                'verification_method': 'email' if user.communication_email else 'mobile',
                'verified': user.is_active
            })
        except CustomUser.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        



class VerifyOTPView(APIView):
    def post(self, request):
        # Get data from request
        username = request.data.get('username')
        otp = request.data.get('otp')
        password = request.data.get('password')
        full_name = request.data.get('full_name')
        auth_token = request.data.get('auth_token')
        # Check if auth_token is provided
        # if auth_token:
        #     try:
        #         device = Device.objects.get(device_token=auth_token)
        #     except Device.DoesNotExist:
        #         return Response({'error': 'No auth token found for this device'}, status=400)
        # else:
        #     device = None



        missing_fields = []
        if not full_name:
            missing_fields.append("full_name")
        if not username:
            missing_fields.append("username")
        if not password:
            missing_fields.append("password")
        if not otp:
            missing_fields.append("otp")


        # print(username,otp,password)
        if missing_fields:
            verb = "is" if len(missing_fields) == 1 else "are"

            return Response(
                {'status':False,"message": f"{', '.join(missing_fields)} {verb} required. "},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Determine if username is email or mobile
            is_email = False
            try:
                validate_email(username)
                is_email = True
            except ValidationError:
                # Basic mobile number validation
                if not re.match(r'^\+?1?\d{9,15}$', username):
                    return Response(
                        {"message": "Invalid email or mobile number format"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            # Find user based on username type
            if is_email:
                try:
                    user = CustomUser.objects.create_user(username=username,password = password)
                    user.is_active = True
                    user.communication_email = username
                    user.full_name = full_name
                    user.save()

                    wallet, created = Wallet.objects.get_or_create(user=user)

                   
                except CustomUser.DoesNotExist:
                    return Response(
                        {"message": "No user found with this email"},
                        status=status.HTTP_404_NOT_FOUND
                    )
                
                # Verify email OTP
                try:
                  
                    user_otp = email_otp.objects.filter(
                        email = username
                    ).latest('created_at')
                      # print('otp',otp)
                    device_otp = email_otp.objects.update(
                    email = username,
                    # device=device
                )
                    
                    if user_otp.otp != int(otp):
                        return Response(
                            {"error": "Invalid OTP"},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                    
                    if timezone.now() > user_otp.created_at + timedelta(hours=5):
                        return Response(
                            {"error": "OTP has expired"},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                except email_otp.DoesNotExist:
                    return Response(
                        {"error": "No OTP found for this email"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            else:
                # Verify mobile OTP
                result = OTPManager.verify_otp(
                    phone_number=username,
                    otp=otp,
                    # device=device
                )
                if not result.get('status', False):
                    return Response(
                        {"error": result.get('message', 'Invalid OTP')},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                try:
                    user = CustomUser.objects.create_user(username=username,password = password)
                    user.is_active =True
                    user.full_name = full_name
                    user.communication_mobile = username
                    user.save()

                    wallet, created = Wallet.objects.get_or_create(user=user)
                    cart, created = Cart.objects.get_or_create(user=user)

                except CustomUser.DoesNotExist:
                    return Response(
                        {"message": "No user found with this mobile number"},
                        status=status.HTTP_404_NOT_FOUND
                    )

            # Authenticate with username and password
            auth_username = user.username  # Use the actual username from DB
           
            refresh = RefreshToken.for_user(user)

            # access_token = str(refresh.access_token)
            access_token = str(refresh.access_token)

            user_data = {
                "id": user.id,
                "username": user.username,
                "full_name": user.full_name,
                "is_active": user.is_active,
                "wallet": wallet.amount,
                "cart":cart.user.username
            }
            
            return Response({
                "success": True,
                "message":"OTP verified and Login successfully",
                "refresh_token": str(refresh),
                "access_token": access_token,
                "user": user_data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            error_msg = str(e)

               # Check for unique constraint violation
            if 'UNIQUE constraint failed' in error_msg:
                print(error_msg)
                # Extract the field name from the error message
                field_match = re.search(r'UNIQUE constraint failed: \w+\.\w+_(.*?)\)?$', error_msg)
                if field_match:
                    field_name = field_match.group(1)
                    error_msg = f"This {field_name} is already in use. Please use a different one."
                else:
                    error_msg = "This value is already in use. Please try a different one."
            
            return Response(
                    {"message": "User Exists With This Account","success": False},status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    def post(self, request):

        username = request.data.get('username')
        password = request.data.get('password')
        
        if not username or not password:
            return Response(
                {"message": "Both username and password are required","status":False},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = self.authenticate_custom_user(username, password)
        print(user,'user')
        if user == None:
            return Response({"message":"password not match","status":False},status=status.HTTP_404_NOT_FOUND)
        if user:
            return self.generate_token_response(user)
        
        # Step 2: Check Prune_Old_User if CustomUser auth fails
        old_user = self.get_old_user(username)
        if old_user:
            # # Auto-migrate and login
            # user = self.migrate_user(old_user, password)
            # old_user.is_migrated = True  # Mark as migrated
            # old_user.save()
            # return self.generate_token_response(user)

            try:
                with transaction.atomic():
                    user = self.migrate_user(old_user, password)
                    old_user.is_migrated = True  # Mark as migrated
                    old_user.save()
                    return self.generate_token_response(user)
            except Exception as e:
                return Response(
                    {"error": f"Migration failed: {str(e)}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        # If neither worked
        return Response(
            {"status":False,"message": "User not Found"},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    def authenticate_custom_user(self, identifier, password):
        try:
            user = CustomUser.objects.get(
                Q(communication_email=identifier) |
                Q(communication_mobile=identifier) |
                Q(username=identifier)
            )
            if user.check_password(password):
                return user
            return None
        except CustomUser.DoesNotExist:
            return None
        except CustomUser.MultipleObjectsReturned:
            users = CustomUser.objects.filter(Q(communication_email=identifier) |
                Q(communication_mobile=identifier) |
                Q(username=identifier)
            )
            for user in users:
                if user.check_password(password):
                    return user
            return None
    
    def get_old_user(self, identifier):
        """Find user in Prune_Old_User by email or mobile"""
        try:
            if '@' in identifier:
                return Prune_Old_User.objects.get(email=identifier)
            return Prune_Old_User.objects.get(mobile=identifier)
        except Prune_Old_User.DoesNotExist:
            return None
    
    def migrate_user(self, old_user, password):
        """Create new CustomUser from old user data"""
        username = old_user.email or old_user.mobile
        full_name = f"{old_user.first_name} {old_user.last_name}".strip()
        
        return CustomUser.objects.create(
            username=username,
            communication_email=old_user.email,
            communication_mobile=old_user.mobile,
            full_name=full_name,
            password=make_password(password),
            avatar=old_user.avatar,
            birth_date=old_user.birth_date,
            country=old_user.country,
            referral_code=old_user.referral_code,
            is_active=True
        )
    
    def generate_token_response(self, user):
        refresh = RefreshToken.for_user(user)
        return Response({
            "status": True,
            "message":"Login successfully",
            "access_token": str(refresh.access_token),
            "refresh_token": str(refresh),
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.communication_email,
                "mobile": user.communication_mobile,
                "full_name": user.full_name
            }
        }, status=status.HTTP_200_OK)

class LogoutView(APIView):
    # authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        print(f"User attempting logout: {request.user.username}")
        print(f"Auth Header: {request.headers.get('Authorization')}")

        try:
            refresh_token = request.data.get("refresh_token")
            if not refresh_token:
                return Response(
                    {"error": "Refresh token is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            token = RefreshToken(refresh_token)
            token.blacklist()

            auth_header = request.headers.get('Authorization', '').split()
            if len(auth_header) == 2 and auth_header[0].lower() == 'bearer':
                access_token = auth_header[1]
                try:
                    RefreshToken(access_token).blacklist()
                except TokenError:
                    pass  

            return Response(
                {"message": "Logout successful"}, 
                status=status.HTTP_200_OK
            )

        except TokenError as e:
            return Response(
                {"error": "Invalid token", "details": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": "Logout failed", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
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

        user.set_password(serializer.validated_data['new_password'])
        user.save()

        return Response(
            {"message": "Password reset successfully"},
            status=status.HTTP_200_OK
        )
    
class PasswordVerifyOtpView(APIView):
    def post(self,request):
        otp = request.data.get('otp')
        
        username = request.data.get('username')
        if not otp or not username:
            missing_fields = []
            if not otp:
                missing_fields.append('otp')
            if not username:
                missing_fields.append('username')
            return Response(
                {"message": f"Missing field(s): {', '.join(missing_fields)}",'status':False},
                status=status.HTTP_400_BAD_REQUEST
            )
        is_email = False
        try:
            validate_email(username)
            is_email = True
        except ValidationError:
            if not re.match(r'^\+?1?\d{9,15}$', username):
                return Response(
                    {"error": "Invalid email or mobile number format"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        try:
            if is_email:
                user = CustomUser.objects.get(username=username)
                user_otp = email_otp.objects.filter(
                    email=username
                ).latest('created_at')

                if user_otp.otp != int(otp):
                    return Response(
                        {"message": "Invalid OTP"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                user_otp.is_verified = True
                user_otp.save()
                if timezone.now() > user_otp.created_at + timedelta(hours=5):
                    return Response(
                        {"error": "OTP has expired"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            else:
                try:
                    user = CustomUser.objects.get(username=username)
                except:
                    return Response({"message":"user not found","status":False})
                
                
                result = OTPManager.verify_otp(
                    phone_number=username,
                    otp=otp
                )
                if not result.get('status', False):
                    return Response(
                        {'status':False,"message": 'Invalid OTP'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            # if is_email:
            #     user_otp.delete()
        except CustomUser.DoesNotExist:
            return Response(
                {"status":False,"message": "User not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except email_otp.DoesNotExist:
            return Response(
                {"message": "No OTP found for this email"},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"status":False,"message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        return Response({"status":True,"message":"otp verified","fullname":user.full_name},status=status.HTTP_200_OK)
        

class PasswordResetConfirmView(APIView):
    def post(self, request):
        username = request.data.get('username')
       
        new_password = request.data.get('new_password')
        confirm_password = request.data.get('confirm_password')


        missing_fields = []
        if not new_password:
            missing_fields.append("new_password")
        if not confirm_password:
            missing_fields.append("confirm_password")
        if not username:
            missing_fields.append("username")
      

        if missing_fields:
            verb = "is" if len(missing_fields) == 1 else "are"
            return Response(
                {'status':False,"message": f"{', '.join(missing_fields)} {verb} required. "},
                status=status.HTTP_400_BAD_REQUEST
            )


        if new_password != confirm_password:
            return Response(
                {"status":False,"message": "Passwords do not match"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = CustomUser.objects.get(username=username)
        except:
            return Response({"message":"User Does not Exists","status":False},status=status.HTTP_404_NOT_FOUND)
        if email_otp.objects.filter(is_verified = True).latest():
            user.set_password(new_password)
            user.save()

            return Response(
                    {"status":True,"message": "Password has been reset successfully"},
                    status=status.HTTP_200_OK
                )
        else:
            return Response({"status":False,"message": "OTP is not verified"},
                    status=status.HTTP_403_FORBIDDEN
                )

    

class RefreshTokenView(APIView):
    """
    API to refresh access token using refresh token
    """
    def post(self, request):
        refresh_token = request.data.get('refresh')
        
        if not refresh_token:
            return Response(
                {"error": "Refresh token is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            refresh = RefreshToken(refresh_token)
            new_access_token = str(refresh.access_token)
            
            
            new_refresh_token = str(RefreshToken.for_user(refresh.payload['user_id']))
            
            return Response({
                "access": new_access_token,
                "refresh": new_refresh_token  
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {"error": "Invalid or expired refresh token"},
                status=status.HTTP_401_UNAUTHORIZED
            )
        

class UserListView(generics.ListAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    # authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)

        return Response({
            "status": True,
            "message": "Users retrieved successfully",
            "data": serializer.data
        }, status=status.HTTP_200_OK)



class UserDetailView(APIView):
    # authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        serializer = UserSerializer(user)
        return Response({
            "status": True,
            "message": "User profile retrieved successfully",
            "data": serializer.data
        }, status=status.HTTP_200_OK)



class UserProfileUpdateView(generics.UpdateAPIView):
    serializer_class = UserSerializer
    # authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', True)  # Allow PATCH by default
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response({
            "status": True,
            "message": "User profile updated successfully",
            "data": serializer.data
        }, status=status.HTTP_200_OK)

    

class UserAddressSave(generics.ListAPIView):
    # authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self,request):
        try:
            address = UserAddress.objects.filter(user = request.user, is_active = True)

            user_address = UserAddressRetrunSerializer(address, many=True)
            return JsonResponse({"status":True,"message":"your saved address","user_address" : user_address.data})
        except Exception as e:
                return JsonResponse({"status":"fail","message":str(e),"user_address" : ""})
    def post(self, request):
        try:
            user = request.user

            required_fields = [
                'phone_no', 'house_no', 'locality', 'landmark', 
                'district', 'state', 'country', 'pincode', 'full_address'
            ]
            optional_fields = ['request_for', 'lat', 'lng']

            data = request.data

            missing_fields = [field for field in required_fields if not data.get(field)]
            if missing_fields:
                return Response({
                    "status": False,
                    "message": f"Missing fields: {', '.join(missing_fields)}"
                }, status=status.HTTP_400_BAD_REQUEST)

            if UserAddress.objects.filter(user=user, is_active=True).count() >= 4:
                return Response({
                    "status": True,
                    "message": "You can only save up to 4 addresses."
                }, status=status.HTTP_400_BAD_REQUEST)

            serializer = UserAddressSerializer(data=request.data)
            if serializer.is_valid():
                address = serializer.save(user=user)  # assign user here
                return Response({
                    "status": True,
                    "message": "Data saved",
                    "user_address": [UserAddressSerializer(address).data]
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    "status": False,
                    "message": serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({
                "status": False,
                "message": "Address Not Saved",
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class DeleteUserAddressAPIView(APIView):
    # authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def delete(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response({"status": "fail", "message": "User is not authenticated", "user_address": ""}, status=status.HTTP_401_UNAUTHORIZED)

        address_id = request.data.get("address_id") or request.query_params.get("address_id")
        if not address_id:
            return Response({"status": "fail", "message": "Address ID is required", "user_address": ""}, status=status.HTTP_400_BAD_REQUEST)

        try:
            address = UserAddress.objects.get(id=address_id, user=request.user, is_active=True)
            address.delete()
            remaining_addresses = UserAddress.objects.filter(user=request.user, is_active=True)
            user_address = UserAddressRetrunSerializer(remaining_addresses, many=True)
            return Response({"status": "success", "message": "Address deleted"},status=status.HTTP_200_OK)
        except UserAddress.DoesNotExist:
            return Response({"status": "fail", "message": "Address not found", "user_address": ""}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"status": "fail", "message": str(e), "user_address": ""}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class WalletBalanceAPIView(APIView):
    # authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]


    def get(self, request, format=None):
        wallet, created = Wallet.objects.get_or_create(user=request.user)
        return Response({"success":True,'wallet_balance': wallet.amount},status=status.HTTP_200_OK)


class WalletHistoryAPIView(APIView):
    permission_classes = [IsAuthenticated]
    # authentication_classes = [JWTAuthentication]

    def get(self, request, format=None):
        page = int(request.GET.get('page', 0))
        per_page = 20
        start = page * per_page
        end = start + per_page

        all_history = WalletHistory.objects.filter(is_active=True, user=request.user).order_by('-id')
        paginated_history = all_history[start:end]
        total_pages = max(math.ceil(all_history.count() / per_page) - 1, 0)

        return Response({
            "success":True,
            "page": f"{page}/{total_pages}",
            "wallet_history": WalletHistorySerializer(paginated_history, many=True).data
        },status=status.HTTP_200_OK)
