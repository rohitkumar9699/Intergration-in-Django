from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.utils import timezone
from django.conf import settings


class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateField(auto_now=True)

    class Meta:
        abstract = True



class CustomUserManager(BaseUserManager):
    def create_user(self, username, communication_email=None, communication_mobile=None, password=None, **extra_fields):
        if not username:
            raise ValueError('Username must be set')
        
        communication_email = self.normalize_email(communication_email) if communication_email else None
        user = self.model(
            username=username,
            communication_email=communication_email,
            communication_mobile=communication_mobile,
            **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, communication_email=None, communication_mobile=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(username, communication_email, communication_mobile, password, **extra_fields)

class CustomUser(AbstractBaseUser, PermissionsMixin):
    GENDER = (
        ('Male', 'Male'),
        ('Female', 'Female'),
    )

    username = models.CharField(max_length=50, unique=True)
    full_name = models.CharField(max_length=100, blank=True)
    communication_email = models.EmailField('Communication Email',  null=True, blank=True)
    communication_mobile = models.CharField('Communication Mobile', max_length=13, null=True, blank=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=20, blank=True, choices=GENDER, default='')
    country = models.CharField(max_length=300, blank=True, default='India')
    referral_code = models.CharField(max_length=15, blank=True, null = True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateField(auto_now=True)
   
    
    # Required fields
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    objects = CustomUserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = []  # No additional required fields

    class Meta:
        verbose_name = 'userManagement'
        verbose_name_plural = 'userManagement'

    def __str__(self):
        return self.full_name or self.username



class Prune_Old_User(models.Model):
    email = models.EmailField(null=True, blank=True, default='')
    username = models.CharField(null=True, blank=True, default='', max_length=50)
    first_name = models.CharField(max_length=30, blank=True)
    last_name = models.CharField(max_length=30, blank=True)
    date_joined = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    mobile = models.CharField(max_length=13, unique=True)
    birth_date = models.DateField(null=True)
    country = models.CharField(max_length=300, blank=True, default='')
    referral_code = models.CharField(max_length=15, blank=True, null=True, default='')
    is_migrated = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now=True)
    updated_at = models.DateField(auto_now=True)
    

    def __str__(self):
        
        full_name = '%s %s' % (self.first_name, self.last_name)
        return full_name.strip()

class UserAddress(BaseModel):
    user =  models.ForeignKey(CustomUser, default='', null=True,blank=True, related_name='user_address',on_delete=models.CASCADE)
    phone_no =  models.CharField(max_length=12,null=True,blank=True, default='')
    house_no =  models.CharField(max_length=100,null=True,blank=True, default='')
    locality =  models.CharField(max_length=100,null=True,blank=True, default='')
    request_for =  models.CharField(max_length=100,null=True,blank=True, default='indian sim')
    lat =  models.CharField(max_length=100,null=True,blank=True, default='')
    lng =  models.CharField(max_length=100,null=True,blank=True, default='')
    landmark =  models.CharField(max_length=100,null=True,blank=True, default='')
    district =  models.CharField(max_length=100,null=True,blank=True, default='')
    state =  models.CharField(max_length=100,null=True,blank=True, default='')
    country =  models.CharField(max_length=100,null=True,blank=True, default='')
    pincode =  models.CharField(max_length=6,null=True,blank=True, default='')
    full_address =  models.TextField(null=True,blank=True, default='')
    is_active =  models.BooleanField(default=True)
     
    def __str__(self):
        return str(self.user)
    


class Wallet(BaseModel):
    amount = models.FloatField(default=0)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        primary_key=True,
    )
    is_active = models.BooleanField(default=True)
  

    def __str__(self):
        return str(self.amount)



class WalletHistory(BaseModel):
    TRANSACTION_TYPE = (
        ('Debit', 'Debit'),
        ('Credit', 'Credit'),
    )
    amount = models.FloatField(default=0)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
    transaction_type = models.CharField(max_length=50, blank=False, null=False, choices=TRANSACTION_TYPE)
    description = models.CharField(max_length=500, blank=False, null=False)
    additional_details = models.CharField(max_length=1500, blank=False, null=False)
    is_active = models.BooleanField(default=True)
  

    
    
class Cart(BaseModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    # sim_pack = models.ForeignKey(IndiaFRCSimPack, on_delete=models.CASCADE, null=True, blank=True)
    is_ordered = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username}"

  








class email_otp(BaseModel):
    mobile = models.CharField(max_length=13, unique=True)
    otp = models.CharField(max_length=6)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.mobile
    
class mobile_otp(BaseModel):
    mobile = models.CharField(max_length=13, unique=True)
    otp = models.CharField(max_length=6)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    otp_status = models.BooleanField(default=False)
    number = models.CharField(max_length=13, unique=True)

    def __str__(self):
        return self.mobile