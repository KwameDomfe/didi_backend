from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    RestaurantViewSet, MenuCategoryViewSet, MenuItemViewSet,
    RestaurantReviewViewSet, OptionGroupViewSet, OptionChoiceViewSet, CuisineViewSet,
    RestaurantCommentViewSet
)

app_name = 'restaurants'

router = DefaultRouter()
router.register(r'restaurants', RestaurantViewSet, basename='restaurant')
router.register(r'menu-categories', MenuCategoryViewSet, basename='menu-category')
router.register(r'menu-items', MenuItemViewSet, basename='menu-item')
router.register(r'reviews', RestaurantReviewViewSet, basename='review')
router.register(r'option-groups', OptionGroupViewSet, basename='option-group')
router.register(r'option-choices', OptionChoiceViewSet, basename='option-choice')
router.register(r'cuisines', CuisineViewSet, basename='cuisine')
router.register(r'restaurant-comments', RestaurantCommentViewSet, basename='restaurant-comment')

urlpatterns = [
    path('', include(router.urls)),
]
