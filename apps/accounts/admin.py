from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    CustomUser, UserProfile, CustomerProfile, VendorProfile, 
    DeliveryProfile, StaffProfile, UserVerification
)

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = [
        'username', 'email', 'first_name', 'last_name', 
        'user_type', 'account_status', 'email_verified', 
        'loyalty_points', 'is_active', 'date_joined'
    ]
    list_filter = [
        'user_type', 'account_status', 'is_active', 'is_staff', 
        'is_superuser', 'email_verified', 'phone_verified', 
        'identity_verified', 'date_joined'
    ]
    search_fields = ['username', 'email', 'first_name', 'last_name', 'phone_number']
    ordering = ['-date_joined']
    readonly_fields = ['date_joined', 'last_login', 'created_at', 'updated_at']
    
    fieldsets = UserAdmin.fieldsets + (
        ('User Type & Status', {
            'fields': ('user_type', 'account_status')
        }),
        ('Contact Information', {
            'fields': ('phone_number', 'date_of_birth', 'profile_picture')
        }),
        ('Customer Information', {
            'fields': ('dietary_preferences', 'loyalty_points', 'preferred_payment_methods', 'delivery_addresses'),
            'classes': ('collapse',)
        }),
        ('Business Information', {
            'fields': ('business_license', 'tax_id', 'bank_account_info'),
            'classes': ('collapse',)
        }),
        ('Delivery Information', {
            'fields': ('vehicle_type', 'license_plate', 'delivery_radius'),
            'classes': ('collapse',)
        }),
        ('Employment Information', {
            'fields': ('employment_start_date', 'employment_end_date', 'hourly_rate', 'commission_rate'),
            'classes': ('collapse',)
        }),
        ('Verification Status', {
            'fields': ('email_verified', 'phone_verified', 'identity_verified', 'background_check_passed', 'two_factor_enabled')
        }),
        ('System Information', {
            'fields': ('last_login_ip', 'email_verified_at', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('profile')

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'user_type', 'location', 'average_rating', 'total_ratings']
    list_filter = ['user__user_type', 'marketing_opt_in', 'spice_tolerance']
    search_fields = ['user__username', 'user__email', 'bio', 'location']
    readonly_fields = ['created_at', 'updated_at', 'average_rating', 'total_ratings']
    
    fieldsets = [
        ('Basic Information', {
            'fields': ('user', 'bio', 'location')
        }),
        ('Preferences', {
            'fields': ('favorite_cuisines', 'allergens', 'spice_tolerance')
        }),
        ('Contact & Social', {
            'fields': ('social_media_links', 'emergency_contact')
        }),
        ('Privacy & Notifications', {
            'fields': ('privacy_settings', 'notification_preferences', 'marketing_opt_in')
        }),
        ('Professional Information', {
            'fields': ('professional_summary', 'certifications', 'languages_spoken', 'availability_hours'),
            'classes': ('collapse',)
        }),
        ('Ratings', {
            'fields': ('average_rating', 'total_ratings')
        }),
        ('System Information', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    ]

    def user_type(self, obj):
        return obj.user.get_user_type_display()
    user_type.short_description = 'User Type'

@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'membership_tier', 'total_orders', 'total_spent', 
        'budget_range', 'created_at'
    ]
    list_filter = ['membership_tier', 'budget_range']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['total_orders', 'total_spent', 'created_at', 'updated_at']
    
    fieldsets = [
        ('Customer Details', {
            'fields': ('user', 'preferred_delivery_time', 'budget_range')
        }),
        ('Order Statistics', {
            'fields': ('total_orders', 'total_spent', 'favorite_restaurants')
        }),
        ('Membership', {
            'fields': ('membership_tier', 'membership_expires')
        }),
        ('System Information', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    ]

@admin.register(VendorProfile)
class VendorProfileAdmin(admin.ModelAdmin):
    list_display = [
        'business_name', 'user', 'business_type', 'verification_status', 
        'total_orders', 'total_sales', 'commission_rate', 'created_at'
    ]
    list_filter = ['business_type', 'verification_status', 'payout_schedule']
    search_fields = ['business_name', 'user__username', 'user__email', 'business_registration_number']
    readonly_fields = ['total_sales', 'total_orders', 'average_preparation_time', 'created_at', 'updated_at']
    
    fieldsets = [
        ('Business Information', {
            'fields': ('user', 'business_name', 'business_type', 'business_description')
        }),
        ('Legal & Certification', {
            'fields': ('business_registration_number', 'food_safety_certification', 'insurance_policy_number')
        }),
        ('Operational Details', {
            'fields': ('cuisine_specialties', 'service_areas', 'operating_hours', 'minimum_order_amount')
        }),
        ('Financial Information', {
            'fields': ('commission_rate', 'payout_schedule')
        }),
        ('Performance Metrics', {
            'fields': ('total_sales', 'total_orders', 'average_preparation_time')
        }),
        ('Status', {
            'fields': ('verification_status',)
        }),
        ('System Information', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    ]

@admin.register(DeliveryProfile)
class DeliveryProfileAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'vehicle_make', 'is_online', 'total_deliveries', 
        'successful_deliveries', 'success_rate', 'average_delivery_time', 
        'total_earnings'
    ]
    list_filter = ['vehicle_make', 'is_online', 'has_insulated_bag', 'has_gps_device']
    search_fields = ['user__username', 'user__email', 'drivers_license_number', 'vehicle_make', 'vehicle_model']
    readonly_fields = ['total_deliveries', 'successful_deliveries', 'success_rate', 'average_delivery_time', 'total_earnings', 'created_at', 'updated_at']
    
    fieldsets = [
        ('Driver Information', {
            'fields': ('user', 'drivers_license_number')
        }),
        ('Vehicle Information', {
            'fields': ('vehicle_make', 'vehicle_model', 'vehicle_year', 'vehicle_color', 'vehicle_registration')
        }),
        ('Equipment', {
            'fields': ('has_insulated_bag', 'has_gps_device')
        }),
        ('Documentation', {
            'fields': ('insurance_policy',)
        }),
        ('Availability', {
            'fields': ('available_hours', 'preferred_zones', 'max_deliveries_per_hour')
        }),
        ('Performance Metrics', {
            'fields': ('total_deliveries', 'successful_deliveries', 'average_delivery_time', 'total_earnings')
        }),
        ('Current Status', {
            'fields': ('is_online', 'current_location', 'current_orders')
        }),
        ('System Information', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    ]

    def success_rate(self, obj):
        return f"{obj.success_rate:.1f}%"
    success_rate.short_description = 'Success Rate'

@admin.register(StaffProfile)
class StaffProfileAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'employee_id', 'position', 'department', 
        'shift_pattern', 'performance_rating', 'created_at'
    ]
    list_filter = ['position', 'department', 'shift_pattern', 'can_process_orders', 'can_handle_payments']
    search_fields = ['user__username', 'user__email', 'employee_id', 'position']
    readonly_fields = ['performance_rating', 'created_at', 'updated_at']
    
    fieldsets = [
        ('Employee Information', {
            'fields': ('user', 'employee_id', 'position', 'department')
        }),
        ('Work Details', {
            'fields': ('shift_pattern', 'work_schedule')
        }),
        ('Permissions', {
            'fields': ('permissions', 'can_process_orders', 'can_handle_payments', 'can_modify_menu', 'can_manage_staff')
        }),
        ('Performance', {
            'fields': ('performance_rating', 'training_completed')
        }),
        ('System Information', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    ]

@admin.register(UserVerification)
class UserVerificationAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'user_type', 'fully_verified', 'identity_document_verified', 
        'background_check_status', 'bank_account_verified', 'verified_by', 'updated_at'
    ]
    list_filter = [
        'fully_verified', 'identity_document_verified', 'business_license_verified', 
        'background_check_status', 'bank_account_verified'
    ]
    search_fields = ['user__username', 'user__email', 'identity_document_number']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = [
        ('User Information', {
            'fields': ('user',)
        }),
        ('Identity Verification', {
            'fields': ('identity_document_type', 'identity_document_number', 'identity_document_verified', 'identity_verified_at')
        }),
        ('Business Verification', {
            'fields': ('business_license_verified', 'tax_id_verified', 'food_safety_verified'),
            'classes': ('collapse',)
        }),
        ('Background Check', {
            'fields': ('background_check_status', 'background_check_date'),
            'classes': ('collapse',)
        }),
        ('Financial Verification', {
            'fields': ('bank_account_verified', 'payment_method_verified')
        }),
        ('Overall Status', {
            'fields': ('fully_verified', 'verification_notes', 'verified_by')
        }),
        ('System Information', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    ]

    def user_type(self, obj):
        return obj.user.get_user_type_display()
    user_type.short_description = 'User Type'
