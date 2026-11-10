from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from .models import Notification


@login_required
def notification_list(request):

    notifications = Notification.objects.filter(
        recipient=request.user
    ).order_by("-created_at")

    unread_count = Notification.objects.filter(
        recipient=request.user,
        is_read=False
    ).count()

    context = {
        "notifications": notifications,
        "unread_count": unread_count,
    }

    return render(
        request,
        "notifications/notification_list.html",
        context
    )


@login_required
def mark_as_read(request, notification_id):

    notification = get_object_or_404(
        Notification,
        id=notification_id,
        recipient=request.user
    )

    notification.is_read = True
    notification.save(
        update_fields=["is_read"]
    )

    if notification.related_url:
        return redirect(notification.related_url)

    return redirect("notifications:list")


@login_required
def mark_all_as_read(request):

    Notification.objects.filter(
        recipient=request.user,
        is_read=False
    ).update(
        is_read=True
    )

    return redirect("notifications:list")