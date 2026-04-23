from rest_framework import serializers
from .models import Order, OrderItem, OrderTracking, Cart, CartItem
from apps.restaurants.serializers import MenuItemSerializer, RestaurantListSerializer
from apps.restaurants.models import MenuItem, OptionChoice
from django.contrib.auth import get_user_model
from decimal import Decimal, InvalidOperation
import uuid

User = get_user_model()


def normalize_customizations_for_menu_item(customizations, menu_item):
    """Normalize extras payload and validate choices belong to the selected menu item."""
    if customizations in (None, ''):
        return {}, Decimal('0')

    if not isinstance(customizations, dict):
        raise serializers.ValidationError({'customizations': 'Must be a JSON object.'})

    normalized = dict(customizations)
    raw_extras = normalized.get('extras')

    # Backward compatibility: convert option_choice_ids -> extras with quantity 1.
    if raw_extras is None and 'option_choice_ids' in normalized:
        option_choice_ids = normalized.get('option_choice_ids') or []
        if not isinstance(option_choice_ids, list):
            raise serializers.ValidationError({'customizations': 'option_choice_ids must be a list.'})
        raw_extras = [{'choice_id': choice_id, 'quantity': 1} for choice_id in option_choice_ids]

    if raw_extras is None:
        raw_extras = []

    if not isinstance(raw_extras, list):
        raise serializers.ValidationError({'customizations': 'extras must be a list.'})

    aggregated_quantities = {}
    for index, extra in enumerate(raw_extras):
        if isinstance(extra, int):
            choice_id = extra
            quantity = 1
        elif isinstance(extra, dict):
            choice_id = extra.get('choice_id', extra.get('id'))
            quantity = extra.get('quantity', 1)
        else:
            raise serializers.ValidationError({'customizations': f'extras[{index}] must be an object or integer choice id.'})

        if choice_id is None:
            raise serializers.ValidationError({'customizations': f'extras[{index}].choice_id is required.'})

        try:
            choice_id = int(choice_id)
            quantity = int(quantity)
        except (TypeError, ValueError):
            raise serializers.ValidationError({'customizations': f'extras[{index}] contains invalid numbers.'})

        if quantity < 1:
            raise serializers.ValidationError({'customizations': f'extras[{index}].quantity must be at least 1.'})

        aggregated_quantities[choice_id] = aggregated_quantities.get(choice_id, 0) + quantity

    if not aggregated_quantities:
        normalized['extras'] = []
        normalized.pop('option_choice_ids', None)
        return normalized, Decimal('0')

    choices = OptionChoice.objects.filter(
        id__in=list(aggregated_quantities.keys()),
        group__menu_item=menu_item,
    )
    choice_map = {choice.id: choice for choice in choices}

    invalid_choice_ids = [choice_id for choice_id in aggregated_quantities.keys() if choice_id not in choice_map]
    if invalid_choice_ids:
        raise serializers.ValidationError({
            'customizations': f'Invalid extras for this item: {sorted(invalid_choice_ids)}.'
        })

    extras_total = Decimal('0')
    normalized_extras = []
    for choice_id, quantity in sorted(aggregated_quantities.items(), key=lambda item: item[0]):
        choice = choice_map[choice_id]
        unit_price = choice.price_modifier
        line_total = unit_price * quantity
        extras_total += line_total
        normalized_extras.append({
            'choice_id': choice.id,
            'name': choice.name,
            'quantity': quantity,
            'unit_price': str(unit_price),
            'line_total': str(line_total),
        })

    normalized['extras'] = normalized_extras
    normalized.pop('option_choice_ids', None)
    return normalized, extras_total


def calculate_extras_total(customizations):
    if not isinstance(customizations, dict):
        return Decimal('0')

    extras = customizations.get('extras') or []
    if not isinstance(extras, list):
        return Decimal('0')

    total = Decimal('0')
    for extra in extras:
        if not isinstance(extra, dict):
            continue

        quantity = extra.get('quantity', 1)
        unit_price = extra.get('unit_price', extra.get('price_modifier', 0))
        try:
            quantity_dec = Decimal(str(int(quantity)))
            unit_price_dec = Decimal(str(unit_price))
        except (TypeError, ValueError, InvalidOperation):
            continue

        if quantity_dec > 0 and unit_price_dec > 0:
            total += quantity_dec * unit_price_dec

    return total


def merge_cart_item_customizations(existing_customizations, incoming_customizations, menu_item):
    existing_normalized, _ = normalize_customizations_for_menu_item(
        existing_customizations or {},
        menu_item,
    )
    incoming_normalized, _ = normalize_customizations_for_menu_item(
        incoming_customizations or {},
        menu_item,
    )

    merged = dict(existing_normalized)
    for key, value in incoming_normalized.items():
        if key != 'extras':
            merged[key] = value

    combined_quantities = {}
    for source in (existing_normalized.get('extras', []), incoming_normalized.get('extras', [])):
        for extra in source:
            if not isinstance(extra, dict):
                continue
            choice_id = extra.get('choice_id')
            quantity = extra.get('quantity', 1)
            try:
                choice_id = int(choice_id)
                quantity = int(quantity)
            except (TypeError, ValueError):
                continue
            if quantity < 1:
                continue
            combined_quantities[choice_id] = combined_quantities.get(choice_id, 0) + quantity

    merged['extras'] = [
        {'choice_id': choice_id, 'quantity': quantity}
        for choice_id, quantity in combined_quantities.items()
    ]
    final_customizations, _ = normalize_customizations_for_menu_item(merged, menu_item)
    return final_customizations

class OrderItemSerializer(serializers.ModelSerializer):
    menu_item = MenuItemSerializer(read_only=True)
    menu_item_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = OrderItem
        fields = [
            'id', 'menu_item', 'menu_item_id', 'quantity', 'unit_price',
            'total_price', 'special_instructions', 'customizations'
        ]
        read_only_fields = ['id', 'total_price']

class OrderTrackingSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderTracking
        fields = ['id', 'status', 'message', 'timestamp']
        read_only_fields = ['id', 'timestamp']

class OrderListSerializer(serializers.ModelSerializer):
    restaurant = RestaurantListSerializer(read_only=True)
    items_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'restaurant', 'status', 'total_amount',
            'items_count', 'estimated_delivery_time', 'created_at'
        ]

    def get_items_count(self, obj):
        return obj.items.count()

class OrderDetailSerializer(serializers.ModelSerializer):
    restaurant = RestaurantListSerializer(read_only=True)
    items = OrderItemSerializer(many=True, read_only=True)
    tracking = OrderTrackingSerializer(many=True, read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'restaurant', 'status', 'total_amount',
            'delivery_fee', 'tax_amount', 'tip_amount', 'delivery_address',
            'delivery_instructions', 'estimated_delivery_time', 
            'actual_delivery_time', 'payment_method', 'payment_status',
            'notes', 'items', 'tracking', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'order_number', 'created_at', 'updated_at'
        ]

class OrderCreateSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, write_only=True)
    restaurant_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Order
        fields = [
            'restaurant_id', 'delivery_address', 'delivery_instructions',
            'payment_method', 'notes', 'items', 'tip_amount'
        ]

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        restaurant_id = validated_data.pop('restaurant_id')
        
        # Generate order number
        validated_data['order_number'] = f"ORD-{uuid.uuid4().hex[:8].upper()}"
        validated_data['user'] = self.context['request'].user
        validated_data['restaurant_id'] = restaurant_id
        
        # Calculate totals
        subtotal = 0
        for item_data in items_data:
            menu_item = MenuItem.objects.get(id=item_data['menu_item_id'])
            normalized_customizations, extras_total = normalize_customizations_for_menu_item(
                item_data.get('customizations', {}),
                menu_item,
            )
            unit_price = menu_item.price + extras_total
            item_data['customizations'] = normalized_customizations
            item_data['unit_price'] = unit_price
            item_data['total_price'] = item_data['quantity'] * unit_price
            subtotal += item_data['total_price']
        
        # Add delivery fee and tax (simplified calculation)
        validated_data['delivery_fee'] = 5.00  # Fixed delivery fee
        validated_data['tax_amount'] = subtotal * 0.08  # 8% tax
        validated_data['total_amount'] = (
            subtotal + 
            validated_data['delivery_fee'] + 
            validated_data['tax_amount'] + 
            validated_data.get('tip_amount', 0)
        )
        
        order = Order.objects.create(**validated_data)
        
        # Create order items
        for item_data in items_data:
            OrderItem.objects.create(order=order, **item_data)
        
        # Create initial tracking entry
        OrderTracking.objects.create(
            order=order,
            status='pending',
            message='Order received and being processed'
        )
        
        return order

class CartItemSerializer(serializers.ModelSerializer):
    menu_item = MenuItemSerializer(read_only=True)
    menu_item_id = serializers.IntegerField(write_only=True)
    item_total = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = [
            'id', 'menu_item', 'menu_item_id', 'quantity', 
            'customizations', 'item_total', 'added_at'
        ]
        read_only_fields = ['id', 'added_at']

    def get_item_total(self, obj):
        extras_total = calculate_extras_total(obj.customizations)
        return obj.quantity * (obj.menu_item.price + extras_total)

class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    restaurant = RestaurantListSerializer(read_only=True)
    total_items = serializers.SerializerMethodField()
    cart_total = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = [
            'id', 'restaurant', 'items', 'total_items', 
            'cart_total', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_total_items(self, obj):
        return sum(item.quantity for item in obj.items.all())

    def get_cart_total(self, obj):
        return sum(
            item.quantity * (item.menu_item.price + calculate_extras_total(item.customizations))
            for item in obj.items.all()
        )

class AddToCartSerializer(serializers.Serializer):
    menu_item_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1, default=1)
    customizations = serializers.JSONField(required=False, default=dict)

    def validate(self, attrs):
        menu_item = MenuItem.objects.filter(id=attrs['menu_item_id']).first()
        if not menu_item:
            raise serializers.ValidationError({'menu_item_id': 'Menu item not found.'})

        normalized_customizations, _ = normalize_customizations_for_menu_item(
            attrs.get('customizations', {}),
            menu_item,
        )
        attrs['customizations'] = normalized_customizations
        return attrs

class UpdateCartItemSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=0, required=False)  # 0 means remove item
    customizations = serializers.JSONField(required=False)

    def validate(self, attrs):
        cart_item = self.context.get('cart_item')
        if 'quantity' not in attrs and 'customizations' not in attrs:
            raise serializers.ValidationError('Provide at least one of quantity or customizations.')

        if 'customizations' in attrs and cart_item:
            normalized_customizations, _ = normalize_customizations_for_menu_item(
                attrs.get('customizations', {}),
                cart_item.menu_item,
            )
            attrs['customizations'] = normalized_customizations
        return attrs