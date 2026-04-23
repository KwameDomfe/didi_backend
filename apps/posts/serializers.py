from rest_framework import serializers
from apps.accounts.serializers import PublicUserSerializer
from .models import Post, Comment, PostImage


class RestaurantMinimalSerializer(serializers.Serializer):
    """Lightweight read-only restaurant info embedded in posts."""
    id = serializers.IntegerField()
    name = serializers.CharField()
    slug = serializers.CharField()


class CommentSerializer(serializers.ModelSerializer):
    user = PublicUserSerializer(read_only=True)
    replies = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ['id', 'user', 'content', 'replies', 'created_at', 'updated_at']
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']

    def get_replies(self, obj):
        if obj.parent is None:
            replies = obj.replies.all()[:5]
            return CommentSerializer(replies, many=True, context=self.context).data
        return []


class PostImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostImage
        fields = ['id', 'image', 'order']


class PostSerializer(serializers.ModelSerializer):
    user = PublicUserSerializer(read_only=True)
    images = PostImageSerializer(many=True, read_only=True)
    restaurant_detail = RestaurantMinimalSerializer(source='restaurant', read_only=True)
    likes_count = serializers.SerializerMethodField()
    comments_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            'id',
            'user',
            'restaurant',
            'restaurant_detail',
            'title',
            'content',
            'image',
            'video',
            'images',
            'is_published',
            'likes_count',
            'comments_count',
            'is_liked',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']

    def get_likes_count(self, obj):
        return obj.likes.count()

    def get_comments_count(self, obj):
        return obj.comments.count()

    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.likes.filter(user=request.user).exists()
        return False
