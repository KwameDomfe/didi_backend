from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import PostViewSet

router = DefaultRouter()
router.register(r'posts', PostViewSet, basename='auth-post')

app_name = 'posts'

urlpatterns = [
    path('', include(router.urls)),
]
