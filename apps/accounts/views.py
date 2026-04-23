from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings
from django.utils.crypto import get_random_string
from django.utils import timezone
from datetime import timedelta
from .models import (
    UserProfile, CustomerProfile, VendorProfile, 
    DeliveryProfile, StaffProfile, UserVerification
)
from .serializers import (
    UserSerializer, UserProfileSerializer, PublicUserSerializer, 
    UserStatsSerializer, UserRegistrationSerializer, UserProfileUpdateSerializer
)

User = get_user_model()

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.action == 'list':
            # Only allow users to see other users in public context
            return User.objects.filter(is_active=True)
        return User.objects.all()

    def get_serializer_class(self):
        if self.action == 'list':
            return PublicUserSerializer

        if self.action == 'retrieve':
            target_user = self.get_object()
            if self.request.user != target_user:
                return PublicUserSerializer

        if self.action == 'stats':
            return UserStatsSerializer

        return UserSerializer

    def get_permissions(self):
        if self.action == 'create':
            permission_classes = [permissions.AllowAny]
        elif self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [permissions.IsAuthenticated]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]

    @action(detail=False, methods=['get', 'put', 'patch'])
    def me(self, request):
        """Get or update current user's profile"""
        if request.method == 'GET':
            serializer = self.get_serializer(request.user)
            return Response(serializer.data)
        
        serializer = self.get_serializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """Get user statistics"""
        user = self.get_object()
        serializer = UserStatsSerializer(user)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def change_password(self, request):
        """Change user password"""
        user = request.user
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')
        
        if not user.check_password(old_password):
            return Response({'error': 'Invalid old password'}, status=status.HTTP_400_BAD_REQUEST)
        
        user.set_password(new_password)
        user.save()
        return Response({'message': 'Password changed successfully'})

class UserProfileViewSet(viewsets.ModelViewSet):
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return UserProfile.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

# Authentication Views
class CustomAuthToken(ObtainAuthToken):
    """Enhanced login view that returns user information along with token"""
    
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        
        # Update last login IP
        user.last_login_ip = self.get_client_ip(request)
        user.save(update_fields=['last_login_ip'])
        
        # Return comprehensive user data
        user_serializer = UserSerializer(user)
        return Response({
            'token': token.key,
            'user': user_serializer.data,
            'message': 'Login successful'
        })
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def login_user(request):
    """Login user with email and password"""
    email = request.data.get('email')
    password = request.data.get('password')
    
    if not email or not password:
        return Response({'error': 'Email and password are required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
    
    if not user.check_password(password):
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
    
    if not user.is_active:
        return Response({'error': 'Account is not active'}, status=status.HTTP_403_FORBIDDEN)
    
    # Create or get token
    token, created = Token.objects.get_or_create(user=user)
    
    # Return user data and token
    user_serializer = UserSerializer(user)
    return Response({
        'token': token.key,
        'user': user_serializer.data,
        'message': 'Login successful'
    }, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def register_user(request):
    """Register a new user with specified user type"""
    
    serializer = UserRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        
        # Create authentication token
        token, created = Token.objects.get_or_create(user=user)
        
        # Send welcome email based on user type
        send_welcome_email(user)
        
        # Send verification email
        verification_sent = send_verification_email(user)
        
        # Return user data and token
        user_serializer = UserSerializer(user)
        return Response({
            'token': token.key,
            'user': user_serializer.data,
            'message': f'{user.get_user_type_display()} account created successfully!',
            'verification_email_sent': verification_sent,
            'requires_verification': True
        }, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def logout_user(request):
    """Logout user by deleting their auth token"""
    try:
        request.user.auth_token.delete()
        return Response({'message': 'Logout successful'}, status=status.HTTP_200_OK)
    except:
        return Response({'error': 'Logout failed'}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def check_username_availability(request):
    """Check if username is available"""
    username = request.data.get('username')
    if not username:
        return Response({'error': 'Username is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    is_available = not User.objects.filter(username=username).exists()
    return Response({
        'username': username,
        'available': is_available,
        'message': 'Username is available' if is_available else 'Username is already taken'
    })

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def check_email_availability(request):
    """Check if email is available"""
    email = request.data.get('email')
    if not email:
        return Response({'error': 'Email is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    is_available = not User.objects.filter(email=email).exists()
    return Response({
        'email': email,
        'available': is_available,
        'message': 'Email is available' if is_available else 'Email is already registered'
    })

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def request_password_reset(request):
    """Request password reset for user"""
    email = request.data.get('email')
    if not email:
        return Response({'error': 'Email is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        user = User.objects.get(email=email)
        # Generate reset token (in production, use a more secure method)
        reset_token = get_random_string(32)
        
        # Store token in user profile or separate model (simplified for demo)
        # In production, you'd want a separate PasswordReset model with expiry
        
        # Send password reset email
        send_password_reset_email(user, reset_token)
        
        return Response({
            'message': 'Password reset email sent successfully',
            'email': email
        })
    except User.DoesNotExist:
        # Don't reveal that email doesn't exist for security
        return Response({
            'message': 'If this email is registered, you will receive a password reset link',
            'email': email
        })

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def verify_email(request):
    """Verify user's email address using verification code"""
    code = request.data.get('code')
    email = request.data.get('email')
    
    if not code or not email:
        return Response({
            'error': 'Verification code and email are required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        user = User.objects.get(email=email)
        
        # Check if already verified
        if user.email_verified:
            return Response({
                'message': 'Email already verified',
                'email': email
            })
        
        # Get verification record
        try:
            verification = user.verification
        except:
            return Response({
                'error': 'No verification record found'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if code matches and not expired
        if verification.email_verification_code != code:
            return Response({
                'error': 'Invalid verification code'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if verification.code_expires_at and verification.code_expires_at < timezone.now():
            return Response({
                'error': 'Verification code has expired'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Mark email as verified
        user.email_verified = True
        user.email_verified_at = timezone.now()
        user.save(update_fields=['email_verified', 'email_verified_at'])
        
        # Clear verification code
        verification.email_verification_code = ''
        verification.save()
        
        return Response({
            'message': 'Email verified successfully',
            'email': email
        })
    except User.DoesNotExist:
        return Response({
            'error': 'User not found'
        }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def resend_verification_code(request):
    """Resend verification code to user's email"""
    email = request.data.get('email')
    
    if not email:
        return Response({
            'error': 'Email is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        user = User.objects.get(email=email)
        
        # Check if already verified
        if user.email_verified:
            return Response({
                'message': 'Email already verified'
            })
        
        # Send verification email
        verification_sent = send_verification_email(user)
        
        if verification_sent:
            return Response({
                'message': 'Verification code sent successfully',
                'email': email
            })
        else:
            return Response({
                'error': 'Failed to send verification code'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except User.DoesNotExist:
        return Response({
            'error': 'User not found'
        }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def get_user_types(request):
    """Get available user types for registration"""
    user_types = [
        {
            'value': choice[0],
            'label': choice[1],
            'description': get_user_type_description(choice[0])
        }
        for choice in User.USER_TYPES
    ]
    
    return Response({
        'user_types': user_types,
        'default': 'customer'
    })

def get_user_type_description(user_type):
    """Get description for each user type"""
    descriptions = {
        'customer': 'Order food from restaurants and enjoy delivery services',
        'vendor': 'Own and manage restaurants, create menus, and handle orders',
        'delivery': 'Deliver orders to customers and earn money',
        'restaurant_staff': 'Work in restaurants as chef, server, cashier, etc.',
        'restaurant_manager': 'Manage restaurant operations and staff',
        'restaurant_owner': 'Own multiple restaurants and manage business',
        'platform_admin': 'Administer the entire platform and manage users',
        'support_agent': 'Help customers with their questions and issues',
        'content_moderator': 'Review and moderate content on the platform',
        'marketing_specialist': 'Create marketing campaigns and promotions',
        'finance_manager': 'Manage financial operations and reporting',
        'data_analyst': 'Analyze data and create business insights',
    }
    return descriptions.get(user_type, 'Platform user')

def send_welcome_email(user):
    """Send welcome email based on user type"""
    subject_templates = {
        'customer': 'Welcome to The Restaurant - Start Ordering!',
        'vendor': 'Welcome to The Restaurant - Grow Your Business!',
        'delivery': 'Welcome to The Restaurant - Start Delivering!',
        'restaurant_staff': 'Welcome to The Restaurant Team!',
        'restaurant_manager': 'Welcome to The Restaurant Management!',
        'restaurant_owner': 'Welcome to The Restaurant Partnership!',
        'platform_admin': 'Admin Access Granted - The Restaurant Platform',
        'support_agent': 'Customer Support Role Activated',
        'content_moderator': 'Content Moderator Access Granted',
        'marketing_specialist': 'Marketing Team Access Activated',
        'finance_manager': 'Finance Management Access Granted',
        'data_analyst': 'Data Analytics Access Activated',
    }
    
    message_templates = {
        'customer': f'Hi {user.get_full_name()},\n\nWelcome to The Restaurant! You can now browse restaurants, order food, and track deliveries.\n\nEnjoy your meals!',
        'vendor': f'Hi {user.get_full_name()},\n\nWelcome to The Restaurant platform! You can now set up your restaurant, create menus, and start receiving orders.\n\nLet\'s grow your business together!',
        'delivery': f'Hi {user.get_full_name()},\n\nWelcome to The Restaurant delivery team! Complete your profile setup to start accepting delivery requests.\n\nStart earning today!',
        # Add more templates for other user types...
    }
    
    subject = subject_templates.get(user.user_type, 'Welcome to The Restaurant!')
    message = message_templates.get(user.user_type, f'Welcome to The Restaurant, {user.get_full_name()}!')
    
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=True,
        )
    except:
        # Email sending failed, but don't break registration
        pass

def send_verification_email(user):
    """Send email verification code to user"""
    # Generate 6-digit verification code
    verification_code = get_random_string(6, allowed_chars='0123456789')
    
    # Store verification code
    try:
        verification = user.verification
    except:
        verification = UserVerification.objects.create(user=user)
    
    # Store code and expiry (you'll need to add these fields to UserVerification model)
    verification.email_verification_code = verification_code
    verification.code_expires_at = timezone.now() + timedelta(hours=24)
    verification.save()
    
    subject = 'Verify Your Email - The Restaurant'
    message = f'''
Hi {user.get_full_name()},

Thank you for registering with The Restaurant!

Your verification code is: {verification_code}

This code will expire in 24 hours.

Alternatively, you can verify your email by clicking the link below:
{getattr(settings, 'FRONTEND_URL', 'http://localhost:5173')}/verify-email?code={verification_code}&email={user.email}

Best regards,
The Restaurant Team
'''
    
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Failed to send verification email: {e}")
        return False

def send_password_reset_email(user, reset_token):
    """Send password reset email"""
    subject = 'Password Reset - The Restaurant'
    message = f'''
Hi {user.get_full_name()},

You requested a password reset for your The Restaurant account.

Click the link below to reset your password:
{settings.FRONTEND_URL}/reset-password?token={reset_token}&email={user.email}

If you didn't request this, please ignore this email.

Best regards,
The Restaurant Team
'''
    
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=True,
        )
    except:
        # Email sending failed
        pass
