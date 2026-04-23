from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from accounts.models import (
    UserProfile, CustomerProfile, VendorProfile, 
    DeliveryProfile, StaffProfile, UserVerification
)

User = get_user_model()

class Command(BaseCommand):
    help = 'Migrate existing users to the new multi-user type system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user-type',
            type=str,
            help='Default user type for existing users (default: customer)',
            default='customer'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes',
        )

    def handle(self, *args, **options):
        user_type = options['user_type']
        dry_run = options['dry_run']
        
        # Get users without profiles
        users_without_profiles = User.objects.filter(
            profile__isnull=True
        )
        
        users_without_verification = User.objects.filter(
            verification__isnull=True
        )
        
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f'DRY RUN MODE: Would migrate {users_without_profiles.count()} users to {user_type} type'
                )
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f'DRY RUN MODE: Would create verification records for {users_without_verification.count()} users'
                )
            )
            return
        
        self.stdout.write(f'Migrating users to user type: {user_type}')
        
        # Update existing users without user_type
        users_without_type = User.objects.filter(user_type='')
        if users_without_type.exists():
            count = users_without_type.update(user_type=user_type)
            self.stdout.write(
                self.style.SUCCESS(f'Updated {count} users with user_type = {user_type}')
            )
        
        # Create missing profiles
        created_profiles = 0
        for user in users_without_profiles:
            UserProfile.objects.create(user=user)
            created_profiles += 1
        
        if created_profiles > 0:
            self.stdout.write(
                self.style.SUCCESS(f'Created {created_profiles} UserProfile records')
            )
        
        # Create missing verification records
        created_verifications = 0
        for user in users_without_verification:
            UserVerification.objects.create(user=user)
            created_verifications += 1
        
        if created_verifications > 0:
            self.stdout.write(
                self.style.SUCCESS(f'Created {created_verifications} UserVerification records')
            )
        
        # Create type-specific profiles
        created_customer_profiles = 0
        created_vendor_profiles = 0
        created_delivery_profiles = 0
        created_staff_profiles = 0
        
        for user in User.objects.all():
            if user.user_type == 'customer' and not hasattr(user, 'customer_profile'):
                CustomerProfile.objects.create(user=user)
                created_customer_profiles += 1
            elif user.user_type == 'vendor' and not hasattr(user, 'vendor_profile'):
                VendorProfile.objects.create(
                    user=user,
                    business_name=f"{user.get_full_name()}'s Business" or f"{user.username}'s Business",
                    business_registration_number=f"REG_{user.id}_{user.username}"
                )
                created_vendor_profiles += 1
            elif user.user_type == 'delivery' and not hasattr(user, 'delivery_profile'):
                DeliveryProfile.objects.create(
                    user=user,
                    drivers_license_number=f"DL_{user.id}_{user.username}"
                )
                created_delivery_profiles += 1
            elif (user.user_type in ['restaurant_staff', 'restaurant_manager', 'restaurant_owner']
                  and not hasattr(user, 'staff_profile')):
                StaffProfile.objects.create(
                    user=user,
                    employee_id=f"EMP_{user.id}_{user.username}",
                    position='staff' if user.user_type == 'restaurant_staff' else user.user_type.split('_')[1]
                )
                created_staff_profiles += 1
        
        if created_customer_profiles > 0:
            self.stdout.write(
                self.style.SUCCESS(f'Created {created_customer_profiles} CustomerProfile records')
            )
        if created_vendor_profiles > 0:
            self.stdout.write(
                self.style.SUCCESS(f'Created {created_vendor_profiles} VendorProfile records')
            )
        if created_delivery_profiles > 0:
            self.stdout.write(
                self.style.SUCCESS(f'Created {created_delivery_profiles} DeliveryProfile records')
            )
        if created_staff_profiles > 0:
            self.stdout.write(
                self.style.SUCCESS(f'Created {created_staff_profiles} StaffProfile records')
            )
        
        self.stdout.write(
            self.style.SUCCESS('Migration completed successfully!')
        )