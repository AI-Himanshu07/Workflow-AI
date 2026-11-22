
def notification_count(request):

    unread_count = 0

    if request.user.is_authenticated:
        unread_count = request.user.notifications.filter(
            is_read=False
        ).count()

    return {
        'notifications_unread_count': unread_count
    }
