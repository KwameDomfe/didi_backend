from django.contrib import admin
from .models import Order, OrderItem, OrderTracking, Cart, CartItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1
    readonly_fields = ('total_price',)
    fields = ('menu_item', 'quantity', 'unit_price', 'total_price', 'special_instructions')


class OrderTrackingInline(admin.TabularInline):
    model = OrderTracking
    extra = 0
    readonly_fields = ('timestamp',)
    fields = ('status', 'message', 'timestamp')
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'user', 'restaurant', 'status', 'total_amount', 'created_at')
    list_filter = ('status', 'payment_status', 'created_at', 'restaurant')
    search_fields = ('order_number', 'user__username', 'user__email', 'restaurant__name')
    readonly_fields = ('order_number', 'created_at', 'updated_at')
    fieldsets = (
        ('Order Information', {
            'fields': ('order_number', 'user', 'restaurant', 'status')
        }),
        ('Amount Details', {
            'fields': ('total_amount', 'delivery_fee', 'tax_amount', 'tip_amount')
        }),
        ('Delivery Information', {
            'fields': ('delivery_address', 'delivery_instructions', 'estimated_delivery_time', 'actual_delivery_time')
        }),
        ('Payment Information', {
            'fields': ('payment_method', 'payment_status')
        }),
        ('Additional Information', {
            'fields': ('notes', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    inlines = [OrderItemInline, OrderTrackingInline]


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 1
    fields = ('menu_item', 'quantity', 'customizations')


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('user', 'restaurant', 'created_at', 'updated_at')
    list_filter = ('created_at', 'restaurant')
    search_fields = ('user__username', 'user__email', 'restaurant__name')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [CartItemInline]


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'menu_item', 'quantity', 'unit_price', 'total_price')
    list_filter = ('order__created_at', 'menu_item')
    search_fields = ('order__order_number', 'menu_item__name')
    readonly_fields = ('total_price',)


@admin.register(OrderTracking)
class OrderTrackingAdmin(admin.ModelAdmin):
    list_display = ('order', 'status', 'message', 'timestamp')
    list_filter = ('status', 'timestamp')
    search_fields = ('order__order_number', 'status')
    readonly_fields = ('timestamp',)


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('cart', 'menu_item', 'quantity', 'added_at')
    list_filter = ('added_at', 'menu_item')
    search_fields = ('cart__user__username', 'menu_item__name')
