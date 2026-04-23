from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from drf_spectacular.views import (
    SpectacularAPIView, 
    SpectacularRedocView, 
    SpectacularSwaggerView
)
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from apps.restaurants.views import (
  RestaurantViewSet,
  MenuCategoryViewSet,
  MenuItemViewSet,
  RestaurantReviewViewSet,
  OptionGroupViewSet,
  OptionChoiceViewSet,
  CuisineViewSet,
  RestaurantCommentViewSet,
)

@api_view(['GET'])
@permission_classes([AllowAny])
def api_root(request):
    return Response({
        'message': 'Welcome to The Restaurant API',
        'version': '1.0',
        'endpoints': {
            'restaurants': '/api/restaurants/',
            'orders': '/api/orders/',
            'posts': '/api/posts/',
            'accounts': '/api/accounts/',
            'social': '/api/social/',
            'auth': '/api/auth/',
            'docs': '/api/docs/',
            'test': '/api/test/'
        }
    })

router = DefaultRouter()
router.register(r'restaurants', RestaurantViewSet, basename='restaurant')
router.register(r'menu-items', MenuItemViewSet, basename='menuitem')
router.register(r'categories', MenuCategoryViewSet, basename='menucategory')
router.register(r'reviews', RestaurantReviewViewSet, basename='restaurantreview')
router.register(r'option-groups', OptionGroupViewSet, basename='optiongroup')
router.register(r'option-choices', OptionChoiceViewSet, basename='optionchoice')
router.register(r'cuisines', CuisineViewSet, basename='cuisine')
router.register(r'restaurant-comments', RestaurantCommentViewSet, basename='restaurant-comment')


urlpatterns = [

    path('', 
        api_root, 
        name='api-root'
    ),

    # Favicon to avoid 404 in browsers hitting backend root
    path('favicon.ico', 
        RedirectView.as_view(url='/static/favicon.ico', 
            permanent=True
        ),
    ),

    path('admin/', admin.site.urls),
    
    path('api/', 
        include(router.urls)
    ),
    
    path('api/auth/', include('djoser.urls')),
    path('api/auth/', include('djoser.urls.jwt')),
    path('api/accounts/', include('apps.accounts.urls')),
    path('api/orders/', include('apps.orders.urls')),
    path('api/posts/', include('apps.posts.urls')),
    path('api/social/', include('apps.social.urls')),
    
        # Social auth endpoints
        path('dj-rest-auth/', include('dj_rest_auth.urls')),
        path('dj-rest-auth/registration/', include('dj_rest_auth.registration.urls')),
        path('accounts/', include('allauth.urls')),

    # OpenAPI 3 documentation with Swagger UI
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL, 
        document_root=settings.MEDIA_ROOT
    )
    
