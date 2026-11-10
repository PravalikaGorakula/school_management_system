
def get_client_ip(request):
    """
    Get the client IP address from the current request.
    """
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")

    if forwarded_for:
        ip_address = forwarded_for.split(",")[0].strip()
    else:
        ip_address = request.META.get("REMOTE_ADDR")

    return ip_address or None


from .models import SystemActivityLog


def log_activity(
    request,
    module,
    action,
    description,
):
    """
    Save a user's activity in the system activity log.
    """

    try:
        user = None

        if (
            request is not None
            and hasattr(request, "user")
            and request.user.is_authenticated
        ):
            user = request.user

        ip_address = None

        if request is not None:
            ip_address = get_client_ip(request)

        SystemActivityLog.objects.create(
            user=user,
            module=module,
            action=action,
            description=description,
            ip_address=ip_address,
        )

    except Exception:
        # Do not interrupt the main operation if logging fails.
        import logging
        logging.getLogger(__name__).exception(
            "Failed to save system activity log."
        )
