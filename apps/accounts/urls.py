from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserViewSet, UserProfileViewSet, CustomAuthToken,
    login_user, register_user, logout_user, check_username_availability,
    check_email_availability, request_password_reset,
    verify_email, resend_verification_code, get_user_types
)

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'profiles', UserProfileViewSet)

app_name = 'accounts'

urlpatterns = [
    path('', include(router.urls)),
    
    # Authentication endpoints
    path('login/', login_user, name='login'),  # Email-based login
    path('register/', register_user, name='register'),  # New unified registration path
    path('auth/login/', CustomAuthToken.as_view(), name='token_login'),  # Username-based login
    path('auth/register/', register_user, name='register_legacy'),  # Legacy (to be deprecated)
    path('auth/logout/', logout_user, name='logout'),
    
    # User validation endpoints
    path('auth/check-username/', check_username_availability, name='check_username'),
    path('auth/check-email/', check_email_availability, name='check_email'),
    
    # Password management
    path('auth/request-password-reset/', request_password_reset, name='request_password_reset'),
    
    # Email verification
    path('auth/verify-email/', verify_email, name='verify_email'),
    path('auth/resend-verification/', resend_verification_code, name='resend_verification'),
    
    # User types
    path('auth/user-types/', get_user_types, name='user_types'),
]