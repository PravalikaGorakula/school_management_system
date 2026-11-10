from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth import update_session_auth_hash
from django.shortcuts import render, redirect


def login_view(request):

    if request.user.is_authenticated:
        return redirect("dashboard:home")

    if request.method == "POST":

        login_input = request.POST.get("login", "").strip()
        password = request.POST.get("password", "")

        if not login_input or not password:
            return render(
                request,
                "accounts/login.html",
                {
                    "error": "Please enter your username/email and password.",
                    "login_value": login_input,
                },
            )

        username = login_input

        if "@" in login_input:

            user = User.objects.filter(
                email__iexact=login_input
            ).first()

            if user:
                username = user.username

        authenticated_user = authenticate(
            request,
            username=username,
            password=password,
        )

        if authenticated_user is not None:

            if hasattr(authenticated_user, "profile"):

                if not authenticated_user.profile.is_active:

                    return render(
                        request,
                        "accounts/login.html",
                        {
                            "error": "Your account is inactive. Please contact the administrator.",
                            "login_value": login_input,
                        },
                    )

            login(request, authenticated_user)

            return redirect("dashboard:home")

        return render(
            request,
            "accounts/login.html",
            {
                "error": "Invalid username/email or password.",
                "login_value": login_input,
            },
        )

    return render(
        request,
        "accounts/login.html",
    )


@login_required
def logout_view(request):

    logout(request)

    return redirect("accounts:login")


@login_required
def profile_view(request):

    user = request.user
    profile = user.profile

    context = {
        "user": user,
        "profile": profile,
    }

    return render(
        request,
        "accounts/profile.html",
        context,
    )


# =========================================================
# CHANGE PASSWORD
# =========================================================

@login_required
def change_password_view(request):

    if request.method == "POST":

        current_password = request.POST.get(
            "current_password",
            ""
        )

        new_password = request.POST.get(
            "new_password",
            ""
        )

        confirm_password = request.POST.get(
            "confirm_password",
            ""
        )


        # -------------------------------------------------
        # CURRENT PASSWORD
        # -------------------------------------------------

        if not current_password:

            return render(
                request,
                "accounts/change_password.html",
                {
                    "error": "Please enter your current password."
                },
            )


        if not request.user.check_password(current_password):

            return render(
                request,
                "accounts/change_password.html",
                {
                    "error": "Current password is incorrect."
                },
            )


        # -------------------------------------------------
        # NEW PASSWORD
        # -------------------------------------------------

        if not new_password:

            return render(
                request,
                "accounts/change_password.html",
                {
                    "error": "Please enter a new password."
                },
            )


        # -------------------------------------------------
        # PASSWORD LENGTH
        # -------------------------------------------------

        if len(new_password) < 8:

            return render(
                request,
                "accounts/change_password.html",
                {
                    "error": "New password must contain at least 8 characters."
                },
            )


        # -------------------------------------------------
        # SAME PASSWORD
        # -------------------------------------------------

        if current_password == new_password:

            return render(
                request,
                "accounts/change_password.html",
                {
                    "error": "New password must be different from your current password."
                },
            )


        # -------------------------------------------------
        # CONFIRM PASSWORD
        # -------------------------------------------------

        if new_password != confirm_password:

            return render(
                request,
                "accounts/change_password.html",
                {
                    "error": "New password and confirm password do not match."
                },
            )


        # -------------------------------------------------
        # SET PASSWORD
        # -------------------------------------------------

        request.user.set_password(new_password)

        request.user.save()


        # -------------------------------------------------
        # KEEP USER LOGGED IN
        # -------------------------------------------------

        update_session_auth_hash(
            request,
            request.user
        )


        # -------------------------------------------------
        # SUCCESS
        # -------------------------------------------------

        return render(
            request,
            "accounts/change_password.html",
            {
                "success": "Your password has been changed successfully."
            },
        )


    return render(
        request,
        "accounts/change_password.html",
    )


from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render
from django.utils.dateparse import parse_date

from .models import SystemActivityLog


@login_required
def system_logs_view(request):
    # Role-based access control
    profile = getattr(request.user, "profile", None)
    role = getattr(profile, "role", None)

    allowed_roles = {
        "chairman",
        "principal",
        "vice_principal",
        "system_administrator",
    }

    if role not in allowed_roles and not request.user.is_superuser:
        raise PermissionDenied

    # Exclude view actions from all displayed logs
    logs = SystemActivityLog.objects.exclude(
        action="view"
    ).select_related("user")

    # Read filter values
    search = request.GET.get("search", "").strip()
    selected_module = request.GET.get("module", "").strip()
    selected_action = request.GET.get("action", "").strip()
    start_date = request.GET.get("start_date", "").strip()
    end_date = request.GET.get("end_date", "").strip()

    # Search filter
    if search:
        logs = logs.filter(
            Q(user__username__icontains=search)
            | Q(module__icontains=search)
            | Q(description__icontains=search)
            | Q(ip_address__icontains=search)
        )

    # Module filter
    if selected_module:
        logs = logs.filter(module=selected_module)

    # Available actions excluding view
    action_choices = [
        choice
        for choice in SystemActivityLog.ACTION_CHOICES
        if choice[0] != "view"
    ]

    valid_actions = {choice[0] for choice in action_choices}

    if selected_action in valid_actions:
        logs = logs.filter(action=selected_action)

    # Date filters
    parsed_start = parse_date(start_date) if start_date else None
    parsed_end = parse_date(end_date) if end_date else None

    if parsed_start:
        logs = logs.filter(timestamp__date__gte=parsed_start)

    if parsed_end:
        logs = logs.filter(timestamp__date__lte=parsed_end)

    # Summary counts exclude view actions
    visible_logs = SystemActivityLog.objects.exclude(action="view")

    total_logs = visible_logs.count()

    login_count = visible_logs.filter(
        action="login"
    ).count()

    rejected_count = visible_logs.filter(
        action="reject"
    ).count()

    # Modules available in the database
    modules = list(
        visible_logs.order_by()
        .values_list("module", flat=True)
        .distinct()
    )

    # Pagination
    paginator = Paginator(logs, 25)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {
        "page_obj": page_obj,
        "total_logs": total_logs,
        "login_count": login_count,
        "failed_or_security_count": rejected_count,
        "modules": modules,
        "action_choices": action_choices,
        "search": search,
        "selected_module": selected_module,
        "selected_action": selected_action,
        "start_date": start_date,
        "end_date": end_date,
    }

    return render(
        request,
        "accounts/system_logs.html",
        context,
    )

