from django.db.models import Q
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from .models import Comment, Like, Post, PostImage
from .serializers import CommentSerializer, PostSerializer


def _notify_post_owner(post, actor, notification_type, message):
    """Create a notification for the post owner, silently skipped for own posts."""
    if post.user_id == actor.id:
        return
    try:
        from apps.social.models import Notification
        Notification.objects.create(
            recipient=post.user,
            sender=actor,
            notification_type=notification_type,
            message=message,
            data={'post_id': post.id},
        )
    except Exception:
        pass  # Notifications are non-critical


class PostViewSet(viewsets.ModelViewSet):
    serializer_class = PostSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['is_published', 'user', 'restaurant']
    ordering = ['-created_at']

    def get_queryset(self):
        queryset = Post.objects.select_related('user', 'restaurant').prefetch_related('images')

        if self.action in ['update', 'partial_update', 'destroy']:
            return queryset.filter(user=self.request.user)

        return queryset.filter(
            Q(is_published=True) | Q(user=self.request.user)
        )

    def perform_create(self, serializer):
        restaurant = serializer.validated_data.get('restaurant')
        if restaurant is not None:
            # Only the restaurant owner or platform admins may post on behalf of a restaurant
            user = self.request.user
            is_owner = getattr(restaurant, 'owner_id', None) == user.id
            is_admin = getattr(user, 'user_type', '') == 'platform_admin'
            if not (is_owner or is_admin):
                raise PermissionDenied('You are not authorised to post on behalf of this restaurant.')
        post = serializer.save(user=self.request.user)
        for i, img in enumerate(self.request.FILES.getlist('images')):
            PostImage.objects.create(post=post, image=img, order=i)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        post = serializer.save()
        # Remove images the user explicitly removed
        remove_ids = request.data.getlist('remove_image_ids')
        if remove_ids:
            PostImage.objects.filter(post=post, id__in=remove_ids).delete()
        # Add newly uploaded images
        for i, img in enumerate(request.FILES.getlist('images')):
            PostImage.objects.create(post=post, image=img, order=i)
        return Response(self.get_serializer(post).data)

    @action(detail=True, methods=['post', 'delete'])
    def like(self, request, pk=None):
        post = self.get_object()
        user = request.user
        if request.method == 'POST':
            _, created = Like.objects.get_or_create(user=user, post=post)
            if created:
                _notify_post_owner(
                    post, user, 'post_liked',
                    f'{user.get_full_name() or user.username} liked your post.',
                )
                return Response({'message': 'Post liked'}, status=status.HTTP_201_CREATED)
            return Response({'message': 'Already liked'}, status=status.HTTP_400_BAD_REQUEST)
        # DELETE
        deleted, _ = Like.objects.filter(user=user, post=post).delete()
        if deleted:
            return Response({'message': 'Post unliked'})
        return Response({'message': 'Not liked'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get', 'post'])
    def comments(self, request, pk=None):
        post = self.get_object()
        if request.method == 'GET':
            qs = post.comments.filter(parent=None).select_related('user')
            serializer = CommentSerializer(qs, many=True, context={'request': request})
            return Response(serializer.data)
        # POST
        serializer = CommentSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save(user=request.user, post=post)
            _notify_post_owner(
                post, request.user, 'post_commented',
                f'{request.user.get_full_name() or request.user.username} commented on your post.',
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['delete'], url_path='comments/(?P<comment_pk>[^/.]+)')
    def delete_comment(self, request, pk=None, comment_pk=None):
        try:
            comment = Comment.objects.get(pk=comment_pk, post_id=pk, user=request.user)
        except Comment.DoesNotExist:
            return Response({'message': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
        comment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def share(self, request, pk=None):
        post = self.get_object()
        _notify_post_owner(
            post, request.user, 'post_shared',
            f'{request.user.get_full_name() or request.user.username} shared your post.',
        )
        return Response({'message': 'Shared'}, status=status.HTTP_200_OK)
