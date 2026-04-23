from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import (
    CustomUser, UserProfile, CustomerProfile, VendorProfile, 
    DeliveryProfile, StaffProfile, UserVerification
)

@receiver(post_save, sender=CustomUser)
def create_user_profiles(sender, instance, created, **kwargs):
    """Create appropriate profile objects when a new user is created"""
    if created:
        # Always create a basic UserProfile
        UserProfile.objects.create(user=instance)
        
        # Always create verification record
        UserVerification.objects.create(user=instance)
        
        # Create specific profile based on user type
        if instance.user_type == 'customer':
            CustomerProfile.objects.create(user=instance)
        elif instance.user_type == 'vendor':
            VendorProfile.objects.create(
                user=instance,
                business_name=f"{instance.get_full_name()}'s Business",
                business_registration_number=f"REG_{instance.id}_{instance.username}"
            )
        elif instance.user_type == 'delivery':
            DeliveryProfile.objects.create(
                user=instance,
                drivers_license_number=f"DL_{instance.id}_{instance.username}"
            )
        elif instance.user_type in ['restaurant_staff', 'restaurant_manager', 'restaurant_owner']:
            StaffProfile.objects.create(
                user=instance,
                employee_id=f"EMP_{instance.id}_{instance.username}",
                position='staff' if instance.user_type == 'restaurant_staff' else instance.user_type.split('_')[1]
            )

@receiver(post_save, sender=CustomUser)
def save_user_profiles(sender, instance, **kwargs):
    """Ensure profiles exist when user is saved"""
    # Create UserProfile if it doesn't exist
    if not hasattr(instance, 'profile'):
        UserProfile.objects.create(user=instance)
    
    # Create UserVerification if it doesn't exist
    if not hasattr(instance, 'verification'):
        UserVerification.objects.create(user=instance)
    
    # Create type-specific profiles if they don't exist
    if instance.user_type == 'customer' and not hasattr(instance, 'customer_profile'):
        CustomerProfile.objects.create(user=instance)
    elif instance.user_type == 'vendor' and not hasattr(instance, 'vendor_profile'):
        VendorProfile.objects.create(
            user=instance,
            business_name=f"{instance.get_full_name()}'s Business",
            business_registration_number=f"REG_{instance.id}_{instance.username}"
        )
    elif instance.user_type == 'delivery' and not hasattr(instance, 'delivery_profile'):
        DeliveryProfile.objects.create(
            user=instance,
            drivers_license_number=f"DL_{instance.id}_{instance.username}"
        )
    elif (instance.user_type in ['restaurant_staff', 'restaurant_manager', 'restaurant_owner'] 
          and not hasattr(instance, 'staff_profile')):
        StaffProfile.objects.create(
            user=instance,
            employee_id=f"EMP_{instance.id}_{instance.username}",
            position='staff' if instance.user_type == 'restaurant_staff' else instance.user_type.split('_')[1]
        )