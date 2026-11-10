from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone

from .models import Announcement


# =========================================================
# ROLES WHO CAN CREATE ANNOUNCEMENTS
# =========================================================

ANNOUNCEMENT_CREATORS = [
    "vice_principal",
    "principal",
    "chairman",
]


# =========================================================
# GET USER ROLE
# =========================================================

def get_user_role(request):

    if not hasattr(request.user, "profile"):
        return None

    return request.user.profile.role


# =========================================================
# RECEIVED ANNOUNCEMENTS
# =========================================================

@login_required
def announcement_list(request):

    role = get_user_role(request)

    if role is None:
        return redirect("accounts:login")

    # -----------------------------------------------------
    # Audience based on logged-in user's role
    # -----------------------------------------------------

    if role == "student":

        audience_roles = [
            "all",
            "students",
        ]

    elif role == "parent":

        audience_roles = [
            "all",
            "parents",
        ]

    elif role == "teacher":

        audience_roles = [
            "all",
            "teachers",
            "staff",
        ]

    elif role in [
        "admission_staff",
        "accountant",
        "bus_driver",
    ]:

        audience_roles = [
            "all",
            "staff",
        ]

    elif role in [
        "system_administrator",
        "vice_principal",
        "principal",
        "chairman",
    ]:

        audience_roles = [
            "all",
            "management",
            "staff",
        ]

    else:

        audience_roles = [
            "all",
        ]

    # -----------------------------------------------------
    # Active + non-expired announcements
    # -----------------------------------------------------

    now = timezone.now()

    announcements = Announcement.objects.filter(
        is_active=True,
        audience__in=audience_roles,
    ).filter(
        models_q_expiry()
    ).order_by("-publish_date")

    context = {
        "announcements": announcements,
        "role": role,
        "role_display": request.user.profile.get_role_display(),
        "can_create": role in ANNOUNCEMENT_CREATORS,
    }

    return render(
        request,
        "announcements/announcement_list.html",
        context,
    )


# =========================================================
# CREATE ANNOUNCEMENT
# =========================================================

@login_required
def announcement_create(request):

    role = get_user_role(request)

    # -----------------------------------------------------
    # Backend permission
    # -----------------------------------------------------

    if role not in ANNOUNCEMENT_CREATORS:

        messages.error(
            request,
            "You do not have permission to create announcements."
        )

        return redirect("announcements:list")

    # -----------------------------------------------------
    # POST
    # -----------------------------------------------------

    if request.method == "POST":

        title = request.POST.get("title", "").strip()
        message = request.POST.get("message", "").strip()
        priority = request.POST.get("priority", "normal")
        audience = request.POST.get("audience", "all")
        expiry_date = request.POST.get("expiry_date", "").strip()

        # -------------------------------------------------
        # Validation
        # -------------------------------------------------

        if not title:

            messages.error(
                request,
                "Please enter announcement title."
            )

            return render(
                request,
                "announcements/announcement_create.html",
                {
                    "form_data": request.POST,
                    "role": role,
                    "role_display": request.user.profile.get_role_display(),
                },
            )

        if not message:

            messages.error(
                request,
                "Please enter announcement message."
            )

            return render(
                request,
                "announcements/announcement_create.html",
                {
                    "form_data": request.POST,
                    "role": role,
                    "role_display": request.user.profile.get_role_display(),
                },
            )

        # -------------------------------------------------
        # Create announcement
        # -------------------------------------------------

        announcement = Announcement.objects.create(
            title=title,
            message=message,
            priority=priority,
            audience=audience,
            expiry_date=expiry_date if expiry_date else None,
            is_active=True,
            created_by=request.user,
        )

        messages.success(
            request,
            "Announcement created successfully."
        )

        return redirect(
            "announcements:history"
        )

    # -----------------------------------------------------
    # GET
    # -----------------------------------------------------

    context = {
        "role": role,
        "role_display": request.user.profile.get_role_display(),
    }

    return render(
        request,
        "announcements/announcement_create.html",
        context,
    )


# =========================================================
# ANNOUNCEMENT HISTORY
# =========================================================

@login_required
def announcement_history(request):

    role = get_user_role(request)

    # -----------------------------------------------------
    # Backend permission
    # -----------------------------------------------------

    if role not in ANNOUNCEMENT_CREATORS:

        messages.error(
            request,
            "You do not have permission to access announcement history."
        )

        return redirect("announcements:list")

    # -----------------------------------------------------
    # History of announcements created by the user
    # -----------------------------------------------------

    announcements = Announcement.objects.filter(
        created_by=request.user
    ).order_by(
        "-created_at"
    )

    context = {
        "announcements": announcements,
        "role": role,
        "role_display": request.user.profile.get_role_display(),
    }

    return render(
        request,
        "announcements/announcement_history.html",
        context,
    )


# =========================================================
# ANNOUNCEMENT DETAIL
# =========================================================

@login_required
def announcement_detail(request, announcement_id):

    role = get_user_role(request)

    if role is None:
        return redirect("accounts:login")

    # -----------------------------------------------------
    # Find announcement
    # -----------------------------------------------------

    announcement = get_object_or_404(
        Announcement,
        id=announcement_id,
        is_active=True,
    )

    # -----------------------------------------------------
    # Check whether user can receive it
    # -----------------------------------------------------

    allowed_audiences = ["all"]

    if role == "student":

        allowed_audiences += [
            "students",
        ]

    elif role == "parent":

        allowed_audiences += [
            "parents",
        ]

    elif role == "teacher":

        allowed_audiences += [
            "teachers",
            "staff",
        ]

    elif role in [
        "admission_staff",
        "accountant",
        "bus_driver",
    ]:

        allowed_audiences += [
            "staff",
        ]

    elif role in [
        "system_administrator",
        "vice_principal",
        "principal",
        "chairman",
    ]:

        allowed_audiences += [
            "management",
            "staff",
        ]

    # -----------------------------------------------------
    # Creator can always view own announcement
    # -----------------------------------------------------

    if announcement.created_by == request.user:

        allowed = True

    else:

        allowed = announcement.audience in allowed_audiences

    if not allowed:

        messages.error(
            request,
            "You do not have access to this announcement."
        )

        return redirect(
            "announcements:list"
        )

    context = {
        "announcement": announcement,
        "role": role,
        "role_display": request.user.profile.get_role_display(),
    }

    return render(
        request,
        "announcements/announcement_detail.html",
        context,
    )


# =========================================================
# EXPIRY FILTER HELPER
# =========================================================

from django.db.models import Q


def models_q_expiry():

    now = timezone.now()

    return Q(
        expiry_date__isnull=True
    ) | Q(
        expiry_date__gte=now
    )