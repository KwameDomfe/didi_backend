from django.db import models
from django.contrib.auth import get_user_model
from apps.restaurants.models import Restaurant, MenuItem

User = get_user_model()

class Follow(models.Model):
    follower = models.ForeignKey(User, on_delete=models.CASCADE, related_name='following')
    following = models.ForeignKey(User, on_delete=models.CASCADE, related_name='followers')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['follower', 'following']

    def __str__(self):
        return f"{self.follower.username} follows {self.following.username}"

class Post(models.Model):
    POST_TYPES = [
        ('review', 'Review'),
        ('photo', 'Photo'),
        ('check_in', 'Check In'),
        ('recommendation', 'Recommendation'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='social_posts', null=True, blank=True)
    menu_item = models.ForeignKey(MenuItem, on_delete=models.CASCADE, null=True, blank=True)
    post_type = models.CharField(max_length=20, choices=POST_TYPES)
    content = models.TextField()
    images = models.JSONField(default=list)
    rating = models.IntegerField(null=True, blank=True, choices=[(i, i) for i in range(1, 6)])
    location_data = models.JSONField(default=dict)
    tags = models.JSONField(default=list)
    is_public = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.post_type} - {self.created_at.date()}"

class Like(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'post']

    def __str__(self):
        return f"{self.user.username} likes {self.post.id}"

class Comment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.user.username} commented on {self.post.id}"

class DiningGroup(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_groups')
    members = models.ManyToManyField(User, through='GroupMembership', related_name='dining_groups')
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, null=True, blank=True)
    planned_date = models.DateTimeField(null=True, blank=True)
    max_members = models.IntegerField(default=8)
    is_public = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class GroupMembership(models.Model):
    ROLE_CHOICES = [
        ('creator', 'Creator'),
        ('admin', 'Admin'),
        ('member', 'Member'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    group = models.ForeignKey(DiningGroup, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='member')
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'group']

    def __str__(self):
        return f"{self.user.username} in {self.group.name}"

class Favorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorites')
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, null=True, blank=True)
    menu_item = models.ForeignKey(MenuItem, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [
            ['user', 'restaurant'],
            ['user', 'menu_item']
        ]

    def __str__(self):
        if self.restaurant:
            return f"{self.user.username} favorited {self.restaurant.name}"
        return f"{self.user.username} favorited {self.menu_item.name}"

class ConnectionRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
    ]

    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_connection_requests')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_connection_requests')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ['sender', 'recipient']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.sender.username} -> {self.recipient.username} ({self.status})"

class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('new_connection', 'New Connection'),
        ('connection_request_received', 'Connection Request Received'),
        ('connection_request_accepted', 'Connection Request Accepted'),
        ('connection_request_declined', 'Connection Request Declined'),
        ('plan_joined', 'Plan Joined'),
        ('post_liked', 'Post Liked'),
        ('post_commented', 'Post Commented'),
        ('post_shared', 'Post Shared'),
        ('restaurant_liked', 'Restaurant Liked'),
        ('restaurant_commented', 'Restaurant Commented'),
        ('restaurant_reviewed', 'Restaurant Reviewed'),
        ('menu_item_liked', 'Menu Item Liked'),
        ('menu_item_commented', 'Menu Item Commented'),
        ('menu_item_shared', 'Menu Item Shared'),
    ]

    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    sender = models.ForeignKey(
        User, on_delete=models.SET_NULL, related_name='sent_notifications', null=True, blank=True
    )
    notification_type = models.CharField(max_length=30, choices=NOTIFICATION_TYPES)
    message = models.TextField()
    data = models.JSONField(default=dict, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Notification for {self.recipient.username}: {self.notification_type}"
