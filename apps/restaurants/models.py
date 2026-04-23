from django.db import models
from django.contrib.auth import get_user_model

from django.utils.text import slugify

User = get_user_model()
class Cuisine(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='cuisines/', blank=True)

    class Meta:
        verbose_name_plural = 'Cuisines'
        ordering = ['name']

    def __str__(self):
        return self.name


class Restaurant(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_restaurants', limit_choices_to={'user_type__in': ['vendor', 'platform_admin']}, null=True, blank=True)
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    description = models.TextField()
    cuisine = models.ForeignKey('Cuisine', on_delete=models.SET_NULL, null=True, blank=True, related_name='restaurants')
    address = models.TextField()
    phone_number = models.CharField(max_length=15)
    email = models.EmailField()
    website = models.URLField(blank=True)
    image = models.ImageField(upload_to='restaurants/', blank=True)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.0)
    price_range = models.CharField(max_length=20, choices=[
        ('$', 'Budget'),
        ('$$', 'Moderate'),
        ('$$$', 'Expensive'),
        ('$$$$', 'Fine Dining')
    ])
    opening_hours = models.JSONField(default=dict, null=True, blank=True)  # e.g. {"Monday": "9am-9pm", "Tuesday": "9am-9pm", ...}  
    features = models.JSONField(default=list, null=True, blank=True)  # ['wifi', 'parking', 'delivery']
    delivery_fee = models.DecimalField(max_digits=6, decimal_places=2, default=2.99, help_text="Delivery fee in GHC")
    delivery_time = models.CharField(max_length=50, default="30-45 min", help_text="Estimated delivery time")
    min_order = models.DecimalField(max_digits=8, decimal_places=2, default=15.00, help_text="Minimum order amount in GHC")
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug and self.name:
            raw_base = slugify(self.name) or "restaurant"
            # Ensure base length leaves room for numeric suffixes
            base = raw_base[:240]
            candidate = base
            i = 1
            while Restaurant.objects.filter(slug=candidate).exclude(pk=self.pk).exists():
                i += 1
                suffix = f"-{i}"
                candidate = f"{base[:240-len(suffix)]}{suffix}"
            self.slug = candidate
        super().save(*args, **kwargs)

class MenuCategory(models.Model):
    MEAL_PERIOD_CHOICES = [
        ('breakfast', 'Breakfast'),
        ('brunch', 'Brunch'),
        ('lunch', 'Lunch'),
        ('supper', 'Supper'),
        ('dinner', 'Dinner'),
        ('all_day', 'All Day'),
    ]
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='categories')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='menu_categories/', blank=True)
    meal_period = models.CharField(max_length=20, choices=MEAL_PERIOD_CHOICES, default='all_day')
    display_order = models.IntegerField(default=0)

    class Meta:
        ordering = ['display_order']
        verbose_name_plural = 'Menu Categories'

    def __str__(self):
        return f"{self.restaurant.name} - {self.name}"

class MenuItem(models.Model):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='menu_items')
    category = models.ForeignKey(MenuCategory, on_delete=models.CASCADE, related_name='items')
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=8, decimal_places=2)
    image = models.ImageField(upload_to='menu_items/', blank=True)
    # ingredients: list of objects {name, quantity, unit, notes}
    # ingredients = models.JSONField(
    #     default=list, 
    #     help_text="List of ingredients as objects: [{name, quantity, unit, notes}]"
    # )
    allergens = models.JSONField(default=list)
    nutritional_info = models.JSONField(default=dict)
    is_available = models.BooleanField(default=True)
    is_vegetarian = models.BooleanField(default=False)
    is_vegan = models.BooleanField(default=False)
    is_gluten_free = models.BooleanField(default=False)
    spice_level = models.IntegerField(default=0, choices=[(i, i) for i in range(6)])
    prep_time = models.IntegerField(help_text="Preparation time in minutes", null=True, blank=True, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.restaurant.name} - {self.name}"

    def save(self, *args, **kwargs):
        if not self.slug and self.name:
            base_parts = []
            if self.restaurant_id and hasattr(self, 'restaurant') and self.restaurant and self.restaurant.name:
                base_parts.append(self.restaurant.name)
            base_parts.append(self.name)
            raw_base = slugify("-".join(base_parts)) or "menu-item"
            base = raw_base[:240]
            candidate = base
            i = 1
            while MenuItem.objects.filter(slug=candidate).exclude(pk=self.pk).exists():
                i += 1
                suffix = f"-{i}"
                candidate = f"{base[:240-len(suffix)]}{suffix}"
            self.slug = candidate
        super().save(*args, **kwargs)

class OptionGroup(models.Model):
    """
    A named group of choices the customer must/may select when ordering a MenuItem.
    e.g. "Choose your size", "Add-ons", "Cooking preference"
    """
    menu_item = models.ForeignKey(
        MenuItem, on_delete=models.CASCADE, related_name='option_groups'
    )
    name = models.CharField(max_length=100)
    required = models.BooleanField(
        default=False,
        help_text="Customer must make a selection in this group before adding to cart"
    )
    min_selections = models.PositiveSmallIntegerField(
        default=1,
        help_text="Minimum number of choices the customer must select (when required)"
    )
    max_selections = models.PositiveSmallIntegerField(
        default=1,
        help_text="Maximum choices allowed. 1 = radio buttons; >1 = checkboxes"
    )

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.menu_item.name} – {self.name}"


class OptionChoice(models.Model):
    """
    A single selectable choice inside an OptionGroup.
    e.g. "Large (+₵2.00)", "Extra cheese (+₵1.50)", "No onions"
    """
    group = models.ForeignKey(
        OptionGroup, on_delete=models.CASCADE, related_name='choices'
    )
    name = models.CharField(max_length=100)
    price_modifier = models.DecimalField(
        max_digits=8, decimal_places=2, default=0,
        help_text="Extra cost added to the base item price when this choice is selected"
    )

    class Meta:
        ordering = ['id']

    def __str__(self):
        modifier = f"+{self.price_modifier}" if self.price_modifier else "included"
        return f"{self.group.name}: {self.name} ({modifier})"


class RestaurantReview(models.Model):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    comment = models.TextField()
    images = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['restaurant', 'user']

    def __str__(self):
        return f"{self.user.username} - {self.restaurant.name} ({self.rating}/5)"


class MenuItemLike(models.Model):
    menu_item = models.ForeignKey(MenuItem, on_delete=models.CASCADE, related_name='menu_item_likes')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='menu_item_likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['menu_item', 'user']

    def __str__(self):
        return f"{self.user.username} likes {self.menu_item.name}"


class MenuItemComment(models.Model):
    menu_item = models.ForeignKey(MenuItem, on_delete=models.CASCADE, related_name='menu_item_comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='menu_item_comments')
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} commented on {self.menu_item.name}"


class MenuItemShare(models.Model):
    menu_item = models.ForeignKey(MenuItem, on_delete=models.CASCADE, related_name='menu_item_shares')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='menu_item_shares', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        username = self.user.username if self.user_id else 'anonymous'
        return f"{username} shared {self.menu_item.name}"


class RestaurantLike(models.Model):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='likes')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='restaurant_likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['restaurant', 'user']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} likes {self.restaurant.name}"


class RestaurantComment(models.Model):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='restaurant_comments')
    parent = models.ForeignKey(
        'self', null=True, blank=True, on_delete=models.CASCADE, related_name='replies'
    )
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.user.username} on {self.restaurant.name}"
