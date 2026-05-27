import datetime
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.utils import timezone
from django.views import View

from .models import UserNotificationStatus


class UserNotificationAPIView(LoginRequiredMixin, View):
    """
    Class-Based View handling AJAX interactions for the global notification 
    floating bell badge and the dropdown feed panel.
    """

    def get(self, request, *args, **kwargs):
        """
        Returns JSON containing the unread counter and the latest 10 notifications.
        """
        user_notifications = (
            UserNotificationStatus.objects.filter(user=request.user)
            .select_related('notification', 'notification__sender')
            .order_by('-notification__created_at')
        )

        # 1. Fetch live unread metric count
        unread_count = user_notifications.filter(is_read=False).count()

        # 2. Serialize recent 10 feed rows 
        notification_list = []
        for item in user_notifications[:10]:
            sender_name = "System"
            if item.notification.sender:
                sender_name = item.notification.sender.get_full_name() or item.notification.sender.username

            notification_list.append({
                'id': item.id,
                'title': item.notification.title,
                'message': item.notification.message,
                'type': item.notification.notification_type,
                'scope': item.notification.scope,
                'is_read': item.is_read,
                'sender': sender_name,
                'created_at': item.notification.created_at.strftime('%b %d, %H:%M'),
            })

        return JsonResponse({
            'unread_count': unread_count,
            'notifications': notification_list
        }, status=200)

    def post(self, request, *args, **kwargs):
        """
        Handles updating the read status of notifications.
        Expects 'notification_id' for single items, or 'mark_all=true' for clear outs.
        """
        notification_id = request.POST.get('notification_id')
        mark_all = request.POST.get('mark_all') == 'true'

        base_queryset = UserNotificationStatus.objects.filter(user=request.user, is_read=False)

        # Case A: Clear/Mark all records at once
        if mark_all:
            updated_count = base_queryset.update(
                is_read=True, 
                read_at=timezone.now()
            )
            return JsonResponse({
                'status': 'success', 
                'message': f'{updated_count} notifications marked as read.'
            }, status=200)

        # Case B: Standard click-to-read single notification row transition
        if notification_id:
            try:
                item = base_queryset.get(id=notification_id)
                item.is_read = True
                item.read_at = timezone.now()
                item.save(update_fields=['is_read', 'read_at'])
                return JsonResponse({
                    'status': 'success', 
                    'message': 'Notification marked as read.'
                }, status=200)
            except UserNotificationStatus.DoesNotExist:
                return JsonResponse({
                    'status': 'error', 
                    'message': 'Notification not found or already processed.'
                }, status=404)

        return JsonResponse({
            'status': 'error', 
            'message': 'Missing operational tracking parameters.'
        }, status=400)
    

from django.views.generic import ListView
from .models import UserNotificationStatus

class UserNotificationListView(LoginRequiredMixin, ListView):
    """
    Renders a dedicated, full-page scrolling inbox list 
    displaying all notification feed entries for the current user.
    """
    model = UserNotificationStatus
    template_name = 'notifications/inbox_list.html'
    context_object_name = 'user_notifications'
    paginate_by = 25

    def get_queryset(self):
        # Optimized with select_related to pull notification details and targets smoothly
        return (
            UserNotificationStatus.objects.filter(user=self.request.user)
            .select_related('notification', 'notification__sender')
            .order_by('-notification__created_at')
        )