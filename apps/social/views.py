import json
import time

from django.http import JsonResponse, StreamingHttpResponse
from django.db import transaction
from django.db.models import Exists, OuterRef, Q
from django.utils import timezone
from django.views.decorators.http import require_GET
from rest_framework import viewsets, status, permissions
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from .models import Follow, Post, Like, Comment, DiningGroup, GroupMembership, Favorite, ConnectionRequest, Notification
from .serializers import PostSerializer, CommentSerializer, DiningGroupSerializer, FollowSerializer, ConnectionRequestSerializer, NotificationSerializer


def get_connected_user_ids(user):
    reciprocal_follow = Follow.objects.filter(
        follower=OuterRef('following'),
        following=user,
    )

    return list(
        Follow.objects
        .filter(follower=user)
        .annotate(is_connected=Exists(reciprocal_follow))
        .filter(is_connected=True)
        .values_list('following_id', flat=True)
    )


def create_notification(recipient, sender, notification_type, message, data=None):
    return Notification.objects.create(
        recipient=recipient,
        sender=sender,
        notification_type=notification_type,
        message=message,
        data=data or {},
    )


def accept_connection_request(connection_request, acting_user):
    with transaction.atomic():
        forward_follow, _ = Follow.objects.get_or_create(
            follower=connection_request.sender,
            following=connection_request.recipient,
        )
        reverse_follow, _ = Follow.objects.get_or_create(
            follower=connection_request.recipient,
            following=connection_request.sender,
        )
        connection_request.status = 'accepted'
        connection_request.responded_at = timezone.now()
        connection_request.save(update_fields=['status', 'responded_at'])
        Notification.objects.filter(
            recipient=acting_user,
            notification_type='connection_request_received',
            data__request_id=connection_request.id,
        ).update(is_read=True)
        create_notification(
            recipient=connection_request.sender,
            sender=acting_user,
            notification_type='connection_request_accepted',
            message=f"{acting_user.username} accepted your connection request.",
            data={
                'request_id': connection_request.id,
                'user_id': acting_user.id,
            },
        )
    return forward_follow, reverse_follow


def decline_connection_request(connection_request, acting_user):
    connection_request.status = 'declined'
    connection_request.responded_at = timezone.now()
    connection_request.save(update_fields=['status', 'responded_at'])
    Notification.objects.filter(
        recipient=acting_user,
        notification_type='connection_request_received',
        data__request_id=connection_request.id,
    ).update(is_read=True)
    create_notification(
        recipient=connection_request.sender,
        sender=acting_user,
        notification_type='connection_request_declined',
        message=f"{acting_user.username} declined your connection request.",
        data={
            'request_id': connection_request.id,
            'user_id': acting_user.id,
        },
    )


def get_stream_user(request):
    token_key = request.GET.get('token')
    if not token_key:
        return None
    try:
        token = Token.objects.select_related('user').get(key=token_key)
    except Token.DoesNotExist:
        return None
    return token.user if token.user.is_authenticated else None

class PostViewSet(viewsets.ModelViewSet):
    serializer_class = PostSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['post_type', 'restaurant', 'user']
    ordering = ['-created_at']

    def get_queryset(self):
        return Post.objects.filter(is_public=True).select_related('user', 'restaurant', 'menu_item')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post', 'delete'])
    def like(self, request, pk=None):
        """Like or unlike a post"""
        post = self.get_object()
        user = request.user

        if request.method == 'POST':
            like, created = Like.objects.get_or_create(user=user, post=post)
            if created:
                return Response({'message': 'Post liked'})
            return Response({'message': 'Already liked'}, status=status.HTTP_400_BAD_REQUEST)
        
        elif request.method == 'DELETE':
            try:
                like = Like.objects.get(user=user, post=post)
                like.delete()
                return Response({'message': 'Post unliked'})
            except Like.DoesNotExist:
                return Response({'message': 'Not liked'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get', 'post'])
    def comments(self, request, pk=None):
        """Get or create comments for a post"""
        post = self.get_object()
        
        if request.method == 'GET':
            comments = post.comments.filter(parent=None).select_related('user')
            serializer = CommentSerializer(comments, many=True, context={'request': request})
            return Response(serializer.data)
        
        elif request.method == 'POST':
            serializer = CommentSerializer(data=request.data, context={'request': request})
            if serializer.is_valid():
                serializer.save(user=request.user, post=post)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def feed(self, request):
        """Get personalized feed based on mutual connections"""
        user = request.user
        connected_user_ids = get_connected_user_ids(user)
        
        # Include posts from mutual connections and the current user.
        queryset = self.get_queryset().filter(
            user__in=connected_user_ids + [user.id]
        )
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

class DiningGroupViewSet(viewsets.ModelViewSet):
    serializer_class = DiningGroupSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['restaurant', 'is_public', 'is_active']
    ordering = ['-created_at']

    def get_queryset(self):
        return DiningGroup.objects.filter(is_active=True).select_related('creator', 'restaurant')

    def perform_create(self, serializer):
        group = serializer.save(creator=self.request.user)
        # Add creator as member
        GroupMembership.objects.create(
            user=self.request.user,
            group=group,
            role='creator'
        )

    @action(detail=True, methods=['post'])
    def join(self, request, pk=None):
        """Join a dining group"""
        group = self.get_object()
        user = request.user
        
        if group.members.count() >= group.max_members:
            return Response(
                {'error': 'Group is full'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        membership, created = GroupMembership.objects.get_or_create(
            user=user,
            group=group,
            defaults={'role': 'member'}
        )
        
        if created:
            if group.creator != user:
                create_notification(
                    recipient=group.creator,
                    sender=user,
                    notification_type='plan_joined',
                    message=f"{user.username} joined your dining plan \"{group.name}\".",
                    data={
                        'plan_id': group.id,
                        'plan_name': group.name,
                        'user_id': user.id,
                    },
                )
            return Response({'message': 'Joined group successfully'})
        return Response(
            {'message': 'Already a member'},
            status=status.HTTP_400_BAD_REQUEST
        )

    @action(detail=True, methods=['post'])
    def leave(self, request, pk=None):
        """Leave a dining group"""
        group = self.get_object()
        user = request.user
        
        try:
            membership = GroupMembership.objects.get(user=user, group=group)
            if membership.role == 'creator':
                return Response(
                    {'error': 'Creator cannot leave group'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            membership.delete()
            return Response({'message': 'Left group successfully'})
        except GroupMembership.DoesNotExist:
            return Response(
                {'message': 'Not a member'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

class FollowViewSet(viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def _get_target_user(self, user_id):
        from django.contrib.auth import get_user_model

        User = get_user_model()
        return get_object_or_404(User, id=user_id)

    def _get_connections_queryset(self, user):
        return (
            Follow.objects
            .filter(follower=user)
            .annotate(
                is_connected=Exists(
                    Follow.objects.filter(
                        follower=OuterRef('following'),
                        following=user,
                    )
                )
            )
            .filter(is_connected=True)
            .select_related('follower', 'following')
        )

    def _get_pending_request(self, request_id, recipient):
        return get_object_or_404(
            ConnectionRequest,
            id=request_id,
            recipient=recipient,
            status='pending',
        )

    @action(detail=False, methods=['post'])
    def follow_user(self, request):
        """Follow a user"""
        user_id = request.data.get('user_id')
        if not user_id:
            return Response({'error': 'user_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        user_to_follow = self._get_target_user(user_id)
        
        if user_to_follow == request.user:
            return Response({'error': 'Cannot follow yourself'}, status=status.HTTP_400_BAD_REQUEST)
        
        follow, created = Follow.objects.get_or_create(
            follower=request.user,
            following=user_to_follow
        )
        
        if created:
            return Response({'message': 'User followed successfully'})
        return Response({'message': 'Already following'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def connect_user(self, request):
        """Send a connection request or accept a reciprocal pending request"""
        user_id = request.data.get('user_id')
        if not user_id:
            return Response({'error': 'user_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        other_user = self._get_target_user(user_id)
        if other_user == request.user:
            return Response({'error': 'Cannot connect with yourself'}, status=status.HTTP_400_BAD_REQUEST)

        if self._get_connections_queryset(request.user).filter(following=other_user).exists():
            return Response(
                {'message': 'Already connected', 'relationship_status': 'accepted'},
                status=status.HTTP_200_OK,
            )

        outgoing_request = ConnectionRequest.objects.filter(
            sender=request.user,
            recipient=other_user,
        ).select_related('sender', 'recipient').first()
        if outgoing_request and outgoing_request.status == 'pending':
            serializer = ConnectionRequestSerializer(outgoing_request)
            return Response(
                {
                    'message': 'Connection request already pending',
                    'relationship_status': 'pending_outgoing',
                    'request': serializer.data,
                },
                status=status.HTTP_200_OK,
            )

        incoming_request = ConnectionRequest.objects.filter(
            sender=other_user,
            recipient=request.user,
            status='pending',
        ).select_related('sender', 'recipient').first()
        if incoming_request:
            accept_connection_request(incoming_request, request.user)
            return Response(
                {
                    'message': 'Connection request accepted',
                    'relationship_status': 'accepted',
                    'request': ConnectionRequestSerializer(incoming_request).data,
                },
                status=status.HTTP_200_OK,
            )

        if outgoing_request:
            outgoing_request.status = 'pending'
            outgoing_request.responded_at = None
            outgoing_request.save(update_fields=['status', 'responded_at'])
            connection_request = outgoing_request
        else:
            connection_request = ConnectionRequest.objects.create(
                sender=request.user,
                recipient=other_user,
            )
        create_notification(
            recipient=other_user,
            sender=request.user,
            notification_type='connection_request_received',
            message=f"{request.user.username} sent you a connection request.",
            data={
                'request_id': connection_request.id,
                'user_id': request.user.id,
            },
        )
        return Response(
            {
                'message': 'Connection request sent',
                'relationship_status': 'pending_outgoing',
                'request': ConnectionRequestSerializer(connection_request).data,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=['get'])
    def requests(self, request):
        incoming = ConnectionRequest.objects.filter(
            recipient=request.user,
            status='pending',
        ).select_related('sender', 'recipient')
        outgoing = ConnectionRequest.objects.filter(
            sender=request.user,
            status='pending',
        ).select_related('sender', 'recipient')

        return Response({
            'incoming': ConnectionRequestSerializer(incoming, many=True).data,
            'outgoing': ConnectionRequestSerializer(outgoing, many=True).data,
        })

    @action(detail=False, methods=['post'])
    def accept_request(self, request):
        request_id = request.data.get('request_id')
        if not request_id:
            return Response({'error': 'request_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        connection_request = self._get_pending_request(request_id, request.user)
        accept_connection_request(connection_request, request.user)
        return Response({
            'message': 'Connection request accepted',
            'request': ConnectionRequestSerializer(connection_request).data,
        })

    @action(detail=False, methods=['post'])
    def decline_request(self, request):
        request_id = request.data.get('request_id')
        if not request_id:
            return Response({'error': 'request_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        connection_request = self._get_pending_request(request_id, request.user)
        decline_connection_request(connection_request, request.user)
        return Response({
            'message': 'Connection request declined',
            'request': ConnectionRequestSerializer(connection_request).data,
        })

    @action(detail=False, methods=['post'])
    def unfollow_user(self, request):
        """Unfollow a user"""
        user_id = request.data.get('user_id')
        if not user_id:
            return Response({'error': 'user_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            follow = Follow.objects.get(
                follower=request.user,
                following_id=user_id
            )
            follow.delete()
            return Response({'message': 'User unfollowed successfully'})
        except Follow.DoesNotExist:
            return Response({'message': 'Not following this user'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def disconnect_user(self, request):
        """Remove a bidirectional social connection"""
        user_id = request.data.get('user_id')
        if not user_id:
            return Response({'error': 'user_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        other_user = self._get_target_user(user_id)
        deleted_count, _ = Follow.objects.filter(
            Q(follower=request.user, following=other_user)
            | Q(follower=other_user, following=request.user)
        ).delete()

        if deleted_count == 0:
            return Response({'message': 'Not connected to this user'}, status=status.HTTP_400_BAD_REQUEST)

        return Response({'message': 'User disconnected successfully'})

    @action(detail=False, methods=['get'])
    def followers(self, request):
        """Get user's followers"""
        followers = Follow.objects.filter(following=request.user).select_related('follower')
        serializer = FollowSerializer(followers, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def connections(self, request):
        """Get users with a reciprocal follow relationship"""
        connections = self._get_connections_queryset(request.user)
        serializer = FollowSerializer(connections, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def following(self, request):
        """Get users that current user is following"""
        following = Follow.objects.filter(follower=request.user).select_related('following')
        serializer = FollowSerializer(following, many=True)
        return Response(serializer.data)


class NotificationViewSet(viewsets.GenericViewSet):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)

    def list(self, request):
        queryset = self.get_queryset()[:50]
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        count = Notification.objects.filter(recipient=request.user, is_read=False).count()
        return Response({'count': count})

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        notification = self.get_queryset().filter(pk=pk).first()
        if not notification:
            return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
        notification.is_read = True
        notification.save(update_fields=['is_read'])
        return Response({'message': 'Marked as read'})

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
        return Response({'message': 'All notifications marked as read'})


@require_GET
def stream_notifications(request):
    user = get_stream_user(request)
    if user is None:
        return JsonResponse({'error': 'Invalid or missing token'}, status=401)

    def event_stream():
        last_notification_id = 0
        # Limit to 60 cycles (~5 min) so the WSGI thread is freed regularly.
        # EventSource will automatically reconnect after the stream ends.
        for _ in range(60):
            latest_notification = Notification.objects.filter(recipient=user).order_by('-id').first()
            unread_count = Notification.objects.filter(recipient=user, is_read=False).count()
            latest_id = latest_notification.id if latest_notification else 0

            if latest_id != last_notification_id:
                payload = {
                    'latest_id': latest_id,
                    'unread_count': unread_count,
                }
                yield f"data: {json.dumps(payload)}\n\n"
                last_notification_id = latest_id
            else:
                yield ": keep-alive\n\n"

            time.sleep(5)

    response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response