from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from .models import (
    Order, 
    OrderItem, 
    OrderTracking, 
    Cart, 
    CartItem
)
from apps.restaurants.models import MenuItem
from .serializers import (
    OrderListSerializer, 
    OrderDetailSerializer, 
    OrderCreateSerializer,
    CartSerializer, 
    CartItemSerializer, 
    AddToCartSerializer, 
    UpdateCartItemSerializer, 
    OrderTrackingSerializer,
)

class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.select_related('restaurant').all()
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'restaurant']
    ordering = ['-created_at']

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).select_related('restaurant')

    def get_serializer_class(self):
        if self.action == 'list':
            return OrderListSerializer
        elif self.action == 'create':
            return OrderCreateSerializer
        return OrderDetailSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['get'])
    def tracking(self, request, pk=None):
        """Get order tracking information"""
        order = self.get_object()
        tracking = order.tracking.all().order_by('-timestamp')
        serializer = OrderTrackingSerializer(tracking, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel an order"""
        order = self.get_object()
        
        if order.status in ['delivered', 'cancelled']:
            return Response(
                {'error': 'Cannot cancel this order'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        order.status = 'cancelled'
        order.save()
        
        # Add tracking entry
        OrderTracking.objects.create(
            order=order,
            status='cancelled',
            message='Order cancelled by customer'
        )
        
        return Response({'message': 'Order cancelled successfully'})

    @action(detail=False, methods=['post'])
    def checkout(self, request):
        """Create order from cart"""
        user = request.user
        
        try:
            cart = user.cart
        except Cart.DoesNotExist:
            return Response(
                {'error': 'Cart is empty'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not cart.items.exists():
            return Response(
                {'error': 'Cart is empty'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Convert cart to order data
        order_data = request.data.copy()
        order_data['restaurant_id'] = cart.restaurant.id
        order_data['items'] = [
            {
                'menu_item_id': item.menu_item.id,
                'quantity': item.quantity,
                'customizations': item.customizations
            }
            for item in cart.items.all()
        ]
        
        serializer = OrderCreateSerializer(
            data=order_data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            order = serializer.save()
            
            # Clear cart after successful order
            cart.items.all().delete()
            cart.restaurant = None
            cart.save()
            
            return Response(
                OrderDetailSerializer(order).data,
                status=status.HTTP_201_CREATED
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CartViewSet(viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def get_cart(self):
        cart, created = Cart.objects.get_or_create(user=self.request.user)
        return cart

    def _reset_cart_restaurant_if_empty(self, cart):
        if not cart.items.exists() and cart.restaurant_id is not None:
            cart.restaurant = None
            cart.save(update_fields=['restaurant', 'updated_at'])

    @action(detail=False, methods=['get'])
    def current(self, request):
        """Get current user's cart"""
        cart = self.get_cart()
        serializer = CartSerializer(cart)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def add_item(self, request):
        """Add item to cart"""
        serializer = AddToCartSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        menu_item = get_object_or_404(MenuItem, id=serializer.validated_data['menu_item_id'])
        cart = self.get_cart()

        # Check if cart has items from different restaurant
        if cart.restaurant and cart.restaurant != menu_item.restaurant:
            return Response(
                {
                    'error': 'Cannot add items from different restaurants. Please clear cart first.',
                    'current_restaurant': cart.restaurant.name,
                    'new_restaurant': menu_item.restaurant.name
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Set restaurant if cart is empty
        if not cart.restaurant:
            cart.restaurant = menu_item.restaurant
            cart.save()

        normalized_customizations = serializer.validated_data.get('customizations', {})

        # Add or update cart item. Same menu item + same customizations merge quantity.
        # Different customizations stay as separate cart lines.
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            menu_item=menu_item,
            customizations=normalized_customizations,
            defaults={
                'quantity': serializer.validated_data['quantity'],
                'customizations': normalized_customizations,
            }
        )

        if not created:
            cart_item.quantity += serializer.validated_data['quantity']
            cart_item.save()

        return Response(CartItemSerializer(cart_item).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['put'])
    def update_item(self, request):
        """Update cart item quantity"""
        item_id = request.data.get('item_id')
        if not item_id:
            return Response({'error': 'item_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        cart = self.get_cart()
        cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)

        serializer = UpdateCartItemSerializer(
            data=request.data,
            context={'cart_item': cart_item},
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        quantity = serializer.validated_data.get('quantity')

        if quantity == 0:
            cart_item.delete()
            self._reset_cart_restaurant_if_empty(cart)
            return Response({'message': 'Item removed from cart'})

        updated_customizations = serializer.validated_data.get('customizations', cart_item.customizations)

        duplicate_item = cart.items.filter(
            menu_item=cart_item.menu_item,
            customizations=updated_customizations,
        ).exclude(id=cart_item.id).first()

        if duplicate_item:
            if quantity is not None:
                duplicate_item.quantity += quantity
            duplicate_item.save()
            cart_item.delete()
            return Response(CartItemSerializer(duplicate_item).data)

        if quantity is not None:
            cart_item.quantity = quantity
        if 'customizations' in serializer.validated_data:
            cart_item.customizations = updated_customizations
        cart_item.save()

        return Response(CartItemSerializer(cart_item).data)

    @action(detail=False, methods=['delete'])
    def clear(self, request):
        """Clear entire cart"""
        cart = self.get_cart()
        cart.items.all().delete()
        cart.restaurant = None
        cart.save()
        return Response({'message': 'Cart cleared successfully'})

    @action(detail=False, methods=['delete'])
    def remove_item(self, request):
        """Remove specific item from cart"""
        item_id = request.query_params.get('item_id')
        if not item_id:
            return Response({'error': 'item_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        cart = self.get_cart()
        cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
        cart_item.delete()
        self._reset_cart_restaurant_if_empty(cart)

        return Response({'message': 'Item removed from cart'})
