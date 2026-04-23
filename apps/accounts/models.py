from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import RegexValidator
from decimal import Decimal

class CustomUser(AbstractUser):
    """Enhanced user model supporting multiple user types"""
    
    USER_TYPES = [
        ('customer', 'Customer'),
        ('vendor', 'Food Vendor'),
        ('delivery', 'Delivery Service Provider'),
        ('restaurant_staff', 'Restaurant Staff'),
        ('restaurant_manager', 'Restaurant Manager'),
        ('restaurant_owner', 'Restaurant Owner'),
        ('platform_admin', 'Platform Administrator'),
        ('support_agent', 'Customer Support Agent'),
        ('content_moderator', 'Content Moderator'),
        ('marketing_specialist', 'Marketing Specialist'),
        ('finance_manager', 'Finance Manager'),
        ('data_analyst', 'Data Analyst'),
    ]
    
    ACCOUNT_STATUS = [
        ('active', 'Active'),
        ('pending', 'Pending Verification'),
        ('suspended', 'Suspended'),
        ('inactive', 'Inactive'),
        ('banned', 'Banned'),
    ]
    
    # Basic Information
    email = models.EmailField(unique=True)
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$', 
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
    )
    phone_number = models.CharField(validators=[phone_regex], max_length=17, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    profile_picture = models.ImageField(upload_to='profiles/', null=True, blank=True)
    
    # User Type and Status
    user_type = models.CharField(max_length=20, choices=USER_TYPES, default='customer')
    account_status = models.CharField(max_length=15, choices=ACCOUNT_STATUS, default='active')
    
    # Customer-specific fields
    dietary_preferences = models.JSONField(default=list, blank=True, help_text="List of dietary preferences")
    loyalty_points = models.IntegerField(default=0)
    preferred_payment_methods = models.JSONField(default=list, blank=True)
    delivery_addresses = models.JSONField(default=list, blank=True)
    
    # Vendor/Staff specific fields
    business_license = models.CharField(max_length=100, blank=True, null=True)
    tax_id = models.CharField(max_length=50, blank=True, null=True)
    bank_account_info = models.JSONField(default=dict, blank=True, help_text="Encrypted bank account information")
    
    # Delivery provider specific fields
    vehicle_type = models.CharField(max_length=50, blank=True, null=True)
    license_plate = models.CharField(max_length=20, blank=True, null=True)
    delivery_radius = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="Delivery radius in kilometers")
    
    # Employment/Business Information
    employment_start_date = models.DateField(null=True, blank=True)
    employment_end_date = models.DateField(null=True, blank=True)
    hourly_rate = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="Commission percentage")
    
    # Verification and Security
    email_verified = models.BooleanField(default=False)
    phone_verified = models.BooleanField(default=False)
    identity_verified = models.BooleanField(default=False)
    background_check_passed = models.BooleanField(default=False)
    two_factor_enabled = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    email_verified_at = models.DateTimeField(null=True, blank=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'user_type']

    class Meta:
        db_table = 'accounts_customuser'
        indexes = [
            models.Index(fields=['user_type']),
            models.Index(fields=['account_status']),
            models.Index(fields=['email']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.email} ({self.get_user_type_display()})"

    @property
    def is_customer(self) -> bool:
        return self.user_type == 'customer'

    @property
    def is_vendor(self) -> bool:
        return self.user_type == 'vendor'

    @property
    def is_delivery_provider(self) -> bool:
        return self.user_type == 'delivery'

    @property
    def is_restaurant_staff(self) -> bool:
        return self.user_type in ['restaurant_staff', 'restaurant_manager', 'restaurant_owner']

    @property
    def is_platform_admin(self) -> bool:
        return self.user_type == 'platform_admin'

    @property
    def can_manage_restaurants(self) -> bool:
        return self.user_type in ['restaurant_manager', 'restaurant_owner', 'platform_admin']

    @property
    def can_deliver_orders(self) -> bool:
        return self.user_type == 'delivery' and self.account_status == 'active' and self.background_check_passed

    def get_full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip() or self.username


class UserProfile(models.Model):
    """Extended profile information for all user types"""
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(max_length=500, blank=True)
    location = models.CharField(max_length=100, blank=True)
    
    # Customer preferences
    favorite_cuisines = models.JSONField(default=list, blank=True)
    allergens = models.JSONField(default=list, blank=True)
    spice_tolerance = models.IntegerField(default=0, help_text="Scale of 1-5, 0 for not specified")
    
    # Social and contact information
    social_media_links = models.JSONField(default=dict, blank=True)
    emergency_contact = models.JSONField(default=dict, blank=True)
    
    # Privacy and preferences
    privacy_settings = models.JSONField(default=dict, blank=True)
    notification_preferences = models.JSONField(default=dict, blank=True)
    marketing_opt_in = models.BooleanField(default=False)
    
    # Professional information (for staff/vendors)
    professional_summary = models.TextField(blank=True, help_text="Professional experience summary")
    certifications = models.JSONField(default=list, blank=True)
    languages_spoken = models.JSONField(default=list, blank=True)
    availability_hours = models.JSONField(default=dict, blank=True)
    
    # Ratings and reviews
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=Decimal('0.00'))
    total_ratings = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'accounts_userprofile'
    
    def __str__(self):
        return f"{self.user.email}'s Profile"


class CustomerProfile(models.Model):
    """Additional customer-specific information"""
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='customer_profile', 
                               limit_choices_to={'user_type': 'customer'})
    
    # Customer preferences
    preferred_delivery_time = models.CharField(max_length=50, blank=True)
    budget_range = models.CharField(max_length=20, blank=True, choices=[
        ('low', 'Budget (GHC-GHC GHC)'),
        ('medium', 'Moderate (GHC GHC-GHC GHC GHC)'),
        ('high', 'Premium (GHC GHC GHC+)'),
    ])
    
    # Order history stats
    total_orders = models.IntegerField(default=0)
    total_spent = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    favorite_restaurants = models.JSONField(default=list, blank=True)
    
    # Membership information
    membership_tier = models.CharField(max_length=20, default='bronze', choices=[
        ('bronze', 'Bronze'),
        ('silver', 'Silver'),
        ('gold', 'Gold'),
        ('platinum', 'Platinum'),
    ])
    membership_expires = models.DateField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Customer Profile: {self.user.email}"


class VendorProfile(models.Model):
    """Vendor/Restaurant owner specific information"""
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='vendor_profile',
                               limit_choices_to={'user_type': 'vendor'})
    
    # Business information
    business_name = models.CharField(max_length=200)
    business_type = models.CharField(max_length=50, choices=[
        ('restaurant', 'Restaurant'),
        ('cafe', 'Cafe'),
        ('food_truck', 'Food Truck'),
        ('catering', 'Catering Service'),
        ('bakery', 'Bakery'),
        ('grocery', 'Grocery Store'),
    ])
    business_description = models.TextField(blank=True)
    
    # Legal and financial
    business_registration_number = models.CharField(max_length=100, unique=True)
    food_safety_certification = models.CharField(max_length=100, blank=True)
    insurance_policy_number = models.CharField(max_length=100, blank=True)
    
    # Operational details
    cuisine_specialties = models.JSONField(default=list, blank=True)
    service_areas = models.JSONField(default=list, blank=True)
    operating_hours = models.JSONField(default=dict, blank=True)
    minimum_order_amount = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0.00'))
    
    # Financial information
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('15.00'))
    payout_schedule = models.CharField(max_length=20, default='weekly', choices=[
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ])
    
    # Performance metrics
    total_sales = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    total_orders = models.IntegerField(default=0)
    average_preparation_time = models.IntegerField(default=30, help_text="Average time in minutes")
    
    # Status
    verification_status = models.CharField(max_length=20, default='pending', choices=[
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('suspended', 'Suspended'),
    ])
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Vendor: {self.business_name} ({self.user.email})"


class DeliveryProfile(models.Model):
    """Delivery service provider specific information"""
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='delivery_profile',
                               limit_choices_to={'user_type': 'delivery'})
    
    # Vehicle and equipment information
    vehicle_make = models.CharField(max_length=50, blank=True)
    vehicle_model = models.CharField(max_length=50, blank=True)
    vehicle_year = models.IntegerField(null=True, blank=True)
    vehicle_color = models.CharField(max_length=30, blank=True)
    has_insulated_bag = models.BooleanField(default=False)
    has_gps_device = models.BooleanField(default=True)
    
    # Documentation
    drivers_license_number = models.CharField(max_length=50, unique=True)
    insurance_policy = models.CharField(max_length=100, blank=True)
    vehicle_registration = models.CharField(max_length=100, blank=True)
    
    # Availability and preferences
    available_hours = models.JSONField(default=dict, blank=True)
    preferred_zones = models.JSONField(default=list, blank=True)
    max_deliveries_per_hour = models.IntegerField(default=3)
    
    # Performance metrics
    total_deliveries = models.IntegerField(default=0)
    successful_deliveries = models.IntegerField(default=0)
    average_delivery_time = models.IntegerField(default=30, help_text="Average time in minutes")
    total_earnings = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    # Current status
    is_online = models.BooleanField(default=False)
    current_location = models.JSONField(default=dict, blank=True)
    current_orders = models.JSONField(default=list, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    @property
    def success_rate(self) -> float:
        if self.total_deliveries == 0:
            return 0.0
        return (self.successful_deliveries / self.total_deliveries) * 100
    
    def __str__(self):
        return f"Delivery: {self.user.get_full_name()} ({self.user.email})"


class StaffProfile(models.Model):
    """Restaurant staff specific information"""
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='staff_profile',
                               limit_choices_to={'user_type__in': ['restaurant_staff', 'restaurant_manager', 'restaurant_owner']})
    
    # Employment details
    employee_id = models.CharField(max_length=20, unique=True)
    position = models.CharField(max_length=50, choices=[
        ('chef', 'Chef'),
        ('sous_chef', 'Sous Chef'),
        ('cook', 'Cook'),
        ('server', 'Server'),
        ('host', 'Host/Hostess'),
        ('manager', 'Manager'),
        ('assistant_manager', 'Assistant Manager'),
        ('cashier', 'Cashier'),
        ('bartender', 'Bartender'),
        ('dishwasher', 'Dishwasher'),
        ('cleaner', 'Cleaner'),
        ('owner', 'Owner'),
    ])
    department = models.CharField(max_length=50, blank=True)
    
    # Work schedule
    shift_pattern = models.CharField(max_length=20, choices=[
        ('full_time', 'Full Time'),
        ('part_time', 'Part Time'),
        ('contract', 'Contract'),
        ('seasonal', 'Seasonal'),
    ])
    work_schedule = models.JSONField(default=dict, blank=True)
    
    # Permissions and access
    permissions = models.JSONField(default=list, blank=True)
    can_process_orders = models.BooleanField(default=False)
    can_handle_payments = models.BooleanField(default=False)
    can_modify_menu = models.BooleanField(default=False)
    can_manage_staff = models.BooleanField(default=False)
    
    # Performance
    performance_rating = models.DecimalField(max_digits=3, decimal_places=2, default=Decimal('0.00'))
    training_completed = models.JSONField(default=list, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Staff: {self.user.get_full_name()} - {self.position}"


class UserVerification(models.Model):
    """Track verification status for different user types"""
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='verification')
    
    # Email/Phone verification
    email_verification_code = models.CharField(max_length=10, blank=True)
    phone_verification_code = models.CharField(max_length=10, blank=True)
    code_expires_at = models.DateTimeField(null=True, blank=True)
    
    # Document verification
    identity_document_type = models.CharField(max_length=30, blank=True, choices=[
        ('passport', 'Passport'),
        ('drivers_license', 'Driver\'s License'),
        ('national_id', 'National ID'),
        ('state_id', 'State ID'),
    ])
    identity_document_number = models.CharField(max_length=50, blank=True)
    identity_document_verified = models.BooleanField(default=False)
    identity_verified_at = models.DateTimeField(null=True, blank=True)
    
    # Business verification (for vendors)
    business_license_verified = models.BooleanField(default=False)
    tax_id_verified = models.BooleanField(default=False)
    food_safety_verified = models.BooleanField(default=False)
    
    # Background checks (for delivery and staff)
    background_check_status = models.CharField(max_length=20, default='not_required', choices=[
        ('not_required', 'Not Required'),
        ('pending', 'Pending'),
        ('passed', 'Passed'),
        ('failed', 'Failed'),
        ('expired', 'Expired'),
    ])
    background_check_date = models.DateField(null=True, blank=True)
    
    # Financial verification
    bank_account_verified = models.BooleanField(default=False)
    payment_method_verified = models.BooleanField(default=False)
    
    # Overall verification status
    fully_verified = models.BooleanField(default=False)
    verification_notes = models.TextField(blank=True)
    verified_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True,
                                  related_name='verified_users', limit_choices_to={'user_type': 'platform_admin'})
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Verification for {self.user.email}"
