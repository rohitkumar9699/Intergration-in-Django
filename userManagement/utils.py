import requests
from datetime import date, datetime, timedelta
from django.conf import settings
from .models import CustomUser 
import random
import string
from django.http import JsonResponse
import random
import math
from django.utils import timezone
from .models import email_otp, mobile_otp
from django.utils.timezone import now

SMS_URL = "https://9rd3vd.api.infobip.com/sms/1/text/query?username=MudStudio&password=Prune@122024&from="

class OTPManager:
    
    @staticmethod
    def generate_otp(length=6):
        return str(math.floor(random.random() * 900000) + 100000)


    @staticmethod
    def send_otp(country_code, phone_number, fake_otp=False):
      
        country_code = country_code.replace('+', '')
        number = phone_number.strip()
        
      
        # Generate OTP
        otp = OTPManager.generate_otp()
      
        otp_count_save = mobile_otp.objects.create(number=phone_number,otp = otp,otp_status = True,created_at=now())
        

        otp_count_save.save()

        try:
            # Check daily OTP limit (5 per day)
            otp_count = mobile_otp.objects.filter(number=phone_number,created_at=now()).count()
            
            if otp_count >= 5:
                return {
                    'status': False,
                    'message': 'Daily OTP limit exceeded (5 per day)'
                }

            # Invalidate previous active OTPs
            otp_update = mobile_otp.objects.filter(
                number=phone_number,
                otp_status=True
            ).update(otp_status=False)

            if not fake_otp:
                message = f"{otp} is the OTP for Prune App."
                encoded_msg = requests.utils.quote(message)
                
            
                url = SMS_URL+"IPrune&to=91" + \
                phone_number+"&indiaDltContentTemplateId=1107161513294569922&indiaDltPrincipalEntityId=1101439040000040339&text="+message
                
                response = requests.get(url)
                print(response,'response')
                if response.status_code != 200:
                    return {
                        'status': False,
                        'message': 'Failed to send SMS',
                        'response': response.text
                    }

            # # Get country object
            # print('country_code',country_code)
            # country = Country.objects.filter(
            #     country_code= f"+{country_code}"
            # ).first()
            # print('cc',f"+{country_code}")
            # if not country:
            #     return {
            #         'status': False,
            #         'message': 'Invalid country code'
            #     }
            
            try:
            # Save OTP to user
                device_otp = mobile_otp.objects.filter(
                    number = phone_number
                ).order_by('-created_at').first()
                if device_otp:
                    device_otp.otp = otp
                    device_otp.otp_status = True
                    device_otp.created_date = timezone.now()
                    device_otp.save()

                    print('device_otp filtered', device_otp)

                else:
                    device_otp, created = mobile_otp.objects.create(
                        number = phone_number
                    )
                    

            except Exception as e:
                print('error', {e})

            return {
                'status': True,
                'message': 'OTP sent successfully',
                'otp': otp if settings.DEBUG else None  # Don't expose OTP in production
            }

        except Exception as e:
            return {
                'status': False,
                'message': str(e)
            }

    @staticmethod
    def verify_otp(phone_number, otp, device=None,mark_verified=True):
        try:
            try:
                if device:
                    device_mobile_otp = mobile_otp.objects.update(
                    number = phone_number,
                    device=device
                    )
                device_otp = mobile_otp.objects.filter(
                    number = phone_number,
                    otp = otp,
                ).order_by('-created_at').first()
               
                device_otp.is_verified = True
                device_otp.save()
            except Exception as e:
                    print('device otp error', {e})
                    return {
                        'status': False,
                        'message': f"OTP does not match!!!",
                        'user': None
                    }
            
            if timezone.now() > device_otp.created_at + timedelta(minutes=5):
                return {
                    'status': False,
                    'message': 'OTP expired',
                    'user': None
                }
            
            if mark_verified:
                device_otp.otp_status = False
                device_otp.is_active = True  # Activate user after successful verification
                device_otp.save()
            
            return {
                'status': True,
                'message': 'OTP verified successfully',
                'user': device_otp.number
            }
            
        except CustomUser.DoesNotExist:
            return {
                'status': False,
                'message': 'Invalid OTP or phone number',
                'user': None
            }
        except Exception as e:
            return {
                'status': False,
                'message': str(e),
                'user': None
            }
        
    def send_email(subject, message, recipient_list):
            url = "https://api.zeptomail.com/v1.1/email"

            payload = {
                "from": {"address": "noreply@email.prune.co.in"},
                "to": [{"email_address": {"address": email}} for email in recipient_list],
                "subject": subject,
                "htmlbody": message
            }

            # Set the headers for the ZeptoMail API request
            headers = {
                'Accept': "application/json",
                'Content-Type': "application/json",
                'Authorization': "Zoho-enczapikey wSsVR61+rB/0XK4oyTCqcuo5yg4DAgz1Fht1iQSnunCtSv/F9cdtlBbMAATzHvUWEWc9QGQb9egumRxU22ENjYl7n1hTCCiF9mqRe1U4J3x17qnvhDzMWWxflRqOLooIzghqnmVlE8oq+g=="
            }


            response = requests.post(url, json=payload, headers=headers)
         
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.json()}")