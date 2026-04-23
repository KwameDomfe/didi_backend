from rest_framework import viewsets, status, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Avg, Count
from django.http import Http404
from django.shortcuts import get_object_or_404
from .models import (
    Restaurant,
    MenuCategory,
    MenuItem,
    RestaurantReview,
    OptionGroup,
    OptionChoice,
    MenuItemLike,
    MenuItemComment,
    MenuItemShare,
    Cuisine,
    RestaurantLike,
    RestaurantComment,
)
from .serializers import (
    RestaurantListSerializer, RestaurantDetailSerializer,
    MenuCategorySerializer, MenuItemSerializer, RestaurantReviewSerializer,
    RestaurantSearchSerializer, RestaurantCreateSerializer,
    MenuItemCommentSerializer,
    RestaurantCommentSerializer,
    OptionGroupSerializer, OptionChoiceSerializer,
    CuisineSerializer
)

# Cuisine API
def _notify_restaurant_owner(restaurant, actor, notification_type, message, extra_data=None):
    """Notify a restaurant owner of an action by another user. Silently skipped for own actions."""
    owner = getattr(restaurant, 'owner', None)
    if owner is None or owner.id == actor.id:
        return
    try:
        from apps.social.models import Notification
        Notification.objects.create(
            recipient=owner,
            sender=actor,
            notification_type=notification_type,
            message=message,
            data={'restaurant_id': restaurant.id, 'restaurant_name': restaurant.name, **(extra_data or {})},
        )
    except Exception:
        pass


def _notify_menu_item_owner(menu_item, actor, notification_type, message, extra_data=None):
    """Notify the restaurant owner of an action on one of their menu items."""
    owner = getattr(menu_item.restaurant, 'owner', None)
    if owner is None or owner.id == actor.id:
        return
    try:
        from apps.social.models import Notification
        Notification.objects.create(
            recipient=owner,
            sender=actor,
            notification_type=notification_type,
            message=message,
            data={
                'menu_item_id': menu_item.id,
                'menu_item_name': menu_item.name,
                'restaurant_id': menu_item.restaurant_id,
                **(extra_data or {}),
            },
        )
    except Exception:
        pass


class IsAdminOrPlatformAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        if not request.user or not request.user.is_authenticated:
            return False
        return (
            request.user.is_staff
            or request.user.is_superuser
            or getattr(request.user, 'user_type', None) in ['platform_admin', 'vendor']
        )

class CuisineViewSet(viewsets.ModelViewSet):
    queryset = Cuisine.objects.all()
    serializer_class = CuisineSerializer
    permission_classes = [IsAdminOrPlatformAdmin]

class IsOwnerOrAdminOrReadOnly(permissions.BasePermission):
    """
    Custom permission:
    - Read permissions for everyone
    - Create permissions for vendors and admins
    - Edit/delete permissions only for owners or admins
    """
    def has_permission(self, request, view):
        # Allow read operations
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Create: allow vendors and admins
        if view.action == 'create':
            if not (request.user and request.user.is_authenticated):
                return False

            return (
                request.user.is_superuser
                or request.user.is_staff
                or request.user.user_type in [
                    'vendor', 'restaurant_manager', 'restaurant_owner', 'platform_admin'
                ]
            )
        
        # For update/delete, check object permission
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # Allow read operations
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Allow admins to edit anything
        if request.user.is_superuser or request.user.is_staff:
            return True

        if request.user.user_type == 'platform_admin':
            return True
        
        # Allow owners to edit their own restaurants
        return obj.owner == request.user

class RestaurantViewSet(viewsets.ModelViewSet):
    queryset = Restaurant.objects.filter(is_active=True)
    lookup_field = 'slug'
    http_method_names = ['get', 'post', 'put', 'patch', 'delete', 'head', 'options']
    permission_classes = [IsOwnerOrAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['cuisine', 'price_range']
    search_fields = ['name', 'description', 'address']
    ordering_fields = ['name', 'rating', 'created_at']
    ordering = ['-rating', 'name']

    def get_object(self):
        
        """
        Resolve restaurant by slug (default) and gracefully fall back to numeric id.
        This supports clients that still call /api/restaurants/<id>/.
        For write actions, owners can access their own inactive restaurants.
        """
        queryset = self.filter_queryset(self.get_queryset())
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        lookup_value = self.kwargs.get(lookup_url_kwarg)

        if lookup_value is None:
            return super().get_object()

        obj = queryset.filter(**{self.lookup_field: lookup_value}).first()

        if obj is None and str(lookup_value).isdigit():
            obj = queryset.filter(pk=int(lookup_value)).first()

        # For write operations, also check the owner's inactive restaurants
        if obj is None and self.action in ('update', 'partial_update', 'destroy'):
            if self.request.user and self.request.user.is_authenticated:
                owner_qs = Restaurant.objects.filter(owner=self.request.user)
                obj = owner_qs.filter(**{self.lookup_field: lookup_value}).first()
                if obj is None and str(lookup_value).isdigit():
                    obj = owner_qs.filter(pk=int(lookup_value)).first()

        if obj is None:
            raise Http404("No Restaurant matches the given query.")

        self.check_object_permissions(self.request, obj)
        return obj

    def get_serializer_class(self):
        if self.action == 'list':
            return RestaurantListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return RestaurantCreateSerializer
        return RestaurantDetailSerializer
    
    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
    
    @action(detail=False, methods=['get'], url_path='my-restaurants')
    def my_restaurants(self, request):
        """Get restaurants owned by the current user"""
        if not request.user.is_authenticated:
            return Response(
                {'error': 'Authentication required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        restaurants = Restaurant.objects.filter(owner=request.user)
        serializer = RestaurantListSerializer(
            restaurants, 
            many=True, 
            context={'request': request}
        )
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def search(self, request):
        """Advanced restaurant search"""
        search_serializer = RestaurantSearchSerializer(data=request.data)
        if not search_serializer.is_valid():
            return Response(
                search_serializer.errors, 
                status=status.HTTP_400_BAD_REQUEST
            )

        search_data = search_serializer.validated_data
        queryset = self.get_queryset()

        # Apply filters
        if search_data.get('query'):
            queryset = queryset.filter(
                Q(name__icontains=search_data['query']) |
                Q(description__icontains=search_data['query']) |
                Q(cuisine__name__icontains=search_data['query'])
            )

        if search_data.get('cuisine_type'):
            queryset = queryset.filter(cuisine__name__icontains=search_data['cuisine_type'])

        if search_data.get('price_range'):
            queryset = queryset.filter(price_range=search_data['price_range'])

        if search_data.get('min_rating'):
            queryset = queryset.filter(rating__gte=search_data['min_rating'])

        if search_data.get('features'):
            for feature in search_data['features']:
                queryset = queryset.filter(features__contains=[feature])

        # Apply ordering
        if search_data.get('ordering'):
            queryset = queryset.order_by(search_data['ordering'])

        # Paginate results
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = RestaurantListSerializer(
                page, 
                many=True
            )
            return self.get_paginated_response(serializer.data)

        serializer = RestaurantListSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='like',
            permission_classes=[permissions.IsAuthenticated])
    def like(self, request, slug=None):
        """Toggle like for a restaurant. Returns {liked, likes_count}."""
        restaurant = self.get_object()
        like_obj, created = RestaurantLike.objects.get_or_create(
            restaurant=restaurant, user=request.user
        )
        if not created:
            like_obj.delete()
            liked = False
        else:
            liked = True
            _notify_restaurant_owner(
                restaurant, request.user, 'restaurant_liked',
                f"{request.user.username} liked your restaurant “{restaurant.name}”",
            )
        likes_count = restaurant.likes.count()
        return Response({'liked': liked, 'likes_count': likes_count})

    @action(detail=True, methods=['get', 'post'], url_path='comments',
            permission_classes=[permissions.IsAuthenticatedOrReadOnly])
    def comments(self, request, slug=None):
        """List or create comments for a restaurant."""
        restaurant = self.get_object()

        if request.method == 'GET':
            qs = (
                restaurant.comments
                .filter(parent__isnull=True)
                .select_related('user')
                .prefetch_related('replies__user')
                .order_by('created_at')
            )
            serializer = RestaurantCommentSerializer(
                qs, many=True, context={'request': request}
            )
            return Response(serializer.data)

        if not request.user.is_authenticated:
            return Response(
                {'error': 'Authentication required'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        serializer = RestaurantCommentSerializer(
            data=request.data, context={'request': request}
        )
        if serializer.is_valid():
            serializer.save(restaurant=restaurant, user=request.user)
            _notify_restaurant_owner(
                restaurant, request.user, 'restaurant_commented',
                f"{request.user.username} commented on your restaurant “{restaurant.name}”",
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def menu(self, request, pk=None):
        """Get restaurant menu by categories"""
        restaurant = self.get_object()
        categories = restaurant.categories.prefetch_related('items').all()
        serializer = MenuCategorySerializer(categories, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='popular-cuisines')
    def popular_cuisines(self, request):
        """Get popular cuisines based on restaurant count and ratings"""
        from django.db.models import Count, Avg
        
        # Get cuisine types with restaurant count and average rating
        cuisines = (
            Restaurant.objects
            .filter(is_active=True)
            .values('cuisine__name')
            .annotate(
                restaurant_count=Count('id'),
                avg_rating=Avg('rating')
            )
            .filter(restaurant_count__gt=0)
            .order_by('-restaurant_count', '-avg_rating')
        )
        
        # Format the response with emojis for popular cuisines
        cuisine_emojis = {
            'Italian': '🍝',
            'Japanese': '🍣', 
            'Mexican': '🌮',
            'Indian': '🍛',
            'Chinese': '🥢',
            'American': '🍔',
            'French': '🥐',
            'Thai': '🍜',
            'Mediterranean': '🫒',
            'Korean': '🍲',
            'Vietnamese': '🍲',
            'Greek': '🥗',
            'Spanish': '🥘',
            'Turkish': '🥙',
        }
        
        popular_cuisines = []
        request = self.request
        for cuisine_data in cuisines:
            cuisine_name = cuisine_data['cuisine__name']
            cuisine_obj = Cuisine.objects.filter(name=cuisine_name).first()
            image_url = None
            if cuisine_obj and cuisine_obj.image:
                try:
                    image_url = request.build_absolute_uri(cuisine_obj.image.url)
                except Exception:
                    image_url = cuisine_obj.image.url
            popular_cuisines.append({
                'name': cuisine_name,
                'emoji': cuisine_emojis.get(cuisine_name, '🍽️'),
                'image': image_url,
                'restaurant_count': cuisine_data['restaurant_count'],
                'avg_rating': round(cuisine_data['avg_rating'] or 0, 1)
            })
        return Response(popular_cuisines)

    @action(detail=True, methods=['get', 'post'], permission_classes=[permissions.IsAuthenticatedOrReadOnly])
    def reviews(self, request, slug=None):
        """Get or create restaurant reviews"""
        restaurant = self.get_object()
        
        if request.method == 'GET':
            reviews = restaurant.reviews.select_related('user').all()
            serializer = RestaurantReviewSerializer(reviews, many=True)
            return Response(serializer.data)
        
        elif request.method == 'POST':
            serializer = RestaurantReviewSerializer(
                data=request.data,
                context={'request': request}
            )
            if serializer.is_valid():
                try:
                    serializer.save(restaurant=restaurant)
                except Exception as e:
                    if 'UNIQUE constraint' in str(e) or 'unique constraint' in str(e).lower():
                        return Response(
                            {'detail': 'You have already reviewed this restaurant. You can update your existing review instead.'},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                    raise
                
                # Update restaurant rating
                avg_rating = restaurant.reviews.aggregate(Avg('rating'))['rating__avg']
                restaurant.rating = round(avg_rating, 2) if avg_rating else 0
                restaurant.save()
                _notify_restaurant_owner(
                    restaurant, request.user, 'restaurant_reviewed',
                    f"{request.user.username} left a {request.data.get('rating', '')}\u2605 review on “{restaurant.name}”",
                    extra_data={'rating': request.data.get('rating')},
                )
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class IsCommentOwnerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return (
            obj.user == request.user
            or getattr(request.user, 'user_type', None) == 'platform_admin'
            or request.user.is_staff
        )


class RestaurantCommentViewSet(viewsets.ModelViewSet):
    serializer_class = RestaurantCommentSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsCommentOwnerOrReadOnly]
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['restaurant']

    def get_queryset(self):
        # Only return top-level comments (replies are nested inside each comment)
        qs = RestaurantComment.objects.filter(parent__isnull=True).select_related('user').prefetch_related(
            'replies__user'
        ).order_by('created_at')
        return qs

    def get_object(self):
        # For detail actions (retrieve/update/destroy) allow access to replies too
        queryset = RestaurantComment.objects.select_related('user').prefetch_related('replies__user')
        obj = get_object_or_404(queryset, pk=self.kwargs[self.lookup_field])
        self.check_object_permissions(self.request, obj)
        return obj

    def perform_create(self, serializer):
        restaurant_id = self.request.data.get('restaurant')
        parent_id = self.request.data.get('parent_id') or self.request.data.get('parent')
        kwargs = {'user': self.request.user}
        if restaurant_id and 'restaurant' not in serializer.validated_data:
            restaurant = Restaurant.objects.filter(pk=restaurant_id).first()
            if restaurant:
                kwargs['restaurant'] = restaurant
        if parent_id and 'parent' not in serializer.validated_data:
            parent = RestaurantComment.objects.filter(pk=parent_id).first()
            if parent:
                kwargs['parent'] = parent
                # Inherit restaurant from parent if not provided
                if 'restaurant' not in kwargs:
                    kwargs['restaurant'] = parent.restaurant
        serializer.save(**kwargs)


class IsRestaurantOwnerOrAdminOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        
        if request.user.user_type == 'platform_admin':
            return True
        
        # Check if user owns the restaurant
        return obj.restaurant.owner == request.user

class MenuCategoryViewSet(viewsets.ModelViewSet):
    queryset = MenuCategory.objects.all()
    serializer_class = MenuCategorySerializer
    http_method_names = ['get', 'post', 'put', 'patch', 'delete', 'head', 'options']
    permission_classes = [IsRestaurantOwnerOrAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['restaurant']

    def perform_create(self, serializer):
        restaurant_id = (
            self.request.data.get('restaurant')
            or self.request.data.get('restaurant_id')
            or self.request.query_params.get('restaurant')
        )

        if not restaurant_id:
            raise ValidationError({'restaurant': ['This field is required.']})

        try:
            restaurant = Restaurant.objects.get(pk=restaurant_id)
        except (Restaurant.DoesNotExist, ValueError, TypeError):
            raise ValidationError({'restaurant': ['Invalid restaurant id.']})

        user = self.request.user
        is_platform_admin = getattr(user, 'user_type', None) == 'platform_admin'
        if not is_platform_admin and restaurant.owner_id != user.id:
            raise ValidationError({'restaurant': ['You can only create categories for your own restaurant.']})

        serializer.save(restaurant=restaurant)

class MenuItemViewSet(viewsets.ModelViewSet):
    queryset = MenuItem.objects.filter(is_available=True).order_by('id')
    serializer_class = MenuItemSerializer
    permission_classes = [IsRestaurantOwnerOrAdminOrReadOnly]
    lookup_field = 'slug'
    http_method_names = ['get', 'post', 'put', 'patch', 'delete', 'head', 'options']
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['restaurant', 'category', 'is_vegetarian', 
        'is_vegan', 'is_gluten_free', 'spice_level'
    ]
    search_fields = ['name', 'description', 'ingredients']

    def get_object(self):
        """
        Resolve menu item by slug (default) and fall back to numeric id.
        This supports clients that call /api/menu-items/<id>/.
        """
        queryset = MenuItem.objects.select_related('restaurant').all()
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        lookup_value = self.kwargs.get(lookup_url_kwarg)

        if lookup_value is None:
            return super().get_object()

        obj = queryset.filter(**{self.lookup_field: lookup_value}).first()

        if obj is None and str(lookup_value).isdigit():
            obj = queryset.filter(pk=int(lookup_value)).first()

        if obj is None:
            raise Http404("No MenuItem matches the given query.")

        # Keep unavailable items hidden from anonymous/public read requests.
        if self.request.method in permissions.SAFE_METHODS and not obj.is_available:
            user = self.request.user
            can_view_unavailable = (
                user.is_authenticated and (
                    user.is_superuser
                    or user.is_staff
                    or getattr(user, 'user_type', None) == 'platform_admin'
                    or obj.restaurant.owner_id == user.id
                )
            )
            if not can_view_unavailable:
                raise Http404("No MenuItem matches the given query.")

        self.check_object_permissions(self.request, obj)
        return obj
    
    def get_queryset(self):
        """Show all items to owners/admins, only available items to others"""
        user = self.request.user
        if user.is_authenticated and user.user_type in ['vendor', 'platform_admin']:
            if self.action in ['list', 'retrieve']:
                # For listing, still filter by is_available unless they own the restaurant
                restaurant_id = self.request.query_params.get('restaurant')
                if restaurant_id:
                    try:
                        restaurant = Restaurant.objects.get(id=restaurant_id)
                        if restaurant.owner == user or user.user_type == 'platform_admin':
                            return MenuItem.objects.filter(restaurant=restaurant).order_by('id')
                    except Restaurant.DoesNotExist:
                        pass
        return MenuItem.objects.filter(is_available=True).order_by('id')

    @action(detail=True, methods=['post', 'delete'], permission_classes=[permissions.IsAuthenticated])
    def like(self, request, slug=None):
        """Like or unlike a menu item."""
        menu_item = self.get_object()
        user = request.user

        if request.method == 'POST':
            _, created = MenuItemLike.objects.get_or_create(menu_item=menu_item, user=user)
            if not created:
                # Toggle behavior: POST again removes an existing like.
                MenuItemLike.objects.filter(menu_item=menu_item, user=user).delete()
                return Response({'liked': False, 'likes_count': menu_item.menu_item_likes.count()})
            _notify_menu_item_owner(
                menu_item, user, 'menu_item_liked',
                f"{user.username} liked your menu item “{menu_item.name}”",
            )
            return Response({'liked': True, 'likes_count': menu_item.menu_item_likes.count()})

        deleted, _ = MenuItemLike.objects.filter(menu_item=menu_item, user=user).delete()
        if deleted == 0:
            return Response({'detail': 'Like not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'liked': False, 'likes_count': menu_item.menu_item_likes.count()})

    @action(
        detail=True,
        methods=['get', 'post'],
        url_path='comments',
        permission_classes=[permissions.IsAuthenticatedOrReadOnly],
    )
    def comments(self, request, slug=None):
        """Get or create comments for a menu item."""
        menu_item = self.get_object()

        if request.method == 'GET':
            queryset = menu_item.menu_item_comments.select_related('user').all()
            serializer = MenuItemCommentSerializer(queryset, many=True, context={'request': request})
            return Response({'count': queryset.count(), 'results': serializer.data})

        if not request.user.is_authenticated:
            return Response({'detail': 'Authentication credentials were not provided.'}, status=status.HTTP_401_UNAUTHORIZED)

        text = (
            request.data.get('comment')
            or request.data.get('content')
            or request.data.get('text')
            or ''
        ).strip()
        if not text:
            return Response({'comment': ['This field is required.']}, status=status.HTTP_400_BAD_REQUEST)

        comment = MenuItemComment.objects.create(menu_item=menu_item, user=request.user, comment=text)
        _notify_menu_item_owner(
            menu_item, request.user, 'menu_item_commented',
            f"{request.user.username} commented on your menu item “{menu_item.name}”",
        )
        serializer = MenuItemCommentSerializer(comment, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(
        detail=True,
        methods=['patch', 'delete'],
        url_path=r'comments/(?P<comment_id>[^/.]+)',
        permission_classes=[permissions.IsAuthenticated],
    )
    def delete_comment(self, request, slug=None, comment_id: int = None):
        """Update or delete a menu item comment (author or admin only)."""
        menu_item = self.get_object()
        try:
            comment = MenuItemComment.objects.get(id=comment_id, menu_item=menu_item)
        except MenuItemComment.DoesNotExist:
            return Response({'detail': 'Comment not found.'}, status=status.HTTP_404_NOT_FOUND)

        can_manage = (
            comment.user_id == request.user.id
            or request.user.is_superuser
            or request.user.is_staff
            or getattr(request.user, 'user_type', '') == 'platform_admin'
        )
        if not can_manage:
            return Response({'detail': 'You can only manage your own comment.'}, status=status.HTTP_403_FORBIDDEN)

        if request.method == 'PATCH':
            text = (
                request.data.get('comment')
                or request.data.get('content')
                or request.data.get('text')
                or ''
            ).strip()
            if not text:
                return Response({'comment': ['This field is required.']}, status=status.HTTP_400_BAD_REQUEST)

            comment.comment = text
            comment.save(update_fields=['comment', 'updated_at'])
            serializer = MenuItemCommentSerializer(comment, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)

        comment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def share(self, request, slug=None):
        """Record that a menu item was shared."""
        menu_item = self.get_object()
        user = request.user if request.user.is_authenticated else None
        MenuItemShare.objects.create(menu_item=menu_item, user=user)
        if user:
            _notify_menu_item_owner(
                menu_item, user, 'menu_item_shared',
                f"{user.username} shared your menu item “{menu_item.name}”",
            )
        return Response({'detail': 'Share recorded.'}, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], url_path='meal-periods')
    def by_meal_period(self, request):
        """Get menu items grouped by meal period"""
        # Get distinct meal periods from categories that have items
        categories = MenuCategory.objects.filter(
            items__is_available=True
        ).distinct().select_related('restaurant').prefetch_related('items')
        
        # Group items by meal period
        meal_periods_data = {
            'breakfast': [],
            'brunch': [],
            'lunch': [],
            'supper': [],
            'dinner': [],
            'all_day': []
        }
        
        for category in categories:
            meal_period = category.meal_period
            if meal_period in meal_periods_data:
                items = category.items.filter(is_available=True)
                serialized_items = MenuItemSerializer(
                    items, 
                    many=True, 
                    context={'request': request}
                ).data
                meal_periods_data[meal_period].extend(serialized_items)
        
        # Format response with display names and emojis
        response_data = []
        meal_period_info = {
            'breakfast': {
                'name': 'Breakfast', 
                'emoji': '🌅',
                'time': '7:00 AM - 11:00 AM'},
            'brunch': {
                'name': 'Brunch', 
                'emoji': '🥞',
                'time': '10:00 AM - 2:00 PM'
            },
            'lunch': {
                'name': 'Lunch', 
                'emoji': '🌤️',
                'time': '11:30 AM - 3:00 PM'
            },
            'supper': {
                'name': 'Supper', 
                'emoji': '🌆',
                'time': '5:00 PM - 7:00 PM'
            },
            'dinner': {
                'name': 'Dinner', 
                'emoji': '🌙',
                'time': '6:00 PM - 10:00 PM'
            },
            'all_day': {
                'name': 'All Day', 
                'emoji': '⭐',
                'time': 'Available All Day'
            }
        }
        
        for period_key, items in meal_periods_data.items():
            if items:  # Only include periods with available items
                info = meal_period_info[period_key]
                response_data.append({
                    'period': period_key,
                    'name': info['name'],
                    'emoji': info['emoji'],
                    'time': info['time'],
                    'items': items
                })
        
        return Response(response_data)

    @action(detail=False, methods=['get'])
    def dietary_filters(self, request):
        """Get menu items based on dietary preferences"""
        queryset = self.get_queryset()
        
        if request.query_params.get('vegetarian'):
            queryset = queryset.filter(is_vegetarian=True)
        if request.query_params.get('vegan'):
            queryset = queryset.filter(is_vegan=True)
        if request.query_params.get('gluten_free'):
            queryset = queryset.filter(is_gluten_free=True)
        
        max_spice = request.query_params.get('max_spice_level')
        if max_spice:
            queryset = queryset.filter(spice_level__lte=int(max_spice))

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

class RestaurantReviewViewSet(viewsets.ModelViewSet):
    queryset = RestaurantReview.objects.select_related('user', 'restaurant')
    serializer_class = RestaurantReviewSerializer
    http_method_names = ['get', 'post', 'put', 'patch', 'delete', 'head', 'options']
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['restaurant', 'rating']
    ordering_fields = ['created_at', 'rating']
    ordering = ['-created_at']

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_queryset(self):
        if self.action in ['update', 'partial_update', 'destroy']:
            return self.queryset.filter(user=self.request.user)
        return self.queryset


class IsMenuItemOwnerOrAdminOrReadOnly(permissions.BasePermission):
    """Allow read to anyone; write only to the restaurant owner or admins."""
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        if request.user.is_superuser or request.user.is_staff or getattr(request.user, 'user_type', '') == 'platform_admin':
            return True
        # obj is OptionGroup; check restaurant ownership
        restaurant = obj.menu_item.restaurant if hasattr(obj, 'menu_item') else obj.group.menu_item.restaurant
        return restaurant.owner == request.user


class OptionGroupViewSet(viewsets.ModelViewSet):
    """
    CRUD for option groups attached to menu items.

    Filter by menu item:  GET /api/option-groups/?menu_item=<id>
    """
    serializer_class = OptionGroupSerializer
    permission_classes = [IsMenuItemOwnerOrAdminOrReadOnly]
    queryset = OptionGroup.objects.prefetch_related('choices').all()
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['menu_item']

    def get_queryset(self):
        qs = super().get_queryset()
        menu_item = self.request.query_params.get('menu_item')
        if menu_item:
            qs = qs.filter(menu_item=menu_item)
        return qs


class OptionChoiceViewSet(viewsets.ModelViewSet):
    """
    CRUD for individual choices within an option group.

    Filter by group:  GET /api/option-choices/?group=<id>
    """
    serializer_class = OptionChoiceSerializer
    permission_classes = [IsMenuItemOwnerOrAdminOrReadOnly]
    queryset = OptionChoice.objects.all()
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['group']

    def get_queryset(self):
        qs = super().get_queryset()
        group = self.request.query_params.get('group')
        if group:
            qs = qs.filter(group=group)
        return qs
