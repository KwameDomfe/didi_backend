from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PostViewSet, DiningGroupViewSet, FollowViewSet, NotificationViewSet, stream_notifications

router = DefaultRouter()
router.register(r'posts', PostViewSet, basename='post')
router.register(r'groups', DiningGroupViewSet, basename='group')
router.register(r'follow', FollowViewSet, basename='follow')
router.register(r'notifications', NotificationViewSet, basename='notification')

app_name = 'social'

urlpatterns = [
    path('notifications/stream/', stream_notifications, name='notification-stream'),
    path('', include(router.urls)),
]