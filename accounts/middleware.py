from .models import SystemActivityLog


class SystemActivityLogMiddleware:

    def __init__(self, get_response):

        self.get_response = get_response


    def __call__(self, request):

        response = self.get_response(request)

        # -------------------------------------------------
        # Ignore anonymous users
        # -------------------------------------------------

        if not request.user.is_authenticated:
            return response

        # -------------------------------------------------
        # Ignore static/media
        # -------------------------------------------------

        path = request.path.lower()

        if (
            path.startswith("/static/")
            or
            path.startswith("/media/")
        ):
            return response

        # -------------------------------------------------
        # IP ADDRESS
        # -------------------------------------------------

        ip_address = request.META.get(
            "REMOTE_ADDR"
        )

        # -------------------------------------------------
        # METHOD
        # -------------------------------------------------

        if request.method == "GET":

            action = "view"

        elif request.method == "POST":

            action = "update"

        elif request.method == "DELETE":

            action = "delete"

        else:

            action = "other"

        # -------------------------------------------------
        # MODULE
        # -------------------------------------------------

        path_parts = [
            part
            for part in request.path.strip("/").split("/")
            if part
        ]

        if path_parts:

            module = path_parts[0].replace(
                "_",
                " "
            ).title()

        else:

            module = "Dashboard"

        # -------------------------------------------------
        # DESCRIPTION
        # -------------------------------------------------

        description = (
            f"{request.user.username} "
            f"accessed {request.path} "
            f"using {request.method}."
        )

        # -------------------------------------------------
        # CREATE LOG
        # -------------------------------------------------

        try:

            SystemActivityLog.objects.create(

                user=request.user,

                module=module,

                action=action,

                description=description,

                ip_address=ip_address,

            )

        except Exception:
            pass

        return response